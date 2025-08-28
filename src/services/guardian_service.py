from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from src.models.database import Guardian, Student, StudentGuardian, RelationshipType
from datetime import datetime
from typing import List, Optional, Dict
import pandas as pd

class GuardianService:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, guardian_info: dict) -> Guardian:
        """보호자 생성"""
        try:
            new_guardian = Guardian(**guardian_info)
            self.db.add(new_guardian)
            self.db.commit()
            self.db.refresh(new_guardian)
            
            return new_guardian
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"보호자 생성 실패: {str(e)}")
    
    def get_by_id(self, guardian_id: int) -> Optional[Guardian]:
        """ID로 보호자 조회"""
        return self.db.query(Guardian).filter(Guardian.id == guardian_id).first()
    
    def get_by_phone(self, phone: str) -> Optional[Guardian]:
        """전화번호로 보호자 조회"""
        # 숫자만 추출하여 검색
        clean_phone = ''.join(filter(str.isdigit, phone))
        return self.db.query(Guardian).filter(
            Guardian.phone.like(f"%{clean_phone}%")
        ).first()
    
    def get_all(self, search: str = None, limit: int = None) -> List[Guardian]:
        """모든 보호자 조회"""
        query = self.db.query(Guardian)
        
        # 검색 필터
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Guardian.name.ilike(search_term),
                    Guardian.phone.ilike(search_term),
                    Guardian.email.ilike(search_term),
                    Guardian.workplace.ilike(search_term)
                )
            )
        
        # 정렬
        query = query.order_by(Guardian.name)
        
        # 제한
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def update(self, guardian_id: int, update_data: dict) -> Guardian:
        """보호자 정보 수정"""
        try:
            guardian = self.get_by_id(guardian_id)
            if not guardian:
                raise Exception("보호자를 찾을 수 없습니다.")
            
            # 업데이트
            for key, value in update_data.items():
                if hasattr(guardian, key):
                    setattr(guardian, key, value)
            
            guardian.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(guardian)
            
            return guardian
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"보호자 정보 수정 실패: {str(e)}")
    
    def delete(self, guardian_id: int) -> bool:
        """보호자 삭제"""
        try:
            guardian = self.get_by_id(guardian_id)
            if not guardian:
                raise Exception("보호자를 찾을 수 없습니다.")
            
            # 연결된 학생이 있는지 확인
            student_count = self.db.query(StudentGuardian).filter(
                StudentGuardian.guardian_id == guardian_id
            ).count()
            
            if student_count > 0:
                raise Exception("연결된 학생이 있어 삭제할 수 없습니다. 먼저 학생 연결을 해제해주세요.")
            
            self.db.delete(guardian)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"보호자 삭제 실패: {str(e)}")
    
    def get_by_student(self, student_id: int) -> List[Guardian]:
        """학생의 보호자 목록 조회"""
        return self.db.query(Guardian).join(StudentGuardian).filter(
            StudentGuardian.student_id == student_id
        ).all()
    
    def get_students(self, guardian_id: int) -> List[Student]:
        """보호자의 자녀 목록 조회"""
        return self.db.query(Student).join(StudentGuardian).filter(
            StudentGuardian.guardian_id == guardian_id
        ).all()
    
    def link_student(self, guardian_id: int, student_id: int) -> bool:
        """보호자와 학생 연결"""
        try:
            # 이미 연결되어 있는지 확인
            existing_link = self.db.query(StudentGuardian).filter(
                StudentGuardian.guardian_id == guardian_id,
                StudentGuardian.student_id == student_id
            ).first()
            
            if existing_link:
                return True  # 이미 연결되어 있음
            
            # 새로운 연결 생성
            student_guardian = StudentGuardian(
                student_id=student_id,
                guardian_id=guardian_id
            )
            
            self.db.add(student_guardian)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"보호자-학생 연결 실패: {str(e)}")
    
    def unlink_student(self, guardian_id: int, student_id: int) -> bool:
        """보호자와 학생 연결 해제"""
        try:
            student_guardian = self.db.query(StudentGuardian).filter(
                StudentGuardian.guardian_id == guardian_id,
                StudentGuardian.student_id == student_id
            ).first()
            
            if student_guardian:
                self.db.delete(student_guardian)
                self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"보호자-학생 연결 해제 실패: {str(e)}")
    
    def find_duplicates(self) -> List[Dict]:
        """중복 보호자 찾기 (전화번호 기준)"""
        # 전화번호별 보호자 수 집계
        phone_counts = self.db.query(
            Guardian.phone,
            func.count(Guardian.id).label('count'),
            func.group_concat(Guardian.id).label('ids'),
            func.group_concat(Guardian.name).label('names')
        ).group_by(Guardian.phone).having(func.count(Guardian.id) > 1).all()
        
        duplicates = []
        for phone, count, ids, names in phone_counts:
            if phone:  # 전화번호가 있는 경우만
                duplicates.append({
                    'phone': phone,
                    'count': count,
                    'guardian_ids': [int(id) for id in ids.split(',')],
                    'names': names.split(',')
                })
        
        return duplicates
    
    def merge(self, primary_guardian_id: int, duplicate_guardian_ids: List[int]) -> bool:
        """중복 보호자 병합"""
        try:
            primary_guardian = self.get_guardian_by_id(primary_guardian_id)
            if not primary_guardian:
                raise Exception("기본 보호자를 찾을 수 없습니다.")
            
            for duplicate_id in duplicate_guardian_ids:
                if duplicate_id == primary_guardian_id:
                    continue
                
                # 중복 보호자의 학생 관계를 기본 보호자로 이전
                duplicate_relationships = self.db.query(StudentGuardian).filter(
                    StudentGuardian.guardian_id == duplicate_id
                ).all()
                
                for relationship in duplicate_relationships:
                    # 기본 보호자와 학생의 관계가 이미 있는지 확인
                    existing = self.db.query(StudentGuardian).filter(
                        StudentGuardian.student_id == relationship.student_id,
                        StudentGuardian.guardian_id == primary_guardian_id
                    ).first()
                    
                    if not existing:
                        # 새로운 관계 생성
                        new_relationship = StudentGuardian(
                            student_id=relationship.student_id,
                            guardian_id=primary_guardian_id
                        )
                        self.db.add(new_relationship)
                    
                    # 기존 관계 삭제
                    self.db.delete(relationship)
                
                # 중복 보호자 삭제
                duplicate_guardian = self.get_guardian_by_id(duplicate_id)
                if duplicate_guardian:
                    self.db.delete(duplicate_guardian)
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"보호자 병합 실패: {str(e)}")
    
    def get_statistics(self) -> dict:
        """보호자 통계"""
        total_guardians = self.db.query(Guardian).count()
        
        # 관계별 통계
        relationship_stats = self.db.query(
            Guardian.relationship_type,
            func.count(Guardian.id)
        ).group_by(Guardian.relationship_type).all()
        
        # 연락처 설정 통계
        communication_stats = {
            'sms_enabled': self.db.query(Guardian).filter(Guardian.sms_enabled == True).count(),
            'email_enabled': self.db.query(Guardian).filter(Guardian.email_enabled == True).count(),
            'kakao_enabled': self.db.query(Guardian).filter(Guardian.kakao_enabled == True).count(),
            'phone_enabled': self.db.query(Guardian).filter(Guardian.phone_enabled == True).count(),
        }
        
        # 자녀 수별 통계
        children_stats = self.db.query(
            func.count(StudentGuardian.student_id).label('children_count'),
            func.count(Guardian.id).label('guardian_count')
        ).select_from(Guardian).outerjoin(StudentGuardian).group_by(Guardian.id).all()
        
        children_distribution = {}
        for children_count, guardian_count in children_stats:
            key = f"{children_count}명" if children_count > 0 else "0명"
            children_distribution[key] = children_distribution.get(key, 0) + guardian_count
        
        return {
            'total_guardians': total_guardians,
            'relationship_distribution': {
                str(relationship.value if relationship else '기타'): count 
                for relationship, count in relationship_stats
            },
            'communication_preferences': communication_stats,
            'children_distribution': children_distribution
        }
    
    def import_from_excel(self, file_path: str) -> dict:
        """엑셀 파일에서 보호자 데이터 가져오기"""
        try:
            df = pd.read_excel(file_path)
            
            success_count = 0
            error_count = 0
            errors = []
            
            # 관계 매핑
            relationship_mapping = {
                '아버지': RelationshipType.FATHER,
                '어머니': RelationshipType.MOTHER,
                '할아버지': RelationshipType.GRANDFATHER,
                '할머니': RelationshipType.GRANDMOTHER,
                '삼촌': RelationshipType.UNCLE,
                '이모': RelationshipType.AUNT,
                '보호자': RelationshipType.GUARDIAN,
                '기타': RelationshipType.OTHER
            }
            
            for index, row in df.iterrows():
                try:
                    guardian_data = {
                        'name': row.get('이름'),
                        'relationship': relationship_mapping.get(row.get('관계'), RelationshipType.OTHER),
                        'phone': str(row.get('연락처', '')),
                        'email': row.get('이메일'),
                        'occupation': row.get('직업'),
                        'workplace': row.get('직장'),
                        'work_phone': str(row.get('직장전화', '')),
                        'postal_code': str(row.get('우편번호', '')),
                        'road_address': row.get('주소'),
                        'detail_address': row.get('상세주소'),
                        'is_primary': row.get('주보호자') == 'Y',
                    }
                    
                    # 필수 필드 검증
                    if not guardian_data['name']:
                        raise ValueError("이름은 필수입니다.")
                    if not guardian_data['phone']:
                        raise ValueError("연락처는 필수입니다.")
                    
                    self.create(guardian_data)
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"행 {index + 2}: {str(e)}")
            
            return {
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors
            }
            
        except Exception as e:
            raise Exception(f"엑셀 파일 처리 실패: {str(e)}")
    
    def export_to_excel(self, file_path: str, guardians: List[Guardian] = None) -> str:
        """보호자 데이터를 엑셀로 내보내기"""
        try:
            if guardians is None:
                guardians = self.get_all()
            
            data = []
            for guardian in guardians:
                data.append({
                    'ID': guardian.id,
                    '이름': guardian.name,
                    '관계': guardian.relationship_type.value,
                    '연락처': guardian.phone,
                    '이메일': guardian.email or '',
                    '직업': guardian.occupation or '',
                    '직장': guardian.workplace or '',
                    '직장전화': guardian.work_phone or '',
                    '우편번호': guardian.postal_code or '',
                    '주소': guardian.road_address or '',
                    '상세주소': guardian.detail_address or '',
                    '주보호자': 'Y' if guardian.is_primary else 'N',
                    'SMS수신': 'Y' if guardian.sms_enabled else 'N',
                    '이메일수신': 'Y' if guardian.email_enabled else 'N',
                    '카카오톡수신': 'Y' if guardian.kakao_enabled else 'N',
                    '전화수신': 'Y' if guardian.phone_enabled else 'N',
                    '등록일': guardian.created_at.strftime('%Y-%m-%d %H:%M')
                })
            
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            return file_path
            
        except Exception as e:
            raise Exception(f"엑셀 내보내기 실패: {str(e)}")