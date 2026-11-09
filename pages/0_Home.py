"""홈 · 요청하기 — 서비스 소개, [운송 신청하기]·[요금표 보기], 이용 방법, 시도별 화물차 현황 미리보기

운송 신청 폼은 pages/1_Delivery_Request.py, 지도 상세는 pages/4_Truck_Map.py (별도 페이지)
"""

import streamlit as st

from services.db import DBConnectionError
from services.truck_map import build_deck, is_consistent, load_points, match_points, picked_sido
from services.truck_stats import DATA_NOTE, format_month, load_truck_stats
from services.ui import asset, how_it_works, section_title

# ── 히어로 ──────────────────────────────────────────────────────────
with st.container(key="hero_home"):
    text, image = st.columns([11, 9], gap="large", vertical_alignment="center")
    with text:
        st.html(
            '<span class="jm-hero-badge">다마스 · 라보 · 1톤 생활 용달</span>'
            '<h1 class="jm-hero-title">짐 옮길 땐,<br><span class="hl">짐니.</span></h1>'
            '<p class="jm-hero-desc">출발지·도착지와 짐 크기만 입력하면<br>'
            "내 짐에 맞는 차량과 기사님을 찾아드려요.</p>"
        )
        b1, b2, _ = st.columns([5, 4, 3])
        if b1.button("운송 신청하기", type="primary", width="stretch"):
            st.switch_page("pages/1_Delivery_Request.py")
        if b2.button("요금표 보기", width="stretch"):
            st.switch_page("pages/7_Fare_Table.py")
        st.html('<div class="jm-hero-chips"><span>카카오 주소 검색</span><span>실제 거리 기반 예상 운임</span>'
                "<span>예약번호로 운송 상태 확인</span></div>")
    with image:
        st.image(asset("sub.png"), width="stretch")

# ── 이용 방법 ───────────────────────────────────────────────────────
st.space("large")
section_title("이용 방법", "다섯 단계면 운송 예약이 끝나요", "로그인 없이, 필요한 정보만 입력하면 됩니다.")
how_it_works()

# ── 시도별 화물차 현황 미리보기 ─────────────────────────────────────
st.space("large")
with st.container(key="soft_home_map"):
    # 위쪽 정렬: 버블을 눌러 지도 아래 지역 등록대수가 나타나도 왼쪽 안내 문구가 움직이지 않음
    info, mapcol = st.columns([2, 3], gap="large", vertical_alignment="top")
    try:
        stats = load_truck_stats()
        sido = stats["sido"]
        month = format_month(stats["base_month"])
        with info:
            section_title("공공데이터", "우리 지역 영업용 화물차는<br>얼마나 될까요?",
                          f"국토교통부 자동차 등록 통계({month} 기준)로 시도별 영업용 화물차 등록대수를 보여드려요.")
            st.metric("전국 영업용 화물차 등록대수", f"{int(sido['truck_count'].sum()):,}대")
            if st.button("지역별 화물차 현황 자세히 보기"):
                st.switch_page("pages/4_Truck_Map.py")
        with mapcol:
            points = load_points()
            if points is not None and is_consistent(match_points(points, sido)):
                event = st.pydeck_chart(build_deck(points, sido, month, zoom=5.7), on_select="rerun",
                                        selection_mode="single-object", key="home_sido_map", height=440)
                pick = picked_sido(event)
                if pick:
                    count = int(sido.loc[sido["sido_name"] == pick, "truck_count"].iloc[0])
                    st.metric(f"{pick} 영업용 화물차 등록대수", f"{count:,}대")
                st.caption("버블이 클수록 등록대수가 많습니다. 버블은 시도 대표 위치이며 차량 위치가 아닙니다.")
            else:
                st.bar_chart(sido.set_index("sido_name")["truck_count"], horizontal=True,
                             x_label="등록대수(대)", y_label="")
            st.caption(DATA_NOTE)
    except DBConnectionError as e:
        st.error(str(e))
        if st.button("지역별 화물차 현황 자세히 보기"):
            st.switch_page("pages/4_Truck_Map.py")

# ── 브랜드 소개 · 신청 유도 (짐 + 지니: 짐 옮기는 소원을 들어주는 지니) ──────
st.space("large")
with st.container(key="cta_home"):
    msg, genie = st.columns([3, 2], gap="large", vertical_alignment="center")
    with msg:
        st.html('<h2 class="jm-section-title" style="color:#fff">짐 옮기는 소원,<br>짐니가 들어드릴게요.</h2>'
                '<p class="jm-section-desc" style="color:rgba(255,255,255,.85)">복잡한 용달 예약도 짐니에게 맡겨보세요.<br>'
                "다마스부터 1톤 트럭까지, 내 짐에 딱 맞는 운송을 간편하게.</p>")
        if st.button("운송 신청하기", type="primary", key="home_bottom_request"):  # key가 'cta'로 시작하면 영역 CSS가 버튼에도 적용됨
            st.switch_page("pages/1_Delivery_Request.py")
    with genie:
        st.image(asset("jimni1.png"), width=260)
