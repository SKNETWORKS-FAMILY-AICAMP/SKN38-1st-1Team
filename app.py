"""짐니(JIMNI) — Streamlit 진입점 (실행: python -m streamlit run app.py)

- 첫 접속부터 홈 화면 + 상단 메뉴 (홈 / 운송 신청 / 지역별 현황 / 예약 조회 / FAQ), 로고를 누르면 홈으로 이동
- 메뉴에 없는 화면(매칭 결과, 예약하기, 요금표)은 버튼·푸터 링크로 이동 (visibility="hidden")
- 로그인 없음 (비회원 이용)
- 공통 디자인: .streamlit/config.toml(테마) + services/ui.py(헤더·버튼·카드 CSS, 공통 푸터)
"""

import streamlit as st

from services.ui import apply_global_style, asset, render_footer, show_logo

st.set_page_config(page_title="짐니 JIMNI", page_icon=asset("jimni1.png"), layout="wide")
apply_global_style()
show_logo()

home = st.Page("pages/0_Home.py", title="홈", icon=":material/home:", default=True)
menu_pages = [
    home,
    st.Page("pages/1_Delivery_Request.py", title="운송 신청", icon=":material/local_shipping:", url_path="request"),
    st.Page("pages/4_Truck_Map.py", title="지역별 현황", icon=":material/map:", url_path="truck-map"),
    st.Page("pages/3_Booking_Lookup.py", title="예약 조회", icon=":material/event_note:", url_path="booking-lookup"),
    st.Page("pages/8_Driver_Login.py", title="파트너센터", icon=":material/badge:", url_path="driver-login"),
    st.Page("pages/5_FAQ.py", title="FAQ", icon=":material/help:", url_path="faq"),
]
hidden_pages = [
    st.Page("pages/2_Driver_Matching.py", title="매칭 결과", url_path="matching", visibility="hidden"),
    st.Page("pages/6_Booking.py", title="예약하기", url_path="booking", visibility="hidden"),
    st.Page("pages/7_Fare_Table.py", title="요금표", url_path="fare-table", visibility="hidden"),
]

nav = st.navigation([*menu_pages, *hidden_pages], position="top")

# 페이지 본문 자리를 먼저 만들고 푸터를 그린 뒤 페이지를 실행한다.
# (페이지가 중간에 st.stop()으로 끝나도 푸터는 항상 본문 아래에 표시됨)
body = st.container()
render_footer()
with body:
    nav.run()
