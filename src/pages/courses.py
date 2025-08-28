import streamlit as st
import pandas as pd
from datetime import datetime, date
from src.services.database import get_db_session
from src.services.course_service import CourseService
from src.services.student_service import StudentService
from src.models.database import CourseStatus, EnrollmentStatus, Subject, Course
import json

def render():
    """수강과목 관리 페이지 렌더링"""
    st.title("📚 수강과목 관리")
    
    # 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 과목 관리", 
        "🎯 수강과목 관리", 
        "👥 수강생 배정", 
        "📊 통계"
    ])
    
    db = get_db_session()
    
    try:
        course_service = CourseService(db)
        student_service = StudentService(db)
        
        with tab1:
            render_subject_management(course_service)
        
        with tab2:
            render_course_management(course_service)
        
        with tab3:
            render_enrollment_management(course_service, student_service)
        
        with tab4:
            render_course_statistics(course_service)
            
    except Exception as e:
        st.error(f"페이지 로딩 중 오류 발생: {str(e)}")
    finally:
        db.close()

def render_subject_management(course_service):
    """과목 관리"""
    st.subheader("📋 과목 관리")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 과목 목록
        subjects = course_service.get_subjects()
        
        if subjects:
            subject_data = []
            for subject in subjects:
                course_count = len(subject.courses) if subject.courses else 0
                subject_data.append({
                    "ID": subject.id,
                    "과목명": subject.name,
                    "설명": subject.description or "",
                    "수강과목 수": course_count,
                    "상태": "활성" if subject.is_active else "비활성",
                    "생성일": subject.created_at.strftime("%Y-%m-%d") if subject.created_at else ""
                })
            
            df = pd.DataFrame(subject_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("등록된 과목이 없습니다.")
    
    with col2:
        st.write("**새 과목 등록**")
        
        with st.form("subject_form"):
            subject_name = st.text_input("과목명*", placeholder="예: 수학, 영어, 과학")
            subject_description = st.text_area("설명", placeholder="과목에 대한 설명")
            
            if st.form_submit_button("📋 과목 등록", type="primary"):
                if not subject_name:
                    st.error("과목명을 입력해주세요.")
                else:
                    try:
                        subject_data = {
                            'name': subject_name,
                            'description': subject_description,
                            'is_active': True
                        }
                        
                        course_service.create_subject(subject_data)
                        st.success(f"'{subject_name}' 과목이 등록되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"과목 등록 실패: {str(e)}")

def render_course_management(course_service):
    """수강과목 관리"""
    st.subheader("🎯 수강과목 관리")
    
    # 검색 및 필터
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 검색", placeholder="수강과목명, 과목명, 레벨")
    
    with col2:
        subjects = course_service.get_subjects()
        subject_options = ["전체"] + [s.name for s in subjects]
        selected_subject = st.selectbox("과목 필터", subject_options)
    
    with col3:
        status_options = ["전체"] + [status.value for status in CourseStatus]
        selected_status = st.selectbox("상태", status_options)
    
    # 수강과목 목록 조회
    subject_id = None
    if selected_subject != "전체":
        subject_obj = next((s for s in subjects if s.name == selected_subject), None)
        subject_id = subject_obj.id if subject_obj else None
    
    status = None if selected_status == "전체" else selected_status
    
    courses = course_service.get_courses(
        subject_id=subject_id,
        status=status,
        search_term=search_term if search_term else None
    )
    
    # 수강과목 목록 표시
    if courses:
        course_data = []
        for course in courses:
            enrollment_count = course_service.count_enrollments(course.id)
            
            course_data.append({
                "선택": False,
                "ID": course.id,
                "수강과목명": course.name,
                "과목": course.subject.name if course.subject else "",
                "레벨": course.level or "",
                "정원": course.capacity,
                "현재인원": enrollment_count,
                "여유인원": course.capacity - enrollment_count,
                "시간": course.schedule_info or "",
                "상태": course.status.value,
                "시작일": course.start_date.strftime("%Y-%m-%d") if course.start_date else "",
                "종료일": course.end_date.strftime("%Y-%m-%d") if course.end_date else ""
            })
        
        df = pd.DataFrame(course_data)
        
        edited_df = st.data_editor(
            df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "선택": st.column_config.CheckboxColumn("선택", default=False)
            }
        )
        
        # 선택된 수강과목 상세 정보
        selected_indices = edited_df[edited_df["선택"] == True].index.tolist()
        
        if selected_indices:
            st.markdown("---")
            st.subheader("📚 선택된 수강과목 상세 정보")
            
            for idx in selected_indices:
                if idx < len(courses):
                    course = courses[idx]
                    render_course_detail(course, course_service)
    
    else:
        st.info("등록된 수강과목이 없습니다.")
    
    # 새 수강과목 등록
    st.markdown("---")
    st.subheader("➕ 새 수강과목 등록")
    
    with st.form("course_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            subjects = course_service.get_subjects()
            if not subjects:
                st.warning("먼저 과목을 등록해주세요.")
                st.form_submit_button("등록", disabled=True)
                return
            
            subject_options = [(s.id, s.name) for s in subjects]
            selected_subject_idx = st.selectbox(
                "과목*", 
                range(len(subject_options)),
                format_func=lambda x: subject_options[x][1]
            )
            
            course_name = st.text_input("수강과목명*", placeholder="예: 중등 수학 1학년")
            course_level = st.selectbox("레벨", ["", "초급", "중급", "고급", "심화"])
            capacity = st.number_input("정원", min_value=1, max_value=50, value=20)
        
        with col2:
            duration = st.number_input("수업시간(분)", min_value=30, max_value=300, value=120, step=30)
            schedule_info = st.text_input("수업시간", placeholder="예: 월수금 19:00-21:00")
            textbook = st.text_input("교재", placeholder="사용 교재명")
            
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                start_date = st.date_input("시작일")
            with col_date2:
                end_date = st.date_input("종료일")
        
        curriculum = st.text_area("커리큘럼", placeholder="수업 커리큘럼 설명")
        
        if st.form_submit_button("🎯 수강과목 등록", type="primary"):
            if not course_name:
                st.error("수강과목명을 입력해주세요.")
            else:
                try:
                    subject_id = subject_options[selected_subject_idx][0]
                    
                    course_data = {
                        'name': course_name,
                        'subject_id': subject_id,
                        'level': course_level if course_level else None,
                        'capacity': capacity,
                        'duration_minutes': duration,
                        'schedule_info': schedule_info,
                        'textbook': textbook,
                        'curriculum': curriculum,
                        'start_date': start_date,
                        'end_date': end_date if end_date > start_date else None,
                        'status': CourseStatus.ACTIVE
                    }
                    
                    course = course_service.create_course(course_data)
                    st.success(f"'{course_name}' 수강과목이 등록되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"수강과목 등록 실패: {str(e)}")

def render_course_detail(course, course_service):
    """수강과목 상세 정보"""
    st.write(f"### 📚 {course.name}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**기본 정보**")
        st.write(f"• 과목: {course.subject.name if course.subject else '없음'}")
        st.write(f"• 레벨: {course.level or '없음'}")
        st.write(f"• 정원: {course.capacity}명")
        st.write(f"• 수업시간: {course.duration_minutes}분")
        st.write(f"• 시간표: {course.schedule_info or '없음'}")
    
    with col2:
        st.write("**진행 정보**")
        enrollment_count = course_service.count_enrollments(course.id)
        st.write(f"• 현재 수강생: {enrollment_count}명")
        st.write(f"• 여유 정원: {course.capacity - enrollment_count}명")
        st.write(f"• 상태: {course.status.value}")
        st.write(f"• 시작일: {course.start_date.strftime('%Y-%m-%d') if course.start_date else '없음'}")
        st.write(f"• 종료일: {course.end_date.strftime('%Y-%m-%d') if course.end_date else '없음'}")
    
    if course.textbook:
        st.write(f"**교재**: {course.textbook}")
    
    if course.curriculum:
        st.write("**커리큘럼**")
        st.write(course.curriculum)
    
    # 수강생 목록
    enrollments = course_service.get_course_enrollments(course.id)
    if enrollments:
        st.write("**수강생 목록**")
        student_names = [enrollment.student.name for enrollment in enrollments if enrollment.student]
        st.write(", ".join(student_names))

def render_enrollment_management(course_service, student_service):
    """수강생 배정 관리"""
    st.subheader("👥 수강생 배정 관리")
    
    # 수강과목 선택
    courses = course_service.get_courses(status="진행중")
    if not courses:
        st.warning("진행중인 수강과목이 없습니다.")
        return
    
    course_options = [(c.id, f"{c.name} ({c.subject.name})") for c in courses]
    selected_course_idx = st.selectbox(
        "수강과목 선택",
        range(len(course_options)),
        format_func=lambda x: course_options[x][1]
    )
    
    if selected_course_idx is not None:
        course_id = course_options[selected_course_idx][0]
        course = course_service.get_course(course_id)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**현재 수강생**")
            enrollments = course_service.get_course_enrollments(course_id)
            
            if enrollments:
                for enrollment in enrollments:
                    col_student, col_action = st.columns([3, 1])
                    with col_student:
                        st.write(f"• {enrollment.student.name} ({enrollment.student.academy_id})")
                    with col_action:
                        if st.button("❌", key=f"drop_{enrollment.id}"):
                            try:
                                course_service.unenroll(enrollment.id)
                                st.success(f"{enrollment.student.name} 학생이 수강 취소되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"수강 취소 실패: {str(e)}")
            else:
                st.info("수강중인 학생이 없습니다.")
        
        with col2:
            st.write("**수강 가능한 학생**")
            available_students = course_service.get_available_students(course_id)
            
            if available_students:
                for student in available_students:
                    col_student, col_action = st.columns([3, 1])
                    with col_student:
                        st.write(f"• {student.name} ({student.academy_id})")
                    with col_action:
                        if st.button("➕", key=f"enroll_{student.id}_{course_id}"):
                            try:
                                course_service.enroll(student.id, course_id)
                                st.success(f"{student.name} 학생이 수강 등록되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"수강 등록 실패: {str(e)}")
            else:
                st.info("수강 가능한 학생이 없습니다.")

def render_course_statistics(course_service):
    """수강과목 통계"""
    st.subheader("📊 수강과목 통계")
    
    try:
        stats = course_service.get_course_statistics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 수강과목", f"{stats['total_courses']}개")
        
        with col2:
            st.metric("진행중 수강과목", f"{stats['active_courses']}개")
        
        with col3:
            st.metric("총 과목", f"{stats['total_subjects']}개")
        
        with col4:
            st.metric("총 수강생", f"{stats['total_enrollments']}명")
        
        # 인기 수강과목
        st.subheader("🔥 인기 수강과목 TOP 5")
        popular_courses = course_service.get_popular_courses(5)
        
        if popular_courses:
            popular_data = []
            for i, course in enumerate(popular_courses, 1):
                popular_data.append({
                    "순위": i,
                    "수강과목": course['course_name'],
                    "과목": course['subject_name'],
                    "수강생 수": f"{course['enrollment_count']}명"
                })
            
            df = pd.DataFrame(popular_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("수강 데이터가 없습니다.")
            
    except Exception as e:
        st.error(f"통계 로딩 실패: {str(e)}")

