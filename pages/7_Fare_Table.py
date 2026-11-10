"""요금표 — 홈과 FAQ의 [요금표 보기]가 모두 이 화면으로 연결된다.
표시 데이터: services/fare_view.render_fare_tables (FAQ·운송 신청의 [요금표 보기] 창과 같은 표). 임의 요금을 만들지 않는다.
"""

import streamlit as st

from services.fare_view import render_fare_tables

st.title("요금표")
st.caption("다마스 · 라보 · 1톤 차량별 운임 기준")

with st.container(border=True):
    render_fare_tables()

c1, c2, c3 = st.columns(3)
if c1.button("운송 신청하기", type="primary"):
    st.switch_page("pages/1_Delivery_Request.py")
if c2.button("홈으로"):
    st.switch_page("pages/0_Home.py")
if c3.button("FAQ로 이동"):
    st.switch_page("pages/5_FAQ.py")