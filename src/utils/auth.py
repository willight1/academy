import streamlit as st
from src.services.database import get_db_session
from src.models.database import User
from src.utils.security import verify_password, generate_access_token, verify_token

def login(username: str, password: str) -> bool:
    """로그인 처리"""
    db = get_db_session()
    
    try:
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if user and user.is_active and verify_password(password, user.password_hash):
            # 세션에 사용자 정보 저장
            st.session_state.authenticated = True
            st.session_state.user = {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "email": user.email,
                "role": user.role.value,
                "phone": user.phone
            }
            
            # JWT 토큰 생성
            token_data = {"user_id": user.id, "username": user.username}
            access_token = generate_access_token(token_data)
            st.session_state.access_token = access_token
            
            # 마지막 로그인 시간 업데이트
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.commit()
            
            return True
        
        return False
        
    except Exception as e:
        print(f"로그인 오류: {e}")
        return False
    finally:
        db.close()

def logout():
    """로그아웃 처리"""
    if 'authenticated' in st.session_state:
        del st.session_state.authenticated
    if 'user' in st.session_state:
        del st.session_state.user
    if 'access_token' in st.session_state:
        del st.session_state.access_token

def check_authentication() -> bool:
    """인증 상태 확인"""
    if 'authenticated' not in st.session_state:
        show_login_form()
        return False
    
    return st.session_state.authenticated

def show_login_form():
    """로그인 폼 표시"""
    st.title("🎓 학원 관리 시스템 로그인")
    
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### 로그인")
            username = st.text_input("사용자명 또는 이메일", placeholder="admin")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            
            submitted = st.form_submit_button("로그인", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("사용자명과 비밀번호를 모두 입력해주세요.")
                    return
                
                if login(username, password):
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.error("로그인 실패. 사용자명과 비밀번호를 확인해주세요.")
    
    # 기본 계정 정보 안내
    with st.expander("🔑 기본 계정 정보"):
        st.info("""
        **관리자 계정:**
        - 사용자명: admin
        - 비밀번호: admin123
        
        ⚠️ 초기 설정 후 반드시 비밀번호를 변경해주세요.
        """)

def get_current_user():
    """현재 로그인한 사용자 정보 가져오기"""
    if 'user' in st.session_state:
        return st.session_state.user
    return None

def has_permission(required_role: str = None, required_permissions: list = None) -> bool:
    """권한 확인"""
    user = get_current_user()
    if not user:
        return False
    
    user_role = user.get('role', 'staff')
    
    # 관리자는 모든 권한 보유
    if user_role == 'admin':
        return True
    
    # 역할 기반 권한 확인
    if required_role:
        role_hierarchy = {
            'admin': 4,
            'teacher': 3,
            'counselor': 2,
            'staff': 1
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    return True

def require_permission(required_role: str = None, required_permissions: list = None):
    """권한 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not has_permission(required_role, required_permissions):
                st.error("이 기능에 접근할 권한이 없습니다.")
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator