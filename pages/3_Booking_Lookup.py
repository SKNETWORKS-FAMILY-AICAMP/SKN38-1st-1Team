"""예약 조회 — 예약번호 + 연락처 확인 → 예약 상세·운송 상태 → 운송 완료 시 평점 저장

- DB에 저장된 실제 상태(bookings.status)를 보여주기만 하며 상태를 바꾸지 않는다.
- 데이터 변경은 평점(bookings.rating) 저장 하나뿐이다.
- 실시간 기사 위치 추적 기능은 없다.
"""

import streamlit as st

from services import booking_lookup as bl
from services.db import DBConnectionError, get_connection
from services.ui import status_stepper

AUTH_KEY = "lookup_auth"  # {"booking_id": int, "phone": str} — 확인에 성공한 조회 조건

st.title("예약 조회")

st.caption("예약번호와 예약할 때 입력한 연락처로 예약 내용과 운송 상태를 확인할 수 있어요.")
with st.form("lookup_form"):
    booking_no = st.text_input("예약번호", max_chars=18, placeholder="예약번호를 입력하세요")
    phone = st.text_input("예약자 연락처", max_chars=20, placeholder="예약할 때 입력한 연락처")
    submitted = st.form_submit_button("조회하기", type="primary")

if submitted:
    st.session_state.pop(AUTH_KEY, None)
    booking_id = bl.parse_booking_id(booking_no)
    if booking_id is None:
        st.error("예약번호는 숫자로 입력해 주세요.")
    elif not bl.is_valid_phone(phone):
        st.error("연락처를 정확히 입력해 주세요. (예: 010-1234-5678)")
    else:
        st.session_state[AUTH_KEY] = {"booking_id": booking_id, "phone": bl.normalize_phone(phone)}

auth = st.session_state.get(AUTH_KEY)
if not auth:
    st.stop()

try:
    with get_connection() as conn:
        booking = bl.find_booking(conn, auth["booking_id"], auth["phone"])
except DBConnectionError as e:
    st.error(str(e))
    st.stop()

if booking is None:
    # 예약번호가 없는 경우와 연락처가 다른 경우를 구분하지 않음 (다른 고객 예약 존재 여부 노출 방지)
    st.error("예약번호 또는 연락처가 일치하는 예약이 없습니다. 입력한 내용을 다시 확인해 주세요.")
    st.session_state.pop(AUTH_KEY, None)
    st.stop()

# ── 예약 정보 ─────────────────────────────────────────────────────────
def info_row(label: str, value: str) -> None:
    a, b = st.columns([1, 3])
    a.caption(label)
    b.markdown(value)


with st.container(border=True):
    st.subheader("예약 정보")
    info_row("예약번호", f"**{booking['booking_id']}**")
    info_row("출발지", booking["origin_address"])
    info_row("도착지", booking["dest_address"])
    info_row("예약 일시", f"{booking['scheduled_at']:%Y-%m-%d %H:%M}" if booking["scheduled_at"] else "-")
    if booking["driver_id"] is None:
        st.info("아직 배정된 기사가 없습니다.")
    else:
        verified = booking["verification_status"] == "VERIFIED"
        info_row("기사님", booking["driver_name"] + (" · 사업자 확인 완료" if verified else ""))
    info_row("차량 종류", booking["vehicle_type"] or "정보 없음")
    info_row("예상 운임", f"**{booking['estimated_fare']:,}원**" if booking["estimated_fare"] is not None else "-")

# ── 운송 상태 ─────────────────────────────────────────────────────────
status = (booking["status"] or "").strip().upper()
with st.container(border=True):
    st.subheader("운송 상태")
    if not status:
        st.warning("운송 상태 정보가 없습니다. 고객센터에 문의해 주세요.")
    elif status == "CANCELLED":
        st.warning("취소된 예약입니다.")
    elif status not in bl.STATUS_FLOW:
        st.warning(f"확인되지 않은 운송 상태입니다. ({status})")
    else:
        step = bl.STATUS_FLOW.index(status)
        status_stepper([bl.STATUS_LABELS[c] for c in bl.STATUS_FLOW], step)
        st.caption(f"현재 상태: {bl.STATUS_LABELS[status]}")
    if booking["status_updated_at"]:
        st.caption(f"상태 변경 시각: {booking['status_updated_at']:%Y-%m-%d %H:%M}")
    st.caption("실시간 기사 위치 추적은 제공하지 않습니다.")

# ── 평가 ─────────────────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("이용 평가")
    if status != "COMPLETED":
        st.info("운송이 완료된 뒤 평가할 수 있습니다.")
    elif booking["rating"] is not None:
        st.success(f"평가 완료: {booking['rating']}점")
    else:
        with st.form("rating_form", border=False):
            rating = st.radio("별점 평가", list(range(bl.RATING_MIN, bl.RATING_MAX + 1)), horizontal=True,
                              index=None, format_func=lambda v: "★" * v + "☆" * (bl.RATING_MAX - v))
            rated = st.form_submit_button("평가 제출하기", type="primary")
        if rated:
            if rating is None:
                st.error("평점을 선택해 주세요.")
            else:
                try:
                    with get_connection() as conn:
                        result = bl.submit_rating(conn, auth["booking_id"], auth["phone"], int(rating))
                except DBConnectionError as e:
                    st.error(str(e))
                else:
                    messages = {
                        bl.SAVED: None,
                        bl.ALREADY_RATED: "이미 평가한 예약입니다.",
                        bl.NOT_COMPLETED: "운송이 완료된 예약만 평가할 수 있습니다.",
                        bl.INVALID_RATING: "평점은 1~5점 사이로 선택해 주세요.",
                        bl.NOT_FOUND: "예약 정보를 확인할 수 없습니다. 다시 조회해 주세요.",
                    }
                    if result == bl.SAVED:
                        st.rerun()
                    st.error(messages[result])
