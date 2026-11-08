
"""
운송 신청 페이지
핵심 기능 1: 운송 조건 입력 및 참고 운임 계산
"""

import streamlit as st
from datetime import date, time

from services.fare import estimate, SERVICE_RULES


st.set_page_config(
    page_title="운송 신청",
    page_icon="📦",
    layout="wide"
)

st.title("📦 운송 신청")
st.info("운송 조건을 입력하면 추천 차량과 예상 운임을 확인할 수 있습니다.")


# --------------------------------------------------
# 1. 운송 정보 입력
# --------------------------------------------------

st.subheader("1. 운송 정보")

with st.form("delivery_form"):

    delivery_type = st.radio(
        "운송 유형",
        ["일반 운송", "이사"],
        horizontal=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📍 출발지")

        origin = st.text_input(
            "출발지 주소",
            placeholder="예: 서울시 강남구 테헤란로 123"
        )

        o_floor = st.number_input(
            "출발지 층수", 1, 100, 1
        )

        o_elev = st.checkbox(
            "출발지 엘리베이터 있음",
            value=True
        )

    with col2:
        st.markdown("#### 📍 도착지")

        destination = st.text_input(
            "도착지 주소",
            placeholder="예: 서울시 마포구 월드컵북로 456"
        )

        d_floor = st.number_input(
            "도착지 층수", 1, 100, 1
        )

        d_elev = st.checkbox(
            "도착지 엘리베이터 있음",
            value=True
        )

    st.divider()

    # --------------------------------------------------
    # 2. 운송 물품
    # --------------------------------------------------

    st.subheader("2. 운송 물품")

    st.caption("물품 크기별 수량을 입력해 주세요.")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        s_count = st.number_input("소형 (S)", 0, value=0)

    with col2:
        m_count = st.number_input("중형 (M)", 0, value=0)

    with col3:
        l_count = st.number_input("대형 (L)", 0, value=0)

    with col4:
        xl_count = st.number_input("특대형 (XL)", 0, value=0)

    with col5:
        xxl_count = st.number_input("초대형 (XXL)", 0, value=0)

    st.divider()

    # --------------------------------------------------
    # 3. 추가 서비스 및 희망 일시
    # --------------------------------------------------

    st.subheader("3. 추가 서비스")

    helper_options = {
        "기사 운전만": "VEHICLE_ONLY",
        "기사 상하차 도움": "DRIVER_HELP",
        "작업 인력 1명 추가": "WORKER_1",
        "작업 인력 2명 추가": "WORKER_2"
    }

    helper_label = st.selectbox(
        "상하차 추가 인력",
        list(helper_options.keys())
    )

    helper = helper_options[helper_label]

    helper_fee = SERVICE_RULES[helper]["fee"]

    st.caption(f"추가 인력 비용: {helper_fee:,}원")

    col1, col2 = st.columns(2)

    with col1:
        desired_date = st.date_input(
            "희망 운송 날짜",
            value=date.today()
        )

    with col2:
        desired_time = st.time_input(
            "희망 운송 시간",
            value=time(9, 0)
        )

    st.divider()

    submitted = st.form_submit_button(
        "🚚 예상 운임 계산하기",
        use_container_width=True
    )


# --------------------------------------------------
# 4. 운임 계산
# --------------------------------------------------

if submitted:

    counts = {
        "S": s_count,
        "M": m_count,
        "L": l_count,
        "XL": xl_count,
        "XXL": xxl_count
    }

    if not origin.strip() or not destination.strip():
        st.warning("출발지와 도착지 주소를 모두 입력해 주세요.")

    elif sum(counts.values()) == 0:
        st.warning("운송할 물품을 한 개 이상 입력해 주세요.")

    else:

        try:
            with st.spinner("이동 거리와 예상 운임을 계산하고 있습니다..."):

                result = estimate(
                    origin_address=origin,
                    destination_address=destination,
                    item_counts=counts,
                    service_type=helper,
                    origin_floor=int(o_floor),
                    origin_elevator=o_elev,
                    destination_floor=int(d_floor),
                    destination_elevator=d_elev
                )

            # 거리 계산 실패 또는 차량 매칭 실패
            if "distance" not in result:

                st.error(
                    result.get(
                        "reason",
                        "운임 계산에 실패했습니다."
                    )
                )

            else:

                vehicle = result["vehicle"]
                distance = result["distance"]
                fare = result["fare"]

                st.success("예상 운임 계산이 완료되었습니다!")

                st.divider()
                st.subheader("📋 운송 예상 결과")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "추천 차량",
                        vehicle["vehicle_type"]
                    )

                with col2:
                    st.metric(
                        "예상 이동 거리",
                        f'{distance["distance_km"]}km'
                    )

                with col3:
                    st.metric(
                        "예상 소요 시간",
                        f'{distance["duration_minutes"]}분'
                    )

                # --------------------------------------------------
                # 수동 확인 조건
                # --------------------------------------------------

                if result["manual_check"]:

                    st.warning(
                        "물품의 실제 크기, 무게 또는 작업 환경에 "
                        "대한 추가 확인이 필요합니다. "
                        "실제 차량 배정 전 기사 확인이 필요합니다."
                    )

                # --------------------------------------------------
                # 운임 상세
                # --------------------------------------------------

                st.divider()
                st.subheader("💰 예상 운임 상세")

                breakdown = fare["fare_breakdown"]

                col1, col2 = st.columns(2)

                with col1:

                    st.write("기본 운임")
                    st.write(f'{breakdown["base_fare"]:,}원')

                    st.write("추가 인력 비용")
                    st.write(f'{breakdown["service_fee"]:,}원')

                with col2:

                    st.write("출발지 계단 비용")

                    origin_fee = breakdown["origin_stair_fee"]

                    st.write(
                        f"{origin_fee:,}원"
                        if origin_fee is not None
                        else "별도 협의"
                    )

                    st.write("도착지 계단 비용")

                    destination_fee = breakdown["destination_stair_fee"]

                    st.write(
                        f"{destination_fee:,}원"
                        if destination_fee is not None
                        else "별도 협의"
                    )

                st.divider()

                total_fare = result["total_fare"]

                if total_fare is not None:

                    st.metric(
                        "총 예상 운임",
                        f"{total_fare:,}원"
                    )

                else:

                    st.warning(
                        "일부 작업 조건에 대한 별도 협의가 필요하여 "
                        "최종 운임을 확정할 수 없습니다."
                    )

                st.caption(
                    "※ 본 금액은 참고 운임이며 실제 운송 비용과 "
                    "차이가 있을 수 있습니다."
                )

                # --------------------------------------------------
                # 입력 정보 확인
                # --------------------------------------------------

                with st.expander("입력한 운송 조건 확인"):

                    st.write(f"운송 유형: {delivery_type}")
                    st.write(f"출발지: {origin}")
                    st.write(f"도착지: {destination}")

                    st.write(
                        f"희망 일시: {desired_date} {desired_time}"
                    )

                    st.write(f"물품 수량: {counts}")
                    st.write(f"추가 서비스: {helper_label}")

        except Exception as e:

            st.error(f"운임 계산 중 오류가 발생했습니다: {e}")
