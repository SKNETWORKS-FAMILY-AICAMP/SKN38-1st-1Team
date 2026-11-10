"""파트너센터 (기사님 로그인 화면)

- 화면 구성만 구현: 실제 인증·회원 저장은 하지 않는다 (비밀번호를 저장하거나 비교하지 않음)
"""

import re

import streamlit as st

st.title("파트너센터")
st.caption("짐니 기사님 전용 공간이에요. 가까운 운송 요청 확인, 일정 관리, 정산 내역을 한곳에서 볼 수 있어요.")

_, center, _ = st.columns([1, 2, 1])                         # 가운데 좁은 칸에 로그인 상자

with center:
    with st.container(border=True):
        with st.form("driver_login_form", border=False):
            phone = st.text_input("휴대폰 번호", max_chars=13, placeholder="010-1234-5678")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            keep = st.checkbox("로그인 상태 유지")
            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

        if submitted:
            if not re.fullmatch(r"01\d{8,9}", re.sub(r"\D", "", phone)):
                st.error("휴대폰 번호를 정확히 입력해 주세요.")
            elif not password:
                st.error("비밀번호를 입력해 주세요.")
            else:
                st.info("기사님 로그인 기능은 준비 중입니다. 정식 오픈 후 이용할 수 있어요.")

        c1, c2 = st.columns(2)
        c1.button("아이디 · 비밀번호 찾기", use_container_width=True, disabled=True)
        c2.button("기사님 회원가입", use_container_width=True, disabled=True)
        st.caption("회원가입 시 사업자등록번호와 차종(다마스 · 라보 · 1톤)을 등록하고, 확인이 끝나면 배차를 받을 수 있어요.")