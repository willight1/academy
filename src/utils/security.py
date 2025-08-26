import bcrypt
import secrets
from datetime import datetime, timedelta
from jose import JWTError, jwt
from src.utils.config import load_config

config = load_config()

def hash_password(password: str) -> str:
    """비밀번호 해시화"""
    salt = bcrypt.gensalt(rounds=config["bcrypt_rounds"])
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def generate_access_token(data: dict, expires_delta: timedelta = None):
    """액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config["jwt_secret"], algorithm="HS256")
    return encoded_jwt

def verify_token(token: str):
    """토큰 검증"""
    try:
        payload = jwt.decode(token, config["jwt_secret"], algorithms=["HS256"])
        return payload
    except JWTError:
        return None

def generate_academy_id() -> str:
    """학원 등록번호 생성"""
    timestamp = datetime.now().strftime("%y%m%d")
    random_suffix = secrets.token_hex(2).upper()
    return f"AC{timestamp}{random_suffix}"

def generate_secure_filename(filename: str) -> str:
    """보안 파일명 생성"""
    file_extension = filename.split('.')[-1] if '.' in filename else ''
    secure_name = secrets.token_hex(16)
    return f"{secure_name}.{file_extension}" if file_extension else secure_name