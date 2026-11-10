"""요금표 — 홈과 FAQ의 [요금표 보기]가 모두 이 화면으로 연결된다.
표시 데이터: services/fare_table.py 운임 기준표 + services/settlement.py 수수료 기준. 임의 요금을 만들지 않는다.
"""

import streamlit as st
from services.db import DBConnectionError
from services.fare_rules_db import fare_band_table, extra_fee_table, item_size_table, stair_fee_table
from services.settlement import fee_policy_table

st.title("요금표")
st.caption("다마스 · 라보 · 1톤 차량별 운임 기준")

with st.container(border=True):
    try:
        st.markdown("**① 거리별 기본 운임**")
        st.dataframe(fare_band_table(), hide_index=True)
        st.caption("최대 100km까지 운송합니다.")

        st.markdown("**② 계단 작업 요금 (엘리베이터 없을 때)**")
        st.dataframe(stair_fee_table(), hide_index=True)

        st.markdown("**③ 짐 크기별 차량 기준**")
        st.dataframe(item_size_table(), hide_index=True)
        st.caption("짐 크기와 수량에 맞는 가장 작은 차량이 정해지고, 그 차량의 ① 거리별 운임이 적용됩니다.")

        st.markdown("**④ 인력 추가 요금**")
        st.dataframe(extra_fee_table(), hide_index=True)

        st.markdown("**⑤ 서비스 이용료 · 기사 수수료**")
        fee_rows = [{k: v for k, v in row.items() if not k.startswith("예시")} for row in fee_policy_table()]
        st.dataframe(fee_rows, hide_index=True)
        st.caption("결제 예상 금액 = 기본 운임 + 추가 요금 + 서비스 이용료(5%)")
    except DBConnectionError as e:
        st.error(str(e))

c1, c2, c3 = st.columns(3)
if c1.button("운송 신청하기", type="primary"):
    st.switch_page("pages/1_Delivery_Request.py")
if c2.button("홈으로"):
    st.switch_page("pages/0_Home.py")
if c3.button("FAQ로 이동"):
    st.switch_page("pages/5_FAQ.py")