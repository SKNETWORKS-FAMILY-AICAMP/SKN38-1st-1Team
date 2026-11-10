"""매칭 결과 — 화면 구조와 이동만 구현 (추천 계산·기사 데이터는 매칭/운임 담당: 예준님)

연결 위치 (담당자가 아래 함수를 만들면 이 화면에 자동으로 표시됨)
    services/fare.py      estimate(request: dict) -> dict
        예: {"vehicle_type": "라보", "distance_km": 12.3, "estimated_minutes": 35, "estimated_fare": 65000}
    services/matching.py  recommend_drivers(request: dict) -> list[dict]
        예: [{"driver_id": 1, "nickname": ..., "vehicle_type": ..., "rating": ..., "distance_km": ...}, ...]
선택한 기사는 st.session_state[SELECTED_DRIVER_KEY]에 저장되어 예약하기 화면으로 전달된다.
"""

"""매칭 결과 — 운임 계산 및 기사 매칭 연결"""

import streamlit as st

from services import agreement, fare, matching, settlement

from services.transport_request import (
    HELPER_OPTIONS,
    ITEM_SIZES,
    REQUEST_KEY,
    SELECTED_DRIVER_KEY,
)
from services.ui import step_header


# ============================================================
# 1. 화면 기본 설정
# ============================================================

step_header(3 if SELECTED_DRIVER_KEY in st.session_state else 2)
st.title("매칭 결과")


# ============================================================
# 2. 운송 신청 데이터 가져오기
# ============================================================

request = st.session_state.get(REQUEST_KEY)

if not request:
    st.warning("운송 요청 정보가 없습니다. 홈에서 운송 조건을 먼저 입력해 주세요.")

    if st.button("운송 신청하러 가기"):
        st.switch_page("pages/1_Delivery_Request.py")

    st.stop()


# ============================================================
# 3. 입력한 운송 조건 표시
# ============================================================

with st.expander("입력한 운송 조건", expanded=True):

    st.write(
        f"**출발지** {request['origin_address']} "
        f"({request['origin_floor']}층, "
        f"엘리베이터 {'있음' if request['origin_has_elevator'] else '없음'})"
    )

    st.write(
        f"**도착지** {request['dest_address']} "
        f"({request['dest_floor']}층, "
        f"엘리베이터 {'있음' if request['dest_has_elevator'] else '없음'})"
    )

    st.write(
        "**물품** "
        + " · ".join(
            f"{size} {request.get(f'item_{size.lower()}_count', 0)}개"
            for size in ITEM_SIZES
        )
    )

    st.write(
        f"**희망 일시** {request['scheduled_at']:%Y-%m-%d %H:%M} "
        f"· **추가 인력** "
        f"{HELPER_OPTIONS.get(request['helper_option'], request['helper_option'])}"
    )



# ============================================================
# 4. 운임 및 차량 추천 계산
# ============================================================

st.subheader("추천 차량 · 예상 거리 · 예상 운임")

estimate_result = None

try:
    # 1. 물품 수량 변환
    # fare.py는 XXL 등급도 지원하므로 기본값 0으로 전달
    item_counts = {
        "S": request.get("item_s_count", 0),
        "M": request.get("item_m_count", 0),
        "L": request.get("item_l_count", 0),
        "XL": request.get("item_xl_count", 0),
        "XXL": 0
    }

    # 2. 추가 인력 옵션 변환
    service_type_map = {
        "NONE": "VEHICLE_ONLY",
        "DRIVER_HELP": "DRIVER_HELP",
        "EXTRA_WORKER": "WORKER_1"
    }

    helper_option = request.get("helper_option", "NONE")
    service_type = service_type_map.get(helper_option)

    if service_type is None:
        raise ValueError(
            f"지원하지 않는 추가 인력 옵션: {helper_option}"
        )

    # 3. 운임 계산 실행
    estimate_result = fare.estimate(
        origin_address=request["origin_address"],
        destination_address=request["dest_address"],
        item_counts=item_counts,
        service_type=service_type,

        # 출발지 조건
        origin_floor=request.get("origin_floor", 1),
        origin_elevator=request.get(
            "origin_has_elevator", True
        ),

        # 도착지 조건
        destination_floor=request.get("dest_floor", 1),
        destination_elevator=request.get(
            "dest_has_elevator", True
        )
    )

except Exception as error:
    st.error(f"운임 계산 중 오류가 발생했습니다: {error}")

# ============================================================
# 5. 계산 결과 화면 출력
# ============================================================

if estimate_result:
    
    vehicle_result = estimate_result.get("vehicle", {})
    distance_result = estimate_result.get("distance", {})
    fare_result = estimate_result.get("fare", {})

    vehicle_type = vehicle_result.get("vehicle_type", "-")
    distance_km = distance_result.get("distance_km")
    estimated_minutes = distance_result.get("duration_minutes")
    estimated_fare = estimate_result.get("total_fare")

    with st.container(border=True):

        money = settlement.calc_settlement(estimated_fare) if estimated_fare is not None else None  # 수수료 계산

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "추천 차량",
            vehicle_type or "-"
        )

        c2.metric(
            "예상 거리",
            f"{distance_km} km" if distance_km is not None else "-"
        )

        c3.metric(
            "예상 소요시간",
            f"{estimated_minutes}분"
            if estimated_minutes is not None else "-"
        )

        c4.metric(
            "예상 운임",
            f"{money['customer_total']:,}원"                     # 서비스 이용료 포함
            if money else "-"
        )

        if money:
            st.caption(
                f"운임 {money['fare']:,}원 + 서비스 이용료 {money['service_fee']:,}원"
                f" ({settlement.SERVICE_FEE_PCT}%) 포함"
            )
            
        # 운임 세부 내역
        if fare_result.get("fare_breakdown"):
            with st.expander("운임 상세 내역 확인"):

                breakdown = fare_result["fare_breakdown"]

                st.write(
                    f"기본 운임: {breakdown['base_fare']:,}원"
                )

                st.write(
                    f"추가 인력 비용: {breakdown['service_fee']:,}원"
                )

                origin_fee = breakdown["origin_stair_fee"]
                destination_fee = breakdown["destination_stair_fee"]

                st.write(
                    f"출발지 계단 작업: "
                    f"{origin_fee:,}원"
                    if origin_fee is not None else "출발지 계단 작업: 별도 협의"
                )

                st.write(
                    f"도착지 계단 작업: "
                    f"{destination_fee:,}원"
                    if destination_fee is not None else "도착지 계단 작업: 별도 협의"
                )

                if money:
                    st.write(
                        f"서비스 이용료 ({settlement.SERVICE_FEE_PCT}%): {money['service_fee']:,}원"
                    )

                    st.write(
                        f"**결제 예상 금액: {money['customer_total']:,}원**"
                    )



# ============================================================
# 6. 추천 기사님 (1명 카드 → 예약하기, 실제 배정은 예약 확정 시 services/assignment.py)
# ============================================================

st.subheader("추천 기사님")

recommend_fn = getattr(matching, "recommend_drivers", None)
drivers = []

if recommend_fn is None:
    st.info("기사 매칭 기능을 준비 중입니다.")
else:
    try:
        drivers = recommend_fn(request, estimate_result)   # 운임 계산과 같은 추천 차량 기준으로 매칭
    except Exception as error:
        st.error(f"기사 매칭 중 오류가 발생했습니다: {error}")

if recommend_fn is not None and not drivers:
    st.info("조건에 맞는 기사님이 없습니다. 날짜나 출발지를 바꿔 다시 시도해 주세요.")

if drivers:
    # 같은 요청 안에서 "다른 기사님 보기"를 누를 때마다 다음 순위 기사로 넘어감
    idx_key = f"driver_idx_{request['origin_address']}_{request['scheduled_at']}"
    idx = st.session_state.get(idx_key, 0) % len(drivers)
    d = drivers[idx]

    with st.container(border=True):
        c1, c2 = st.columns([1, 4], vertical_alignment="center")
        c1.markdown(matching.avatar_html(d), unsafe_allow_html=True)       # 프로필 일러스트
        c2.markdown(f"#### {d['nickname'].replace('*', chr(92) + '*')} 기사님")   # 마스킹 별표 그대로 표시
        rating = f"★ {d['rating']:.1f}" if d["rating"] is not None else "신규 기사님"
        c2.write(f"🚚 {d['vehicle_type']}  ·  📍 출발지에서 {d['distance_km']}km  ·  {rating}")
        c2.caption(f"추천 {idx + 1} / {len(drivers)}")

    b1, b2 = st.columns(2)
    if len(drivers) > 1 and b1.button("다른 기사님 보기", use_container_width=True):
        st.session_state[idx_key] = idx + 1
        st.rerun()
    if b2.button("이 기사님으로 예약하기", type="primary", use_container_width=True):
        st.session_state[SELECTED_DRIVER_KEY] = d               # 예약하기 화면으로 기사 정보 전달 (선호 기사)
        st.session_state.pop("booking_result", None)            # 새 예약 진행: 이전 완료 화면 대신 4단계 예약하기부터
        # 화면에 보여준 견적(운임 내역 + 견적 당시 조건 해시)을 사전 확정 운임 동의·예약 저장에 그대로 사용
        request["quote"] = agreement.build_quote(request, estimate_result, service_type)
        st.switch_page("pages/6_Booking.py")
        st.switch_page("pages/6_Booking.py")


# ============================================================
# 7. 하단 이동 버튼
# ============================================================

if st.button("운송 조건 수정", use_container_width=True):
    st.switch_page("pages/1_Delivery_Request.py")