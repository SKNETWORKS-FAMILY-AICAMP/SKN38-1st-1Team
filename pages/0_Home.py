"""홈 — 서비스 소개, [운송 신청하기]·[요금표 보기], 이용 방법, 공공데이터(화물차 등록 현황) 간단 소개

운송 신청 폼은 pages/1_Delivery_Request.py, 버블 지도·시군구 상세는 pages/4_Truck_Map.py (상단 메뉴 '지역별 현황')
"""

import streamlit as st

from services.db import DBConnectionError
from services.truck_stats import format_month, load_truck_stats
from services.ui import how_it_works, image_data_uri, section_title, trimmed_image

# ── 1. 히어로 · 운송 신청 ────────────────────────────────────────────
with st.container(key="hero_home"):
    text, image = st.columns([11, 9], gap="large", vertical_alignment="center")
    with text:
        st.html(
            '<span class="jm-hero-badge">다마스 · 라보 · 1톤 생활 용달</span>'
            '<h1 class="jm-hero-title">짐 옮길 땐,<br><span class="hl">짐니!</span></h1>'
            '<div class="jm-hero-desc-row"><p class="jm-hero-desc">출발지·도착지와 짐 크기만 입력하면<br>'
            "내 짐에 맞는 차량과 기사님을 찾아드려요.</p>"
            f'<img src="{image_data_uri("sub2.png.jpg")}" alt=""></div>'
        )
        b1, b2, _ = st.columns([5, 5, 2])
        if b1.button("운송 신청하기", type="primary", width="stretch"):
            st.switch_page("pages/1_Delivery_Request.py")
        if b2.button("요금표 보기", width="stretch"):
            st.switch_page("pages/7_Fare_Table.py")
        st.html('<div class="jm-hero-chips"><span>카카오 주소 검색</span><span>실제 거리 기반 예상 운임</span>'
                "<span>예약번호로 운송 상태 확인</span></div>")
    with image:
        st.image(trimmed_image("jimni_main.jpg"), width="stretch")   # 바깥 흰 여백만 잘라서 표시

# ── 2. 이용 방법 ─────────────────────────────────────────────────────
st.space("large")
section_title("이용 방법", "다섯 단계면 운송 예약이 끝나요", "로그인 없이, 필요한 정보만 입력하면 됩니다.")
how_it_works()

# ── 3. 공공데이터 간단 소개 (지도·시군구 상세는 '지역별 현황' 페이지) ─────
st.space("large")
with st.container(key="soft_home_data"):
    info, figure = st.columns([3, 2], gap="large", vertical_alignment="center")
    with info:
        section_title("국토교통부 공공데이터", "전국 영업용 화물차 등록 현황",
                      "시도·시군구별 영업용 화물차 등록대수를 지도로 확인해 보세요.")
    with figure:
        try:
            stats = load_truck_stats()
            sido = stats["sido"]
            if sido.empty:
                st.info("저장된 화물차 등록 통계가 없습니다.")
            else:
                st.html(
                    '<div class="jm-home-stat">'
                    f'<p class="label">{format_month(stats["base_month"])} 기준 · 전국 등록대수</p>'
                    f'<p class="value">{int(sido["truck_count"].sum()):,}<span>대</span></p>'
                    '<p class="note">실제 운행 중이거나 지금 예약 가능한 차량 수가 아닙니다.</p></div>'
                )
        except DBConnectionError as e:
            st.error(str(e))
        if st.button("지역별 현황 보기", type="primary", width="stretch"):
            st.session_state["region_view"] = "배차 가능 기사 현황"   # 지역별 현황의 기본 화면으로 이동
            st.switch_page("pages/4_Truck_Map.py")
