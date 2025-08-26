import streamlit as st
import pandas as pd
from datetime import datetime, date
from src.services.database import get_db_session
from src.services.student_service import StudentService
from src.services.guardian_service import GuardianService
from src.models.database import StudentStatus, Gender, RelationshipType
from src.utils.auth import require_permission
import tempfile
import os

def render():
    """학생 관리 페이지 렌더링"""
    st.title("👨‍🎓 학생 관리")
    
    # 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs(["📋 학생 목록", "➕ 학생 등록", "📤 엑셀 관리", "📊 통계"])
    
    db = get_db_session()
    
    try:
        student_service = StudentService(db)
        guardian_service = GuardianService(db)
        
        
        with tab1:
            render_student_list(student_service, guardian_service)
        
        with tab2:
            render_student_registration(student_service, guardian_service)
        
        with tab3:
            render_excel_management(student_service, guardian_service)
        
        with tab4:
            render_student_statistics(student_service, guardian_service)
            
    except Exception as e:
        st.error(f"페이지 로딩 중 오류 발생: {str(e)}")
    finally:
        db.close()

def render_student_list(student_service, guardian_service):
    """학생 목록 - 이름 클릭시 학생+보호자 정보 표시"""
    st.subheader("📋 학생 목록")
    
    # 검색 및 필터
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 검색", placeholder="이름, 학교, 연락처, 학원등록번호")
    
    with col2:
        status_filter = st.selectbox("상태", ["전체"] + [status.value for status in StudentStatus])
    
    with col3:
        st.write("")  # 간격
        if st.button("🔄 새로고침"):
            st.rerun()
    
    # 학생 목록 조회
    students = student_service.get_all_students(
        search=search_term,
        status=None if status_filter == "전체" else status_filter
    )
    
    if students:
        # 학생 정보를 데이터프레임으로 변환
        student_data = []
        for student in students:
            # 보호자 정보 가져오기
            guardians = guardian_service.get_guardians_by_student(student.id)
            guardian_names = ", ".join([g.name for g in guardians[:2]])  # 최대 2명만 표시
            if len(guardians) > 2:
                guardian_names += f" 외 {len(guardians)-2}명"
            
            # 주보호자 연락처
            primary_guardian = next((g for g in guardians if g.is_primary), guardians[0] if guardians else None)
            guardian_phone = primary_guardian.phone if primary_guardian else ""
            
            student_data.append({
                "선택": False,
                "학원번호": student.academy_id,
                "이름": student.name,
                "성별": student.gender.value if student.gender else "",
                "학교": student.school_name or "",
                "학년": f"{student.grade}학년" if student.grade else "",
                "학생연락처": student.phone or "",
                "보호자": guardian_names,
                "보호자연락처": guardian_phone,
                "상태": student.status.value,
                "등록일": student.enrollment_date.strftime("%Y-%m-%d") if student.enrollment_date else "",
                "ID": student.id
            })
        
        df = pd.DataFrame(student_data)
        
        # 데이터 표시 (ID 컬럼 숨김)
        edited_df = st.data_editor(
            df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "선택": st.column_config.CheckboxColumn("선택", default=False),
                "이름": st.column_config.TextColumn("이름", width="medium")
            }
        )
        
        # 선택된 학생들의 상세 정보 표시
        selected_indices = edited_df[edited_df["선택"] == True].index.tolist()
        
        if selected_indices:
            st.markdown("---")
            st.subheader("👤 선택된 학생 상세 정보")
            
            for idx in selected_indices:
                if idx < len(students):
                    student = students[idx]
                    render_student_with_family_detail(student, student_service, guardian_service)
    
    else:
        st.info("등록된 학생이 없습니다.")

def render_student_with_family_detail(student, student_service, guardian_service):
    """학생과 가족 정보를 함께 상세 표시"""
    st.markdown("---")
    st.subheader(f"📄 {student.name} 학생 및 가족 정보")
    
    # 보호자 정보 가져오기
    guardians = guardian_service.get_guardians_by_student(student.id)
    
    # 탭으로 학생 정보와 가족 정보 분리
    tab1, tab2, tab3 = st.tabs(["👤 학생 정보", "👨‍👩‍👧‍👦 가족 정보", "⚙️ 관리"])
    
    with tab1:
        # 학생 기본 정보
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**기본 정보**")
            st.write(f"• 이름: {student.name}")
            st.write(f"• 학원등록번호: {student.academy_id}")
            st.write(f"• 성별: {student.gender.value if student.gender else '미설정'}")
            st.write(f"• 생년월일: {student.birth_date.strftime('%Y-%m-%d') if student.birth_date else '미설정'}")
            st.write(f"• 상태: {student.status.value}")
        
        with col2:
            st.write("**학교 정보**")
            st.write(f"• 학교: {student.school_name or '미설정'}")
            st.write(f"• 학년: {student.grade}학년" if student.grade else "• 학년: 미설정")
            st.write(f"• 반: {student.class_name or '미설정'}")
            st.write(f"• 등록일: {student.enrollment_date.strftime('%Y-%m-%d') if student.enrollment_date else '미설정'}")
        
        # 연락처 정보
        if student.phone or student.email:
            st.write("**연락처 정보**")
            if student.phone:
                st.write(f"• 학생 연락처: {student.phone}")
            if student.email:
                st.write(f"• 학생 이메일: {student.email}")
        
        # 주소 정보
        if student.road_address:
            st.write("**주소 정보**")
            address = f"({student.postal_code}) {student.road_address}"
            if student.detail_address:
                address += f" {student.detail_address}"
            st.write(f"• {address}")
        
        # 특이사항
        if student.notes:
            st.write("**특이사항**")
            st.write(student.notes)
    
    with tab2:
        # 가족 정보 표시
        if guardians:
            st.write("**보호자 정보**")
            
            for guardian in guardians:
                with st.container():
                    role = "👑 주보호자" if guardian.is_primary else "👤 보호자"
                    st.write(f"### {role} - {guardian.name}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"• 관계: {guardian.relationship_type.value}")
                        st.write(f"• 연락처: {guardian.phone}")
                        st.write(f"• 이메일: {guardian.email or '없음'}")
                    
                    with col2:
                        st.write(f"• 직업: {guardian.occupation or '없음'}")
                        st.write(f"• 직장: {guardian.workplace or '없음'}")
                        st.write(f"• 직장전화: {guardian.work_phone or '없음'}")
                    
                    # 주소 정보 (첫 번째 보호자만)
                    if guardian.is_primary and guardian.road_address:
                        st.write("**가족 주소**")
                        address = f"({guardian.postal_code}) {guardian.road_address}"
                        if guardian.detail_address:
                            address += f" {guardian.detail_address}"
                        st.write(f"• {address}")
                    
                    # 응급연락처
                    if guardian.emergency_contact_name:
                        st.write(f"• 응급연락처: {guardian.emergency_contact_name} ({guardian.emergency_contact_relationship}) - {guardian.emergency_contact_phone}")
                    
                    st.markdown("---")
        else:
            st.warning("등록된 보호자 정보가 없습니다.")
        
        # 가족 연락하기 기능
        if guardians:
            render_student_family_contact({
                'student': student,
                'guardians': guardians
            })
    
    with tab3:
        # 관리 기능
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✏️ 수정", key=f"edit_{student.id}"):
                st.session_state.edit_student_id = student.id
                st.rerun()
        
        with col2:
            if st.button("🗑️ 삭제", key=f"delete_{student.id}", type="secondary"):
                if st.confirm("정말 삭제하시겠습니까? 연결된 보호자 정보도 함께 삭제됩니다."):
                    try:
                        student_service.delete_student(student.id)
                        st.success("학생이 삭제되었습니다.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"삭제 실패: {str(e)}")

def render_student_family_contact(student_family_data):
    """학생 가족 연락 기능"""
    st.markdown("---")
    st.subheader("📞 가족 연락하기")
    
    student = student_family_data['student']
    guardians = student_family_data['guardians']
    
    st.write(f"**{student.name} 학생 가족 연락처**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📞 전화번호**")
        for guardian in guardians:
            role = "👑 주보호자" if guardian.is_primary else "👤 보호자"
            st.write(f"• {role} {guardian.name}: {guardian.phone}")
            if guardian.work_phone:
                st.write(f"  - 직장: {guardian.work_phone}")
        
        if student.phone:
            st.write(f"• 👤 학생 {student.name}: {student.phone}")
    
    with col2:
        st.write("**📧 이메일**")
        for guardian in guardians:
            if guardian.email:
                role = "👑 주보호자" if guardian.is_primary else "👤 보호자"
                st.write(f"• {role} {guardian.name}: {guardian.email}")
        
        if student.email:
            st.write(f"• 👤 학생 {student.name}: {student.email}")
    
    # 빠른 연락 버튼
    if guardians:
        st.write("**빠른 연락**")
        primary_guardian = next((g for g in guardians if g.is_primary), guardians[0])
        
        col3, col4 = st.columns(2)
        
        with col3:
            if st.button(f"📞 {primary_guardian.name}에게 전화", key=f"call_{student.id}"):
                st.info(f"전화: {primary_guardian.phone}")
        
        with col4:
            if primary_guardian.email and st.button(f"📧 {primary_guardian.name}에게 이메일", key=f"email_{student.id}"):
                st.info(f"이메일: {primary_guardian.email}")

def render_student_registration(student_service, guardian_service):
    """학생 등록 - 보호자 정보도 함께 입력"""
    st.subheader("➕ 새 학생 등록")
    
    with st.form("student_registration_form"):
        st.write("### 👤 학생 정보")
        
        # 학생 기본 정보
        col1, col2 = st.columns(2)
        
        with col1:
            student_name = st.text_input("학생 이름*", placeholder="학생 이름")
            student_gender = st.selectbox("성별*", [None] + list(Gender), format_func=lambda x: "선택하세요" if x is None else x.value)
            student_birth_date = st.date_input("생년월일")
            student_phone = st.text_input("학생 연락처", placeholder="010-0000-0000")
        
        with col2:
            school_name = st.text_input("학교*", placeholder="학교명")
            grade = st.number_input("학년", min_value=1, max_value=12, value=1)
            class_name = st.text_input("반", placeholder="1반")
            student_email = st.text_input("학생 이메일", placeholder="student@example.com")
        
        # 주소 정보
        st.write("### 🏠 주소 정보")
        col3, col4 = st.columns([1, 3])
        
        with col3:
            postal_code = st.text_input("우편번호")
        
        with col4:
            road_address = st.text_input("주소")
        
        detail_address = st.text_input("상세주소")
        
        # 보호자 정보
        st.write("### 👨‍👩‍👧‍👦 보호자 정보")
        
        # 보호자 1 (주보호자)
        with st.expander("👑 주보호자 정보*", expanded=True):
            col5, col6 = st.columns(2)
            
            with col5:
                guardian1_name = st.text_input("보호자 이름*", key="g1_name", placeholder="보호자 이름")
                guardian1_relationship = st.selectbox("관계*", list(RelationshipType), 
                                                    format_func=lambda x: x.value, key="g1_rel")
                guardian1_phone = st.text_input("연락처*", key="g1_phone", placeholder="010-0000-0000")
                guardian1_email = st.text_input("이메일", key="g1_email", placeholder="guardian@example.com")
            
            with col6:
                guardian1_occupation = st.text_input("직업", key="g1_job", placeholder="직업")
                guardian1_workplace = st.text_input("직장", key="g1_work", placeholder="직장명")
                guardian1_work_phone = st.text_input("직장전화", key="g1_work_phone", placeholder="02-0000-0000")
        
        # 보호자 2 (선택사항)
        add_second_guardian = st.checkbox("👤 추가 보호자 등록")
        
        guardian2_name = guardian2_relationship = guardian2_phone = guardian2_email = None
        guardian2_occupation = guardian2_workplace = guardian2_work_phone = None
        
        if add_second_guardian:
            with st.expander("👤 추가 보호자 정보", expanded=True):
                col7, col8 = st.columns(2)
                
                with col7:
                    guardian2_name = st.text_input("보호자 이름", key="g2_name", placeholder="보호자 이름")
                    guardian2_relationship = st.selectbox("관계", list(RelationshipType), 
                                                        format_func=lambda x: x.value, key="g2_rel")
                    guardian2_phone = st.text_input("연락처", key="g2_phone", placeholder="010-0000-0000")
                    guardian2_email = st.text_input("이메일", key="g2_email", placeholder="guardian@example.com")
                
                with col8:
                    guardian2_occupation = st.text_input("직업", key="g2_job", placeholder="직업")
                    guardian2_workplace = st.text_input("직장", key="g2_work", placeholder="직장명")
                    guardian2_work_phone = st.text_input("직장전화", key="g2_work_phone", placeholder="02-0000-0000")
        
        # 특이사항
        notes = st.text_area("특이사항", placeholder="특이사항이나 참고사항을 입력하세요")
        
        if st.form_submit_button("➕ 학생 등록", type="primary"):
            # 필수 필드 검증
            if not student_name or not school_name or not guardian1_name or not guardian1_phone:
                st.error("학생 이름, 학교, 주보호자 이름, 주보호자 연락처는 필수 입력 항목입니다.")
                return
            
            if student_gender is None:
                st.error("성별을 선택해주세요.")
                return
            
            try:
                # 학생 데이터 생성
                student_data = {
                    'name': student_name,
                    'gender': student_gender,
                    'birth_date': student_birth_date,
                    'school_name': school_name,
                    'grade': grade,
                    'class_name': class_name,
                    'phone': student_phone,
                    'email': student_email,
                    'postal_code': postal_code,
                    'road_address': road_address,
                    'detail_address': detail_address,
                    'status': StudentStatus.ACTIVE,
                    'enrollment_date': date.today(),
                    'notes': notes
                }
                
                # 학생 등록
                student = student_service.create_student(student_data)
                
                # 주보호자 등록
                guardian1_data = {
                    'name': guardian1_name,
                    'relationship_type': guardian1_relationship,
                    'phone': guardian1_phone,
                    'email': guardian1_email,
                    'occupation': guardian1_occupation,
                    'workplace': guardian1_workplace,
                    'work_phone': guardian1_work_phone,
                    'postal_code': postal_code,
                    'road_address': road_address,
                    'detail_address': detail_address,
                    'is_primary': True,
                    'sms_enabled': True,
                    'email_enabled': True,
                    'kakao_enabled': False,
                    'phone_enabled': True
                }
                
                guardian1 = guardian_service.create_guardian(guardian1_data)
                guardian_service.link_guardian_to_student(guardian1.id, student.id)
                
                # 추가 보호자 등록
                if add_second_guardian and guardian2_name and guardian2_phone:
                    guardian2_data = {
                        'name': guardian2_name,
                        'relationship_type': guardian2_relationship,
                        'phone': guardian2_phone,
                        'email': guardian2_email,
                        'occupation': guardian2_occupation,
                        'workplace': guardian2_workplace,
                        'work_phone': guardian2_work_phone,
                        'postal_code': postal_code,
                        'road_address': road_address,
                        'detail_address': detail_address,
                        'is_primary': False,
                        'sms_enabled': True,
                        'email_enabled': True,
                        'kakao_enabled': False,
                        'phone_enabled': True
                    }
                    
                    guardian2 = guardian_service.create_guardian(guardian2_data)
                    guardian_service.link_guardian_to_student(guardian2.id, student.id)
                
                st.success(f"✅ 학생이 등록되었습니다. (학원등록번호: {student.academy_id})")
                st.balloons()  # 축하 애니메이션
                st.info("📋 **등록된 학생을 확인하려면 '학생 목록' 탭을 클릭하세요!**")
                
                # 폼을 초기화하기 위해 페이지 새로고침
                st.rerun()
                
            except Exception as e:
                st.error(f"등록 실패: {str(e)}")
    

def render_excel_management(student_service, guardian_service):
    """엑셀 관리"""
    st.subheader("📤 엑셀 업로드/다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📥 학생 엑셀 업로드**")
        
        # 학생 템플릿 다운로드
        if st.button("📄 학생 업로드 템플릿 다운로드"):
            template_data = {
                '이름': ['김철수', '이영희'],
                '성별': ['남', '여'],
                '생년월일': ['2010-03-15', '2009-08-22'],
                '학교': ['서울초등학교', '강남초등학교'],
                '학년': [6, 6],
                '반': ['1반', '2반'],
                '학생연락처': ['', '010-1234-5678'],
                '학생이메일': ['', 'student@example.com'],
                '우편번호': ['12345', '67890'],
                '주소': ['서울시 강남구 테헤란로', '서울시 서초구 반포로'],
                '상세주소': ['123-45', '678-90'],
                '상태': ['재학', '재학'],
                '특이사항': ['', '']
            }
            
            df_template = pd.DataFrame(template_data)
            
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                df_template.to_excel(tmp_file.name, index=False, engine='openpyxl')
                
                with open(tmp_file.name, 'rb') as f:
                    st.download_button(
                        label="💾 학생 템플릿 다운로드",
                        data=f.read(),
                        file_name="학생_업로드_템플릿.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # 임시 파일 삭제
                os.unlink(tmp_file.name)
        
        # 학생 파일 업로드
        student_uploaded_file = st.file_uploader(
            "학생 엑셀 파일 선택",
            type=['xlsx', 'xls'],
            help="학생 업로드 템플릿 형식에 맞춰 작성해주세요.",
            key="student_upload"
        )
        
        if student_uploaded_file is not None:
            if st.button("📤 학생 업로드 실행"):
                try:
                    # 임시 파일로 저장
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                        tmp_file.write(student_uploaded_file.getvalue())
                        
                        result = student_service.import_students_from_excel(tmp_file.name)
                        
                        st.success(f"✅ 학생 업로드 완료: {result['success_count']}명 성공")
                        st.info("📋 업로드된 학생을 확인하려면 '학생 목록' 탭을 클릭하세요.")
                        
                        if result['error_count'] > 0:
                            st.warning(f"⚠️ 오류: {result['error_count']}건")
                            with st.expander("오류 상세"):
                                for error in result['errors']:
                                    st.write(f"• {error}")
                        
                        # 임시 파일 삭제
                        os.unlink(tmp_file.name)
                        
                except Exception as e:
                    st.error(f"학생 업로드 실패: {str(e)}")
    
    with col2:
        st.write("**📥 보호자 엑셀 업로드**")
        
        # 보호자 템플릿 다운로드
        if st.button("📄 보호자 업로드 템플릿 다운로드"):
            template_data = {
                '이름': ['김아버지', '이어머니'],
                '관계': ['아버지', '어머니'],
                '연락처': ['010-1234-5678', '010-9876-5432'],
                '이메일': ['father@example.com', 'mother@example.com'],
                '직업': ['회사원', '주부'],
                '직장': ['○○회사', ''],
                '직장전화': ['02-1234-5678', ''],
                '우편번호': ['12345', '67890'],
                '주소': ['서울시 강남구 테헤란로', '서울시 서초구 반포로'],
                '상세주소': ['123번지', '456호'],
                '주보호자': ['Y', 'N']
            }
            
            df_template = pd.DataFrame(template_data)
            
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                df_template.to_excel(tmp_file.name, index=False, engine='openpyxl')
                
                with open(tmp_file.name, 'rb') as f:
                    st.download_button(
                        label="💾 보호자 템플릿 다운로드",
                        data=f.read(),
                        file_name="보호자_업로드_템플릿.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # 임시 파일 삭제
                os.unlink(tmp_file.name)
        
        # 보호자 파일 업로드
        guardian_uploaded_file = st.file_uploader(
            "보호자 엑셀 파일 선택",
            type=['xlsx', 'xls'],
            help="보호자 업로드 템플릿 형식에 맞춰 작성해주세요.",
            key="guardian_upload"
        )
        
        if guardian_uploaded_file is not None:
            if st.button("📤 보호자 업로드 실행"):
                try:
                    # 임시 파일로 저장
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                        tmp_file.write(guardian_uploaded_file.getvalue())
                        
                        result = guardian_service.import_guardians_from_excel(tmp_file.name)
                        
                        st.success(f"✅ 보호자 업로드 완료: {result['success_count']}명 성공")
                        st.info("📋 업로드된 보호자를 확인하려면 '학생 목록' 탭을 클릭하세요.")
                        
                        if result['error_count'] > 0:
                            st.warning(f"⚠️ 오류: {result['error_count']}건")
                            with st.expander("오류 상세"):
                                for error in result['errors']:
                                    st.write(f"• {error}")
                        
                        # 임시 파일 삭제
                        os.unlink(tmp_file.name)
                        
                except Exception as e:
                    st.error(f"보호자 업로드 실패: {str(e)}")

def render_student_statistics(student_service, guardian_service):
    """학생 통계"""
    st.subheader("📊 학생 통계")
    
    try:
        # 기본 통계
        students = student_service.get_all_students()
        guardians = guardian_service.get_all_guardians()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 학생 수", f"{len(students)}명")
        
        with col2:
            active_students = len([s for s in students if s.status == StudentStatus.ACTIVE])
            st.metric("재학생", f"{active_students}명")
        
        with col3:
            st.metric("총 보호자 수", f"{len(guardians)}명")
        
        with col4:
            if students:
                avg_guardians = len(guardians) / len(students)
                st.metric("학생당 평균 보호자", f"{avg_guardians:.1f}명")
        
        # 성별 분포
        if students:
            st.write("### 성별 분포")
            gender_count = {}
            for student in students:
                if student.gender:
                    gender_name = "남학생" if student.gender == Gender.MALE else "여학생"
                    gender_count[gender_name] = gender_count.get(gender_name, 0) + 1
            
            if gender_count and len(gender_count) > 0:
                gender_df = pd.DataFrame(list(gender_count.items()), columns=['성별', '인원'])
                # 데이터 유효성 확인
                if not gender_df.empty and gender_df['인원'].sum() > 0:
                    st.bar_chart(gender_df.set_index('성별'))
                else:
                    st.info("성별 데이터가 충분하지 않습니다.")
            else:
                st.info("성별 분포 데이터가 없습니다.")
        
        # 학년별 분포
        if students:
            st.write("### 학년별 분포")
            grade_count = {}
            for student in students:
                if student.grade:
                    grade_name = f"{student.grade}학년"
                    grade_count[grade_name] = grade_count.get(grade_name, 0) + 1
            
            if grade_count and len(grade_count) > 0:
                grade_df = pd.DataFrame(list(grade_count.items()), columns=['학년', '인원'])
                # 데이터 유효성 확인
                if not grade_df.empty and grade_df['인원'].sum() > 0:
                    st.bar_chart(grade_df.set_index('학년'))
                else:
                    st.info("학년 데이터가 충분하지 않습니다.")
            else:
                st.info("학년 분포 데이터가 없습니다.")
        
        # 최근 등록 현황
        st.write("### 최근 등록 현황 (30일)")
        recent_students = [s for s in students if s.enrollment_date and (date.today() - s.enrollment_date).days <= 30]
        
        if recent_students:
            st.success(f"✅ 최근 30일간 {len(recent_students)}명의 학생이 등록되었습니다.")
        else:
            st.info("최근 30일간 등록된 학생이 없습니다.")
        
    except Exception as e:
        st.error(f"통계 로딩 실패: {str(e)}")