"""요금표 — 홈과 FAQ의 [요금표 보기]가 모두 이 화면으로 연결된다.

표시 데이터: MySQL fare_rules (services/fare_rules_db.py). 임의 요금을 만들지 않는다.
"""

import streamlit as st

from services.db import DBConnectionError
from services.fare_rules_db import load_fare_rules

st.title("요금표")
st.caption("다마스 · 라보 · 1톤 차량별 운임 기준")

with st.container(border=True):
    try:
        table = load_fare_rules()
        if table.empty:
            st.info("요금표가 아직 확정되지 않았습니다. 운임 기준(fare_rules)이 등록되면 이곳에 표시됩니다.")
        else:
            st.warning("확정 전 운임 기준으로 참고용입니다. 실제 운임은 거리·물품·옵션에 따라 달라질 수 있습니다.")
            st.dataframe(table, hide_index=True)
    except DBConnectionError as e:
        st.error(str(e))

c1, c2, c3 = st.columns(3)
if c1.button("운송 신청하기", type="primary"):
    st.switch_page("pages/1_Delivery_Request.py")
if c2.button("홈으로"):
    st.switch_page("pages/0_Home.py")
if c3.button("FAQ로 이동"):
    st.switch_page("pages/5_FAQ.py")
