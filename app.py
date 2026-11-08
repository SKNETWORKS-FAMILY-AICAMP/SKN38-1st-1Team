"""짐니(JIMNI) — Streamlit 진입점 (실행: python -m streamlit run app.py)

- 첫 접속: 소개 화면 → [짐니 시작하기] → 홈
- 상단 메뉴: 홈 · 요청하기 / 예약 조회 / FAQ
- 메뉴에 없는 화면(운송 신청, 매칭 결과, 예약하기, 요금표, 지역별 화물차 현황)은 버튼으로 이동 (visibility="hidden")
- 로그인 없음 (비회원 이용)
- 공통 디자인: .streamlit/config.toml(테마) + services/ui.py(호버 등 CSS)
"""

import streamlit as st

from services.ui import apply_global_style, asset, logo_image, show_logo

st.set_page_config(page_title="짐니 JIMNI", page_icon=asset("jimni1.png"), layout="wide")
apply_global_style()
show_logo()

HOME_PATH = "pages/0_Home.py"


def landing():
    with st.container(key="hero_landing"):
        text, image = st.columns([3, 2], vertical_alignment="center")
        with text:
            st.image(logo_image("logo4.png"), width=200)
            st.markdown("# 짐 옮기는 소원,<br>짐니가 들어드릴게요.", unsafe_allow_html=True)
            st.write("복잡한 용달 예약도 짐니에게 맡겨보세요.  \n다마스부터 1톤 트럭까지, 내 짐에 딱 맞는 운송을 간편하게.")
            st.caption("다마스 · 라보 · 1톤, 원하는 운송을 한 번에")
            if st.button("짐니 시작하기", type="primary"):
                st.session_state["started"] = True
                st.switch_page(HOME_PATH)
        with image:
            st.image(asset("jimni1.png"), width=300)


started = st.session_state.get("started", False)

home = st.Page(HOME_PATH, title="홈 · 요청하기", icon=":material/home:", url_path="home", default=started)
lookup = st.Page("pages/3_Booking_Lookup.py", title="예약 조회", icon=":material/event_note:", url_path="booking-lookup")
faq = st.Page("pages/5_FAQ.py", title="FAQ", icon=":material/help:", url_path="faq")
hidden_pages = [
    st.Page(landing, title="짐니", url_path="start", default=not started, visibility="hidden"),
    st.Page("pages/1_Delivery_Request.py", title="운송 신청", url_path="request", visibility="hidden"),
    st.Page("pages/2_Driver_Matching.py", title="매칭 결과", url_path="matching", visibility="hidden"),
    st.Page("pages/6_Booking.py", title="예약하기", url_path="booking", visibility="hidden"),
    st.Page("pages/7_Fare_Table.py", title="요금표", url_path="fare-table", visibility="hidden"),
    st.Page("pages/4_Truck_Map.py", title="지역별 화물차 현황", url_path="truck-map", visibility="hidden"),
]

nav = st.navigation([home, lookup, faq, *hidden_pages], position="top" if started else "hidden")
nav.run()
