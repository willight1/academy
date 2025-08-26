import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def load_config():
    """설정 로드"""
    return {
        "app_name": os.getenv("APP_NAME", "학원 관리 시스템"),
        "app_version": os.getenv("APP_VERSION", "1.0.0"),
        "debug": os.getenv("DEBUG", "True").lower() == "true",
        "timezone": os.getenv("TIMEZONE", "Asia/Seoul"),
        "secret_key": os.getenv("SECRET_KEY", "your-secret-key-here"),
        "jwt_secret": os.getenv("JWT_SECRET_KEY", "your-jwt-secret-here"),
        "bcrypt_rounds": int(os.getenv("BCRYPT_ROUNDS", "12")),
        "upload_folder": os.getenv("UPLOAD_FOLDER", "uploads"),
        "max_file_size": int(os.getenv("MAX_FILE_SIZE", "5242880")),
    }

def get_database_url():
    """데이터베이스 URL 가져오기"""
    return os.getenv("DATABASE_URL", "sqlite:///database/academy.db")

def get_email_config():
    """이메일 설정 가져오기"""
    return {
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "email_user": os.getenv("EMAIL_USER"),
        "email_password": os.getenv("EMAIL_PASSWORD"),
    }

def get_sms_config():
    """SMS 설정 가져오기"""
    return {
        "twilio_account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
        "twilio_auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
        "twilio_phone_number": os.getenv("TWILIO_PHONE_NUMBER"),
    }

def get_kakao_config():
    """카카오톡 설정 가져오기"""
    return {
        "api_key": os.getenv("KAKAO_API_KEY"),
        "sender_key": os.getenv("KAKAO_SENDER_KEY"),
    }

def ensure_upload_directory():
    """업로드 디렉토리 확인 및 생성"""
    upload_folder = load_config()["upload_folder"]
    Path(upload_folder).mkdir(parents=True, exist_ok=True)
    Path(f"{upload_folder}/profiles").mkdir(parents=True, exist_ok=True)
    Path(f"{upload_folder}/documents").mkdir(parents=True, exist_ok=True)
    Path(f"{upload_folder}/temp").mkdir(parents=True, exist_ok=True)