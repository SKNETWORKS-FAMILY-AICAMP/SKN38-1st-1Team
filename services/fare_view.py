"""요금표 화면 조각 — 요금표 페이지 · FAQ · 운송 신청이 같은 표를 보여주도록 한곳에 모음

표시 데이터: services/fare_table.py 운임 기준표 + services/settlement.py 수수료 기준 (임의 요금을 만들지 않음)
- render_fare_tables(): ①~⑤ 요금표
- title_with_fare_button(title): 페이지 제목 바로 옆에 작은 [요금표 보기] 버튼 → 누르면 요금표 창(st.dialog)
"""

from __future__ import annotations

import streamlit as st

from services.db import DBConnectionError
from services.fare_rules_db import extra_fee_table, fare_band_table, item_size_table, stair_fee_table
from services.settlement import fee_policy_table


def render_fare_tables() -> None:
    """① 거리별 기본 운임 ~ ⑤ 서비스 이용료·기사 수수료."""
    try:
        st.markdown("**① 거리별 기본 운임**")
        st.dataframe(fare_band_table(), hide_index=True)
        st.caption("최대 100km까지 운송합니다.")

        st.markdown("**② 계단 작업 요금 (엘리베이터 없을 때)**")
        st.dataframe(stair_fee_table(), hide_index=True)
        st.caption("출발지와 도착지에서 각각 따로 계산해요.")

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


@st.dialog("요금표", width="large")
def fare_dialog() -> None:
    """지금 화면(입력 중인 내용)을 떠나지 않고 요금표를 확인하는 창."""
    st.caption("다마스 · 라보 · 1톤 차량별 운임 기준")
    render_fare_tables()


def title_with_fare_button(title: str, key: str) -> None:
    """페이지 제목 + 바로 옆 작은 [요금표 보기] 버튼."""
    with st.container(horizontal=True, vertical_alignment="center", gap="small", key=f"jm_title_{key}"):
        st.title(title, width="content")                      # 제목 폭만큼만 → 버튼이 바로 옆에 붙음
        if st.button("요금표 보기", icon=":material/receipt_long:", key=f"fare_btn_{key}", width="content"):
            fare_dialog()
