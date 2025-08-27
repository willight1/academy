import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.database import Base
from src.utils.config import get_database_url

# 데이터베이스 엔진 및 세션 설정
engine = None
SessionLocal = None

def init_database():
    """데이터베이스 초기화"""
    global engine, SessionLocal
    
    try:
        # 데이터베이스 디렉토리 생성
        os.makedirs("database", exist_ok=True)
        
        # 데이터베이스 URL 가져오기
        database_url = get_database_url()
        
        # 엔진 생성
        engine = create_engine(
            database_url,
            echo=False,  # SQL 로그 출력 여부
            pool_pre_ping=True
        )
        
        # 세션 팩토리 생성
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        
        # 초기 데이터 생성
        create_initial_data()
        
        print("✅ 데이터베이스 초기화 완료")
        
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        raise

def get_db():
    """데이터베이스 세션 가져오기"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """데이터베이스 세션 가져오기 (단일 세션)"""
    return SessionLocal()

def create_initial_data():
    """초기 데이터 생성"""
    from src.models.database import User, UserRole, Subject
    from src.utils.security import hash_password
    
    db = SessionLocal()
    
    try:
        # 관리자 계정 확인 및 생성
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@academy.com",
                password_hash=hash_password("admin123"),
                name="시스템 관리자",
                role=UserRole.ADMIN,
                phone="010-0000-0000"
            )
            db.add(admin_user)
            print("✅ 관리자 계정 생성 완료")
        
        # 기본 과목 확인 및 생성
        subjects_data = [
            {"name": "수학", "description": "수학 과목"},
            {"name": "영어", "description": "영어 과목"},
            {"name": "국어", "description": "국어 과목"},
            {"name": "과학", "description": "과학 과목"},
            {"name": "사회", "description": "사회 과목"},
            {"name": "코딩", "description": "프로그래밍 과목"}
        ]
        
        for subject_data in subjects_data:
            existing_subject = db.query(Subject).filter(Subject.name == subject_data["name"]).first()
            if not existing_subject:
                subject = Subject(**subject_data)
                db.add(subject)
        
        db.commit()
        print("✅ 초기 데이터 생성 완료")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 초기 데이터 생성 실패: {e}")
        raise
    finally:
        db.close()

def reset_database():
    """데이터베이스 리셋 (개발용)"""
    global engine
    
    if engine:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        create_initial_data()
        print("✅ 데이터베이스 리셋 완료")

# 데이터베이스 연결 테스트
def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return False