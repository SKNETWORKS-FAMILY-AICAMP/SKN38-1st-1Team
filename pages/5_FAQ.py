"""FAQ — 기본 화면만 구현 (FAQ 데이터 로딩·검색·답변 표시는 FAQ 담당: 흥기님)

연결 위치: 아래 '질문·답변 표시 영역'에서 category, keyword 값을 받아 FAQ 목록을 조회·표시하면 된다.
기존 FAQ 데이터 파일(sendy_FAQ)은 이 화면에서 읽거나 수정하지 않는다.
화면 배치는 디자인 시안(검색 → 운임 요금표 → 자주 묻는 질문 카테고리)을 따른다.
"""

import streamlit as st

from services.db import DBConnectionError
from services.fare_rules_db import load_fare_rules

CATEGORIES = ["전체", "예약·취소", "파손·분실", "기사·안전"]

st.title("FAQ")
keyword = st.text_input("키워드 검색", placeholder="궁금한 내용을 검색하세요.")

# ── 운임 요금표 (요금 카테고리는 맨 위 요금표로 안내) ────────────────────
with st.container(border=True):
    head, link = st.columns([3, 1], vertical_alignment="center")
    head.subheader("운임 요금표")
    if link.button("요금표 보기", width="stretch"):
        st.switch_page("pages/7_Fare_Table.py")
    try:
        fares = load_fare_rules()
        if fares.empty:
            st.caption("요금표가 아직 확정되지 않았습니다. 운임 기준이 등록되면 이곳에 표시됩니다.")
        else:
            st.dataframe(fares[["차종", "기본요금(원)", "km당 요금(원)"]], hide_index=True)
            st.caption("확정 전 운임 기준으로 참고용입니다.")
    except DBConnectionError as e:
        st.caption(str(e))

# ── 자주 묻는 질문 ────────────────────────────────────────────────────
st.subheader("자주 묻는 질문")
category = st.segmented_control("카테고리", CATEGORIES, default="전체", label_visibility="collapsed") or "전체"

# TODO(FAQ 담당): category, keyword로 FAQ를 조회해 질문·답변·원문 링크를 st.expander 등으로 표시
st.info("FAQ 데이터 연결 준비 중입니다.")
