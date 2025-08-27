import streamlit as st
import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from src.services.database import init_database
from src.pages import home, students, courses
from src.utils.auth import check_authentication, logout
from src.utils.config import load_config

# 페이지 설정
st.set_page_config(
    page_title="학원 관리 시스템",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 설정 로드
config = load_config()

# 데이터베이스 초기화
init_database()

# 사용자 정의 CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .sidebar-content {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # 인증 확인
    if not check_authentication():
        st.error("로그인이 필요합니다.")
        return
    
    # 메인 헤더
    st.markdown("""
    <div class="main-header">
        <h1>🎓 학원 종합 관리 시스템</h1>
        <p>효율적인 학원 운영을 위한 통합 솔루션</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 사이드바 메뉴
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-content">
            <h3>📋 메뉴</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # 사용자 정보
        if 'user' in st.session_state:
            user = st.session_state.user
            st.success(f"👤 {user.get('name', '사용자')}님 환영합니다!")
            st.caption(f"권한: {user.get('role', 'staff')}")
        
        # 메뉴 선택
        menu_options = {
            "🏠 대시보드": "dashboard",
            "👨‍🎓 학생 관리": "students",
            "📚 수강과목 관리": "courses"
        }
        
        selected_menu = st.selectbox(
            "메뉴 선택",
            options=list(menu_options.keys()),
            key="main_menu"
        )
        
        # 로그아웃 버튼
        if st.button("🚪 로그아웃", type="secondary"):
            logout()
            st.rerun()
    
    # 선택된 페이지 렌더링
    page_key = menu_options[selected_menu]
    
    if page_key == "dashboard":
        home.render()
    elif page_key == "students":
        students.render()
    elif page_key == "courses":
        courses.render()

if __name__ == "__main__":
    main()