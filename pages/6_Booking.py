"""예약하기 — 입력 화면 구조만 구현 (예약 저장·예약번호 발급은 아직 미연결)

연결 위치: services/booking.py (새로 만들 담당자)
    create_booking(request: dict, driver: dict, customer: dict) -> int   # bookings INSERT 후 booking_id 반환
이 함수가 생기기 전까지 [예약 확정] 버튼은 비활성화되고, 예약번호를 발급하거나 저장하지 않는다.
"""

import streamlit as st

from services.booking_lookup import is_valid_phone
from services.transport_request import REQUEST_KEY, SELECTED_DRIVER_KEY
from services.ui import step_header

try:
    from services.booking import create_booking
except ImportError:
    create_booking = None

step_header(4)
st.title("예약하기")

request = st.session_state.get(REQUEST_KEY)
driver = st.session_state.get(SELECTED_DRIVER_KEY)
if not request or not driver:
    st.warning("운송 조건 입력과 기사 선택을 먼저 완료해 주세요.")
    if st.button("운송 신청하러 가기"):
        st.switch_page("pages/1_Delivery_Request.py")
    st.stop()

if create_booking is None:
    st.info("예약 저장 기능이 아직 연결되지 않아 지금은 예약을 접수할 수 없습니다.")

with st.form("booking_form"):
    st.markdown("**고객 정보 입력**")
    name = st.text_input("예약자 이름", max_chars=50)
    phone = st.text_input("연락처", max_chars=20, placeholder="010-0000-0000")
    note = st.text_area("요청사항", max_chars=300)
    confirmed = st.form_submit_button("예약 확정", type="primary", disabled=create_booking is None)

if confirmed and create_booking is not None:
    errors = []
    if not name.strip():
        errors.append("예약자 이름을 입력해 주세요.")
    if not is_valid_phone(phone):
        errors.append("연락처를 정확히 입력해 주세요.")
    for msg in errors:
        st.error(msg)
    if not errors:
        booking_id = create_booking(request, driver, {"name": name.strip(), "phone": phone, "note": note.strip()})
        st.success(f"예약번호: {booking_id}")
