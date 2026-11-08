"""FAQ — 기본 화면만 구현 (FAQ 데이터 로딩·검색·답변 표시는 FAQ 담당: 흥기님)

연결 위치: 아래 '질문·답변 표시 영역'에서 category, keyword 값을 받아 FAQ 목록을 조회·표시하면 된다.
기존 FAQ 데이터 파일(sendy_FAQ)은 이 화면에서 읽거나 수정하지 않는다.
"""

import streamlit as st

CATEGORIES = ["전체", "요금", "예약·취소", "파손·분실", "기사·안전"]

st.title("FAQ")

if st.button("요금표 보기"):
    st.switch_page("pages/7_Fare_Table.py")

category = st.radio("카테고리", CATEGORIES, horizontal=True)
keyword = st.text_input("키워드 검색", placeholder="궁금한 내용을 입력하세요")

st.subheader("질문 · 답변")
# TODO(FAQ 담당): category, keyword로 FAQ를 조회해 질문·답변·원문 링크를 표시
st.info("FAQ 데이터 연결 준비 중입니다.")
