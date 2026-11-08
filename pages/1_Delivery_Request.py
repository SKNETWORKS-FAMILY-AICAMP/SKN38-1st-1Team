"""홈 · 요청하기 — 운송 요청 입력 폼 + 시도별 영업용 화물차 등록 현황 요약

- 입력값은 services.transport_request.REQUEST_KEY로 session_state에 저장 → 매칭 결과 화면에서 사용
- 주소 검색(카카오맵)·거리·운임·차량 추천·기사 매칭은 각 담당 기능에서 연결 (이 화면에서 계산하지 않음)
"""

from datetime import date, datetime, time, timedelta

import streamlit as st

from services.db import DBConnectionError
from services.transport_request import (
    FLOOR_MAX,
    FLOOR_MIN,
    HELPER_OPTIONS,
    ITEM_MAX,
    ITEM_SIZES,
    REQUEST_KEY,
    SELECTED_DRIVER_KEY,
    VEHICLE_TYPES,
    validate_request,
)
from services.truck_map import build_deck, is_consistent, load_points, match_points, picked_sido
from services.truck_stats import DATA_NOTE, format_month, load_truck_stats

st.title("홈 · 요청하기")

saved = st.session_state.get(REQUEST_KEY, {})
default_dt = saved.get("scheduled_at") or datetime.combine(date.today() + timedelta(days=1), time(9, 0))

left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("운송 요청")
    st.caption(f"운송 차량: {' · '.join(VEHICLE_TYPES)} (입력한 짐에 맞춰 추천 예정)")
    with st.form("transport_request_form"):
        st.markdown("**출발지 · 도착지**")
        origin = st.text_input("출발지 주소", value=saved.get("origin_address", ""), placeholder="예: 서울특별시 ○○구 ○○로 00")
        dest = st.text_input("도착지 주소", value=saved.get("dest_address", ""), placeholder="예: 경기도 ○○시 ○○로 00")
        st.caption("주소 검색(카카오맵)은 연결 예정입니다. 지금은 주소를 직접 입력해 주세요.")

        c1, c2 = st.columns(2)
        with c1:
            origin_floor = st.number_input("출발지 층수", min_value=FLOOR_MIN, max_value=FLOOR_MAX, step=1,
                                           value=saved.get("origin_floor", 1))
            origin_elev = st.radio("출발지 엘리베이터", ["있음", "없음"], horizontal=True,
                                   index=0 if saved.get("origin_has_elevator", True) else 1)
        with c2:
            dest_floor = st.number_input("도착지 층수", min_value=FLOOR_MIN, max_value=FLOOR_MAX, step=1,
                                         value=saved.get("dest_floor", 1))
            dest_elev = st.radio("도착지 엘리베이터", ["있음", "없음"], horizontal=True,
                                 index=0 if saved.get("dest_has_elevator", True) else 1)

        st.markdown("**물품 크기별 개수**")
        item_cols = st.columns(len(ITEM_SIZES))
        counts = {}
        for col, size in zip(item_cols, ITEM_SIZES):
            key = f"item_{size.lower()}_count"
            counts[key] = col.number_input(size, min_value=0, max_value=ITEM_MAX, step=1, value=saved.get(key, 0))

        st.markdown("**희망 운송 일시 · 추가 인력**")
        c3, c4 = st.columns(2)
        sched_date = c3.date_input("날짜", value=default_dt.date(), min_value=date.today())
        sched_time = c4.time_input("시간", value=default_dt.time(), step=timedelta(minutes=30))
        helper_keys = list(HELPER_OPTIONS)
        helper = st.radio("추가 인력", helper_keys, format_func=HELPER_OPTIONS.get, horizontal=True,
                          index=helper_keys.index(saved.get("helper_option", "NONE")))

        submitted = st.form_submit_button("매칭 시작", type="primary")

    if submitted:
        request = {
            "origin_address": origin.strip(),
            "dest_address": dest.strip(),
            "origin_floor": int(origin_floor),
            "origin_has_elevator": origin_elev == "있음",
            "dest_floor": int(dest_floor),
            "dest_has_elevator": dest_elev == "있음",
            **{k: int(v) for k, v in counts.items()},
            "scheduled_at": datetime.combine(sched_date, sched_time),
            "helper_option": helper,
        }
        errors = validate_request(request)
        if errors:
            for msg in errors:
                st.error(msg)
        else:
            st.session_state[REQUEST_KEY] = request
            st.session_state.pop(SELECTED_DRIVER_KEY, None)  # 조건이 바뀌면 이전 기사 선택 초기화
            st.switch_page("pages/2_Driver_Matching.py")

with right:
    st.subheader("시도별 영업용 화물차 등록 현황")
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
    if st.button("요금표 보기"):
        st.switch_page("pages/7_Fare_Table.py")
