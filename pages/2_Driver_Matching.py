"""매칭 결과 — 화면 구조와 이동만 구현 (추천 계산·기사 데이터는 매칭/운임 담당: 예준님)

연결 위치 (담당자가 아래 함수를 만들면 이 화면에 자동으로 표시됨)
    services/fare.py      estimate(request: dict) -> dict
        예: {"vehicle_type": "라보", "distance_km": 12.3, "estimated_minutes": 35, "estimated_fare": 65000}
    services/matching.py  recommend_drivers(request: dict) -> list[dict]
        예: [{"driver_id": 1, "nickname": ..., "vehicle_type": ..., "rating": ..., "distance_km": ...}, ...]
선택한 기사는 st.session_state[SELECTED_DRIVER_KEY]에 저장되어 예약하기 화면으로 전달된다.
"""

import streamlit as st

from services import fare, matching
from services.transport_request import HELPER_OPTIONS, ITEM_SIZES, REQUEST_KEY, SELECTED_DRIVER_KEY
from services.ui import step_header

step_header(3 if SELECTED_DRIVER_KEY in st.session_state else 2)
st.title("매칭 결과")

request = st.session_state.get(REQUEST_KEY)
if not request:
    st.warning("운송 요청 정보가 없습니다. 홈에서 운송 조건을 먼저 입력해 주세요.")
    if st.button("운송 신청하러 가기"):
        st.switch_page("pages/1_Delivery_Request.py")
    st.stop()

with st.expander("입력한 운송 조건", expanded=True):
    st.write(f"**출발지** {request['origin_address']} ({request['origin_floor']}층, "
             f"엘리베이터 {'있음' if request['origin_has_elevator'] else '없음'})")
    st.write(f"**도착지** {request['dest_address']} ({request['dest_floor']}층, "
             f"엘리베이터 {'있음' if request['dest_has_elevator'] else '없음'})")
    st.write("**물품** " + " · ".join(f"{s} {request[f'item_{s.lower()}_count']}개" for s in ITEM_SIZES))
    st.write(f"**희망 일시** {request['scheduled_at']:%Y-%m-%d %H:%M} · **추가 인력** {HELPER_OPTIONS[request['helper_option']]}")

estimate_fn = getattr(fare, "estimate", None)
recommend_fn = getattr(matching, "recommend_drivers", None)
PENDING = "기사 매칭 기능 준비 중"

with st.container(border=True):
    st.subheader("추천 차량 · 예상 거리 · 예상 운임")
    if estimate_fn is None:
        st.info(PENDING)
    else:
        est = estimate_fn(request)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("추천 차량", est.get("vehicle_type", "-"))
        c2.metric("예상 거리", f"{est['distance_km']} km" if est.get("distance_km") is not None else "-")
        c3.metric("예상 소요시간", f"{est['estimated_minutes']}분" if est.get("estimated_minutes") is not None else "-")
        c4.metric("예상 운임", f"{est['estimated_fare']:,}원" if est.get("estimated_fare") is not None else "-")

with st.container(border=True):
    st.subheader("추천 기사")
    drivers = recommend_fn(request) if recommend_fn else []
    if recommend_fn is None:
        st.info(PENDING)
    elif not drivers:
        st.info("조건에 맞는 기사가 없습니다.")
    else:
        for d in drivers:
            cols = st.columns([4, 1])
            cols[0].write(" · ".join(str(v) for k, v in d.items() if k != "driver_id"))
            if cols[1].button("기사 선택", key=f"pick_{d['driver_id']}"):
                st.session_state[SELECTED_DRIVER_KEY] = d
        if SELECTED_DRIVER_KEY in st.session_state:
            st.success(f"선택한 기사: {st.session_state[SELECTED_DRIVER_KEY].get('nickname', '')}")

c1, c2 = st.columns(2)
if c1.button("운송 조건 수정"):
    st.switch_page("pages/1_Delivery_Request.py")
if c2.button("다음 단계 · 예약하기", type="primary", disabled=SELECTED_DRIVER_KEY not in st.session_state):
    st.switch_page("pages/6_Booking.py")
