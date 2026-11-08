"""운송 신청 (요청 1단계: 정보 입력) — 홈의 [운송 신청하기]로 진입

- 입력값은 services.transport_request.REQUEST_KEY로 session_state에 저장 → 매칭 결과 화면에서 사용
- 주소 검색(카카오맵)·거리·운임·차량 추천·기사 매칭은 각 담당 기능에서 연결 (이 화면에서 계산하지 않음)
"""

from datetime import date, datetime, time, timedelta

import streamlit as st

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
from services.ui import step_header

step_header(1)
st.title("운송 정보 입력")

saved = st.session_state.get(REQUEST_KEY, {})
default_dt = saved.get("scheduled_at") or datetime.combine(date.today() + timedelta(days=1), time(9, 0))

left, _ = st.columns([3, 1])

with left:
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

        submitted = st.form_submit_button("매칭 시작하기", type="primary")

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

if st.button("홈으로"):
    st.switch_page("pages/0_Home.py")
