from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from src.models.database import Student, Guardian, StudentGuardian, Gender, StudentStatus
from src.utils.security import generate_academy_id
from datetime import datetime, date
from typing import List, Optional, Dict
import pandas as pd

class StudentService:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, student_info: dict) -> Student:
        """학생 생성"""
        try:
            # 학원 등록번호 자동 생성
            student_info['academy_id'] = self.generate_unique_academy_id()
            
            # 생년월일 문자열을 date 객체로 변환
            if isinstance(student_info.get('birth_date'), str):
                student_info['birth_date'] = datetime.strptime(student_info['birth_date'], '%Y-%m-%d').date()
            
            # 입학일 처리
            if isinstance(student_info.get('enrollment_date'), str):
                student_info['enrollment_date'] = datetime.strptime(student_info['enrollment_date'], '%Y-%m-%d').date()
            elif not student_info.get('enrollment_date'):
                student_info['enrollment_date'] = date.today()
            
            new_student = Student(**student_info)
            self.db.add(new_student)
            self.db.commit()
            self.db.refresh(new_student)
            
            return new_student
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"학생 생성 실패: {str(e)}")
    
    def get_by_id(self, student_id: int) -> Optional[Student]:
        """ID로 학생 조회"""
        return self.db.query(Student).filter(Student.id == student_id).first()
    
    def get_by_academy_id(self, academy_id: str) -> Optional[Student]:
        """학원 등록번호로 학생 조회"""
        return self.db.query(Student).filter(Student.academy_id == academy_id).first()
    
    def get_all(self, status: str = None, search: str = None, limit: int = None) -> List[Student]:
        """모든 학생 조회"""
        query = self.db.query(Student)
        
        # 상태 필터
        if status:
            # status가 문자열인 경우 해당하는 enum 찾기
            if isinstance(status, str):
                status_enum = None
                for s in StudentStatus:
                    if s.value == status or s.name.lower() == status.lower():
                        status_enum = s
                        break
                if status_enum:
                    query = query.filter(Student.status == status_enum)
            else:
                query = query.filter(Student.status == status)
        
        # 검색 필터
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Student.name.ilike(search_pattern),
                    Student.academy_id.ilike(search_pattern),
                    Student.school_name.ilike(search_pattern),
                    Student.phone.ilike(search_pattern)
                )
            )
        
        # 정렬
        query = query.order_by(Student.name)
        
        # 제한
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def update(self, student_id: int, data: dict) -> Student:
        """학생 정보 수정"""
        try:
            student = self.get_by_id(student_id)
            if not student:
                raise Exception("학생을 찾을 수 없습니다.")
            
            # 날짜 필드 처리
            if 'birth_date' in data and isinstance(data['birth_date'], str):
                data['birth_date'] = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            
            if 'enrollment_date' in data and isinstance(data['enrollment_date'], str):
                data['enrollment_date'] = datetime.strptime(data['enrollment_date'], '%Y-%m-%d').date()
            
            # 업데이트
            for field_name, value in data.items():
                if hasattr(student, field_name):
                    setattr(student, field_name, value)
            
            student.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(student)
            
            return student
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"학생 정보 수정 실패: {str(e)}")
    
    def delete(self, student_id: int) -> bool:
        """학생 삭제 (비활성화)"""
        try:
            student = self.get_by_id(student_id)
            if not student:
                raise Exception("학생을 찾을 수 없습니다.")
            
            student.status = StudentStatus.INACTIVE
            student.updated_at = datetime.utcnow()
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"학생 삭제 실패: {str(e)}")
    
    def link_guardian(self, student_id: int, guardian_id: int) -> bool:
        """학생에 보호자 추가"""
        try:
            # 기존 관계 확인
            existing_link = self.db.query(StudentGuardian).filter(
                and_(
                    StudentGuardian.student_id == student_id,
                    StudentGuardian.guardian_id == guardian_id
                )
            ).first()
            
            if existing_link:
                return True  # 이미 연결됨
            
            # 새 관계 추가
            new_relationship = StudentGuardian(
                student_id=student_id,
                guardian_id=guardian_id
            )
            self.db.add(new_relationship)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"보호자 연결 실패: {str(e)}")
    
    def unlink_guardian(self, student_id: int, guardian_id: int) -> bool:
        """학생에서 보호자 제거"""
        try:
            existing_link = self.db.query(StudentGuardian).filter(
                and_(
                    StudentGuardian.student_id == student_id,
                    StudentGuardian.guardian_id == guardian_id
                )
            ).first()
            
            if existing_link:
                self.db.delete(existing_link)
                self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"보호자 연결 해제 실패: {str(e)}")
    
    def get_by_guardian(self, guardian_id: int) -> List[Student]:
        """보호자의 자녀 목록 조회"""
        return self.db.query(Student).join(StudentGuardian).filter(
            StudentGuardian.guardian_id == guardian_id
        ).all()
    
    def get_statistics(self) -> dict:
        """학생 통계"""
        total_students = self.db.query(Student).count()
        active_students = self.db.query(Student).filter(Student.status == StudentStatus.ACTIVE).count()
        
        # 성별 통계
        gender_stats = self.db.query(
            Student.gender,
            func.count(Student.id)
        ).group_by(Student.gender).all()
        
        # 학년별 통계
        grade_stats = self.db.query(
            Student.grade,
            func.count(Student.id)
        ).filter(Student.grade.isnot(None)).group_by(Student.grade).all()
        
        # 월별 신입생 통계 (최근 12개월)
        monthly_enrollments = self.db.query(
            func.strftime('%Y-%m', Student.enrollment_date).label('month'),
            func.count(Student.id)
        ).filter(
            Student.enrollment_date >= datetime.now().date().replace(month=1, day=1)
        ).group_by('month').all()
        
        return {
            'total_students': total_students,
            'active_students': active_students,
            'inactive_students': total_students - active_students,
            'gender_distribution': {str(gender): count for gender, count in gender_stats},
            'grade_distribution': {f"{grade}학년": count for grade, count in grade_stats if grade},
            'monthly_enrollments': {month: count for month, count in monthly_enrollments}
        }
    
    def generate_unique_academy_id(self) -> str:
        """고유한 학원 등록번호 생성"""
        while True:
            academy_id = generate_academy_id()
            existing = self.db.query(Student).filter(Student.academy_id == academy_id).first()
            if not existing:
                return academy_id
    
    def import_from_excel(self, file_path: str) -> dict:
        """엑셀 파일에서 학생 데이터 가져오기"""
        try:
            df = pd.read_excel(file_path)
            
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    student_data = {
                        'name': row.get('이름'),
                        'gender': Gender.MALE if row.get('성별') == '남' else Gender.FEMALE,
                        'birth_date': pd.to_datetime(row.get('생년월일')).date(),
                        'phone': str(row.get('연락처', '')),
                        'school_name': row.get('학교명'),
                        'grade': int(row.get('학년', 0)) if pd.notna(row.get('학년')) else None,
                        'postal_code': str(row.get('우편번호', '')),
                        'road_address': row.get('주소'),
                        'detail_address': row.get('상세주소'),
                    }
                    
                    # 필수 필드 검증
                    if not student_data['name']:
                        raise ValueError("이름은 필수입니다.")
                    
                    self.create(student_data)
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
    
    def export_to_excel(self, file_path: str, students: List[Student] = None) -> str:
        """학생 데이터를 엑셀로 내보내기"""
        try:
            if students is None:
                students = self.get_all()
            
            data = []
            for student in students:
                data.append({
                    '학원등록번호': student.academy_id,
                    '이름': student.name,
                    '성별': '남' if student.gender == Gender.MALE else '여',
                    '생년월일': student.birth_date.strftime('%Y-%m-%d'),
                    '연락처': student.phone or '',
                    '이메일': student.email or '',
                    '학교명': student.school_name or '',
                    '학년': student.grade or '',
                    '우편번호': student.postal_code or '',
                    '주소': student.road_address or '',
                    '상세주소': student.detail_address or '',
                    '입학일': student.enrollment_date.strftime('%Y-%m-%d'),
                    '상태': student.status.value,
                    '등록일': student.created_at.strftime('%Y-%m-%d %H:%M')
                })
            
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            return file_path
            
        except Exception as e:
            raise Exception(f"엑셀 내보내기 실패: {str(e)}")