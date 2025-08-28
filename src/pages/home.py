import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
from src.services.database import get_db_session
from src.services.student_service import StudentService
from src.services.guardian_service import GuardianService
from src.models.database import Student, Guardian, StudentStatus
from sqlalchemy import func

def render():
    """대시보드 페이지 렌더링"""
    st.title("📊 대시보드")
    
    # 데이터베이스 세션
    db = get_db_session()
    
    try:
        # 서비스 인스턴스
        student_service = StudentService(db)
        guardian_service = GuardianService(db)
        
        # 주요 지표 카드
        render_key_metrics(db, student_service, guardian_service)
        
        # 차트 영역
        col1, col2 = st.columns(2)
        
        with col1:
            render_student_enrollment_chart(db)
        
        with col2:
            render_student_status_chart(db)
        
        # 최근 활동
        render_recent_activities(db)
        
    except Exception as e:
        st.error(f"대시보드 로딩 중 오류 발생: {str(e)}")
    finally:
        db.close()

def render_key_metrics(db, student_service, guardian_service):
    """주요 지표 카드"""
    # 통계 데이터 가져오기
    students = student_service.get_all()
    guardians = guardian_service.get_all()
    
    total_students = len(students)
    active_students = len([s for s in students if s.status == StudentStatus.ACTIVE])
    total_guardians = len(guardians)
    
    # 최근 30일 등록 학생
    recent_students = len([s for s in students if s.enrollment_date and (datetime.now().date() - s.enrollment_date).days <= 30])
    
    # 지표 카드 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📚 총 학생 수",
            value=f"{total_students}명",
            delta=f"활성: {active_students}명"
        )
    
    with col2:
        st.metric(
            label="👨‍👩‍👧‍👦 총 보호자 수",
            value=f"{total_guardians}명"
        )
    
    with col3:
        st.metric(
            label="📈 최근 30일 신규",
            value=f"{recent_students}명"
        )
    
    with col4:
        avg_guardians = total_guardians / total_students if total_students > 0 else 0
        st.metric(
            label="👥 평균 보호자 수",
            value=f"{avg_guardians:.1f}명/학생"
        )

def render_student_enrollment_chart(db):
    """학생 등록 현황 차트"""
    st.subheader("📈 월별 신입생 등록 현황")
    
    # 최근 12개월 데이터
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365)
    
    enrollments = db.query(
        func.strftime('%Y-%m', Student.enrollment_date).label('month'),
        func.count(Student.id).label('count')
    ).filter(
        Student.enrollment_date >= start_date
    ).group_by('month').order_by('month').all()
    
    if enrollments:
        df = pd.DataFrame(enrollments, columns=['월', '신입생 수'])
        df['월'] = pd.to_datetime(df['월'])
        
        fig = px.line(df, x='월', y='신입생 수', markers=True,
                     title="월별 신입생 등록 추이")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("등록 데이터가 없습니다.")

def render_student_status_chart(db):
    """학생 상태별 분포 차트"""
    st.subheader("👥 학생 상태별 분포")
    
    status_count = db.query(
        Student.status,
        func.count(Student.id).label('count')
    ).group_by(Student.status).all()
    
    if status_count:
        labels = [status.value for status, _ in status_count]
        values = [count for _, count in status_count]
        
        fig = px.pie(values=values, names=labels, title="학생 상태별 분포")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("학생 데이터가 없습니다.")



def render_recent_activities(db):
    """최근 활동"""
    st.subheader("🕒 최근 활동")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📚 최근 등록 학생**")
        recent_students = db.query(Student).order_by(
            Student.created_at.desc()
        ).limit(5).all()
        
        if recent_students:
            for student in recent_students:
                st.write(f"• {student.name} ({student.academy_id}) - {student.created_at.strftime('%m/%d %H:%M')}")
        else:
            st.info("등록된 학생이 없습니다.")
    
    with col2:
        st.write("**👨‍👩‍👧‍👦 최근 등록 보호자**")
        recent_guardians = db.query(Guardian).order_by(
            Guardian.created_at.desc()
        ).limit(5).all()
        
        if recent_guardians:
            for guardian in recent_guardians:
                st.write(f"• {guardian.name} ({guardian.relationship_type.value}) - {guardian.created_at.strftime('%m/%d %H:%M')}")
        else:
            st.info("등록된 보호자가 없습니다.")
    
    # 알림 및 공지사항
    st.subheader("📢 알림")
    
    # 생일자 알림
    today_birthday = db.query(Student).filter(
        func.strftime('%m-%d', Student.birth_date) == datetime.now().strftime('%m-%d')
    ).count()
    
    if today_birthday > 0:
        st.success(f"🎂 오늘 생일인 학생이 {today_birthday}명 있습니다!")
    else:
        st.info("오늘은 생일인 학생이 없습니다.")