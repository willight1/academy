from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import pandas as pd

from src.models.database import Course, Subject, Enrollment, Student, EnrollmentStatus, CourseStatus


class CourseService:
    def __init__(self, db: Session):
        self.db = db

    # ========== 과목 관리 ==========
    def create_subject(self, subject_data: Dict[str, Any]) -> Subject:
        """새 과목 생성"""
        subject = Subject(**subject_data)
        self.db.add(subject)
        self.db.commit()
        self.db.refresh(subject)
        return subject

    def get_all_subjects(self, active_only: bool = True) -> List[Subject]:
        """모든 과목 조회"""
        query = self.db.query(Subject)
        if active_only:
            query = query.filter(Subject.is_active == True)
        return query.order_by(Subject.name).all()

    def get_subject_by_id(self, subject_id: int) -> Optional[Subject]:
        """ID로 과목 조회"""
        return self.db.query(Subject).filter(Subject.id == subject_id).first()

    def update_subject(self, subject_id: int, subject_data: Dict[str, Any]) -> Optional[Subject]:
        """과목 정보 수정"""
        subject = self.get_subject_by_id(subject_id)
        if not subject:
            return None
            
        for key, value in subject_data.items():
            if hasattr(subject, key):
                setattr(subject, key, value)
        
        self.db.commit()
        self.db.refresh(subject)
        return subject

    def delete_subject(self, subject_id: int) -> bool:
        """과목 삭제 (soft delete)"""
        subject = self.get_subject_by_id(subject_id)
        if not subject:
            return False
            
        subject.is_active = False
        self.db.commit()
        return True

    # ========== 수강과목 관리 ==========
    def create_course(self, course_data: Dict[str, Any]) -> Course:
        """새 수강과목 생성"""
        course = Course(**course_data)
        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)
        return course

    def get_all_courses(self, 
                       subject_id: Optional[int] = None,
                       status: Optional[str] = None,
                       search: Optional[str] = None) -> List[Course]:
        """모든 수강과목 조회"""
        query = self.db.query(Course).join(Subject)
        
        if subject_id:
            query = query.filter(Course.subject_id == subject_id)
        
        if status:
            query = query.filter(Course.status == CourseStatus(status))
        
        if search:
            query = query.filter(
                or_(
                    Course.name.contains(search),
                    Subject.name.contains(search),
                    Course.level.contains(search)
                )
            )
        
        return query.order_by(Course.name).all()

    def get_course_by_id(self, course_id: int) -> Optional[Course]:
        """ID로 수강과목 조회"""
        return self.db.query(Course).filter(Course.id == course_id).first()

    def update_course(self, course_id: int, course_data: Dict[str, Any]) -> Optional[Course]:
        """수강과목 정보 수정"""
        course = self.get_course_by_id(course_id)
        if not course:
            return None
            
        for key, value in course_data.items():
            if hasattr(course, key):
                setattr(course, key, value)
        
        self.db.commit()
        self.db.refresh(course)
        return course

    def delete_course(self, course_id: int) -> bool:
        """수강과목 삭제"""
        course = self.get_course_by_id(course_id)
        if not course:
            return False
        
        # 수강중인 학생이 있는지 확인
        active_enrollments = self.db.query(Enrollment).filter(
            and_(
                Enrollment.course_id == course_id,
                Enrollment.status == EnrollmentStatus.ACTIVE
            )
        ).count()
        
        if active_enrollments > 0:
            raise ValueError(f"수강중인 학생이 {active_enrollments}명 있어서 삭제할 수 없습니다.")
        
        self.db.delete(course)
        self.db.commit()
        return True

    # ========== 수강신청 관리 ==========
    def enroll_student(self, student_id: int, course_id: int, enrollment_data: Optional[Dict[str, Any]] = None) -> Enrollment:
        """학생 수강신청"""
        # 이미 수강중인지 확인
        existing_enrollment = self.db.query(Enrollment).filter(
            and_(
                Enrollment.student_id == student_id,
                Enrollment.course_id == course_id,
                Enrollment.status == EnrollmentStatus.ACTIVE
            )
        ).first()
        
        if existing_enrollment:
            raise ValueError("이미 이 수강과목에 등록되어 있습니다.")
        
        # 수강과목 정원 확인
        course = self.get_course_by_id(course_id)
        if not course:
            raise ValueError("존재하지 않는 수강과목입니다.")
        
        current_enrollments = self.get_course_enrollment_count(course_id)
        if current_enrollments >= course.capacity:
            raise ValueError("수강과목 정원이 초과되었습니다.")
        
        # 수강신청 생성
        enrollment_dict = {
            'student_id': student_id,
            'course_id': course_id,
            'enrollment_date': date.today(),
            'start_date': enrollment_data.get('start_date', date.today()) if enrollment_data else date.today(),
            'status': EnrollmentStatus.ACTIVE
        }
        
        if enrollment_data:
            enrollment_dict.update(enrollment_data)
        
        enrollment = Enrollment(**enrollment_dict)
        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment

    def drop_enrollment(self, enrollment_id: int) -> bool:
        """수강 포기"""
        enrollment = self.db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if not enrollment:
            return False
        
        enrollment.status = EnrollmentStatus.DROPPED
        enrollment.end_date = date.today()
        self.db.commit()
        return True

    def get_student_enrollments(self, student_id: int, active_only: bool = True) -> List[Enrollment]:
        """학생의 수강 목록"""
        query = self.db.query(Enrollment).filter(Enrollment.student_id == student_id)
        
        if active_only:
            query = query.filter(Enrollment.status == EnrollmentStatus.ACTIVE)
        
        return query.order_by(Enrollment.created_at.desc()).all()

    def get_course_enrollments(self, course_id: int, active_only: bool = True) -> List[Enrollment]:
        """수강과목의 수강생 목록"""
        query = self.db.query(Enrollment).filter(Enrollment.course_id == course_id)
        
        if active_only:
            query = query.filter(Enrollment.status == EnrollmentStatus.ACTIVE)
        
        return query.order_by(Enrollment.created_at).all()

    def get_course_enrollment_count(self, course_id: int) -> int:
        """수강과목의 현재 수강생 수"""
        return self.db.query(Enrollment).filter(
            and_(
                Enrollment.course_id == course_id,
                Enrollment.status == EnrollmentStatus.ACTIVE
            )
        ).count()

    def get_course_with_students(self, course_id: int) -> Optional[Dict[str, Any]]:
        """수강과목과 수강생 정보 함께 조회"""
        course = self.get_course_by_id(course_id)
        if not course:
            return None
        
        enrollments = self.get_course_enrollments(course_id)
        
        return {
            'course': course,
            'enrollments': enrollments,
            'student_count': len(enrollments),
            'available_slots': course.capacity - len(enrollments)
        }

    # ========== 통계 및 분석 ==========
    def get_course_statistics(self) -> Dict[str, Any]:
        """수강과목 통계"""
        total_courses = self.db.query(Course).count()
        active_courses = self.db.query(Course).filter(Course.status == CourseStatus.ACTIVE).count()
        total_subjects = self.db.query(Subject).filter(Subject.is_active == True).count()
        total_enrollments = self.db.query(Enrollment).filter(Enrollment.status == EnrollmentStatus.ACTIVE).count()
        
        return {
            'total_courses': total_courses,
            'active_courses': active_courses,
            'total_subjects': total_subjects,
            'total_enrollments': total_enrollments
        }

    def get_popular_courses(self, limit: int = 5) -> List[Dict[str, Any]]:
        """인기 수강과목 Top N"""
        popular_courses = self.db.query(
            Course.id,
            Course.name,
            Subject.name.label('subject_name'),
            func.count(Enrollment.id).label('enrollment_count')
        ).join(Subject).join(Enrollment).filter(
            Enrollment.status == EnrollmentStatus.ACTIVE
        ).group_by(Course.id, Course.name, Subject.name).order_by(
            func.count(Enrollment.id).desc()
        ).limit(limit).all()
        
        return [
            {
                'course_id': course.id,
                'course_name': course.name,
                'subject_name': course.subject_name,
                'enrollment_count': course.enrollment_count
            }
            for course in popular_courses
        ]

    # ========== 검색 및 필터링 ==========
    def search_available_courses_for_student(self, student_id: int) -> List[Course]:
        """학생이 수강 가능한 수강과목 검색 (이미 수강중이지 않은 과목)"""
        enrolled_course_ids = self.db.query(Enrollment.course_id).filter(
            and_(
                Enrollment.student_id == student_id,
                Enrollment.status == EnrollmentStatus.ACTIVE
            )
        ).subquery()
        
        available_courses = self.db.query(Course).filter(
            and_(
                Course.status == CourseStatus.ACTIVE,
                ~Course.id.in_(enrolled_course_ids)
            )
        ).order_by(Course.name).all()
        
        return available_courses

    def get_students_not_in_course(self, course_id: int) -> List[Student]:
        """특정 수강과목에 등록되지 않은 학생 목록"""
        enrolled_student_ids = self.db.query(Enrollment.student_id).filter(
            and_(
                Enrollment.course_id == course_id,
                Enrollment.status == EnrollmentStatus.ACTIVE
            )
        ).subquery()
        
        available_students = self.db.query(Student).filter(
            ~Student.id.in_(enrolled_student_ids)
        ).order_by(Student.name).all()
        
        return available_students