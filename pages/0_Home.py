"""홈 · 요청하기 — 서비스 소개, [운송 신청하기]·[요금표 보기], 시도별 화물차 현황 미리보기

운송 신청 폼은 pages/1_Delivery_Request.py, 지도 상세는 pages/4_Truck_Map.py (별도 페이지)
"""

import streamlit as st

from services.db import DBConnectionError
from services.truck_map import build_deck, is_consistent, load_points, match_points, picked_sido
from services.truck_stats import DATA_NOTE, format_month, load_truck_stats
from services.ui import REQUEST_STEPS, asset

with st.container(key="hero_home"):
    text, image = st.columns([3, 2], vertical_alignment="center")
    with text:
        st.title("짐 옮길 땐, 짐니.")
        st.write("출발지·도착지와 짐 크기만 입력하면  \n내 짐에 맞는 차량과 기사님을 찾아드려요.")
        b1, b2 = st.columns(2)
        if b1.button("운송 신청하기", type="primary", width="stretch"):
            st.switch_page("pages/1_Delivery_Request.py")
        if b2.button("요금표 보기", width="stretch"):
            st.switch_page("pages/7_Fare_Table.py")
    with image:
        st.image(asset("sub.png"), width="stretch")

st.write("")
st.subheader("이용 방법")
icons = ["jimni2.png", "jimni6.png", "jimni3.png", "jimni4.png", "jimni5.png"]
with st.container(key="steps_home"):
    for col, (i, label), icon in zip(st.columns(len(REQUEST_STEPS)), enumerate(REQUEST_STEPS, start=1), icons):
        with col.container(border=True):
            st.image(asset(icon))
            st.markdown(f"**{i}. {label}**")

st.write("")
st.subheader("시도별 영업용 화물차 등록 현황")
with st.container(key="soft_home_map"):
    try:
        stats = load_truck_stats()
        sido = stats["sido"]
        month = format_month(stats["base_month"])
        st.caption(f"{month} 기준 · 국토교통부")
        points = load_points()
        if points is not None and is_consistent(match_points(points, sido)):
            event = st.pydeck_chart(build_deck(points, sido, month, zoom=5.6), on_select="rerun",
                                    selection_mode="single-object", key="home_sido_map", height=460)
            pick = picked_sido(event)
            if pick:
                count = int(sido.loc[sido["sido_name"] == pick, "truck_count"].iloc[0])
                st.metric(f"{pick} 영업용 화물차 등록대수", f"{count:,}대")
            st.caption("버블이 클수록 등록대수가 많습니다. 버블에 마우스를 올리거나 클릭하면 수치가 보입니다. "
                       "버블은 시도 대표 위치이며 차량 위치가 아닙니다.")
        else:
            st.bar_chart(sido.set_index("sido_name")["truck_count"], horizontal=True,
                         x_label="등록대수(대)", y_label="")
        st.caption(DATA_NOTE)
    except DBConnectionError as e:
        st.error(str(e))
    if st.button("지역별 화물차 현황 자세히 보기"):
        st.switch_page("pages/4_Truck_Map.py")
