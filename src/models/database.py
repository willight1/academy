from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Date, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

# Enum 정의
class Gender(enum.Enum):
    MALE = "남"
    FEMALE = "여"

class UserRole(enum.Enum):
    ADMIN = "관리자"
    TEACHER = "강사"
    COUNSELOR = "상담사"
    STAFF = "직원"

class StudentStatus(enum.Enum):
    ACTIVE = "재학"
    INACTIVE = "휴학"
    GRADUATED = "졸업"
    TRANSFERRED = "전학"

class RelationshipType(enum.Enum):
    FATHER = "아버지"
    MOTHER = "어머니" 
    GRANDFATHER = "할아버지"
    GRANDMOTHER = "할머니"
    UNCLE = "삼촌"
    AUNT = "이모/고모"
    GUARDIAN = "보호자"
    OTHER = "기타"


# 사용자 모델
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    role = Column(Enum(UserRole), default=UserRole.STAFF)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 학생 모델
class Student(Base):
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True)
    academy_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    
    # 주소
    postal_code = Column(String(10))
    road_address = Column(String(200))
    detail_address = Column(String(100))
    extra_address = Column(String(100))
    
    # 학교 정보
    school_name = Column(String(100))
    grade = Column(Integer)
    class_name = Column(String(20))
    
    # 학원 정보
    enrollment_date = Column(Date, default=datetime.utcnow().date())
    status = Column(Enum(StudentStatus), default=StudentStatus.ACTIVE)
    
    # 프로필 이미지
    profile_image_path = Column(String(500))
    
    # 응급 연락처
    emergency_contact_name = Column(String(100))
    emergency_contact_relationship = Column(String(50))
    emergency_contact_phone = Column(String(20))
    
    # 의료 정보
    allergies = Column(Text)
    medications = Column(Text)
    special_needs = Column(Text)
    
    # 메모
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    guardians = relationship("Guardian", secondary="student_guardians", back_populates="students")

# 보호자 모델
class Guardian(Base):
    __tablename__ = 'guardians'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    relationship_type = Column(Enum(RelationshipType), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100))
    
    # 주소
    postal_code = Column(String(10))
    road_address = Column(String(200))
    detail_address = Column(String(100))
    extra_address = Column(String(100))
    
    # 직업 정보
    occupation = Column(String(100))
    workplace = Column(String(100))
    work_phone = Column(String(20))
    
    # 응급 연락처
    emergency_contact_name = Column(String(100))
    emergency_contact_relationship = Column(String(50))
    emergency_contact_phone = Column(String(20))
    
    # 우선 연락처 여부
    is_primary = Column(Boolean, default=False)
    
    # 커뮤니케이션 설정
    sms_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    kakao_enabled = Column(Boolean, default=False)
    phone_enabled = Column(Boolean, default=False)
    
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    students = relationship("Student", secondary="student_guardians", back_populates="guardians")

# 학생-보호자 관계 테이블
class StudentGuardian(Base):
    __tablename__ = 'student_guardians'
    
    student_id = Column(Integer, ForeignKey('students.id'), primary_key=True)
    guardian_id = Column(Integer, ForeignKey('guardians.id'), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

