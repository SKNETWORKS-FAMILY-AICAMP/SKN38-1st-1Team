"""예약 조회 — 예약번호 + 연락처 확인 → 예약 상세·운송 상태 → 운송 완료 시 평점 저장

- DB에 저장된 실제 상태(bookings.status)를 보여주기만 하며 상태를 바꾸지 않는다.
  (예외: 시연 모드 bl.DEMO_AUTO_PROGRESS — DEMO_STEP_SECONDS초마다 한 단계씩 진행, 진행 바로 표시)
- 데이터 변경은 평점(bookings.rating, 0.5점 단위) 저장 하나뿐이다. (시연 모드의 상태 진행 제외)
- 운송 완료 시 화면 가운데 별점 창이 뜬다 (뒤 화면 어둡게). [나중에 하기]로 닫고 [평가하기]로 다시 열 수 있다.
- 웹 알림: DB 상태값(BOOKED/DEPARTED/IN_TRANSIT/COMPLETED)에 맞는 알림만 표시 (services/notifications.py)
- 실시간 기사 위치 추적 기능은 없다.
"""
import html
import math
import time

import streamlit as st

from services import booking_lookup as bl
from services import notifications
from services.db import DBConnectionError, get_connection
from services.ui import status_stepper

# 운송 상태별 지니 그림 (예약 완료: 체크리스트 · 기사 출발: 달려가는 지니 · 운송 중: 짐 든 지니 · 운송 완료: 짐 내려놓은 지니)
STATUS_GENIES = {"BOOKED": "jimni2.png", "DEPARTED": "jimni1.png", "IN_TRANSIT": "jimni4.png", "COMPLETED": "jimni5.png"}
AUTH_KEY = "lookup_auth"          # {"booking_id": int, "phone": str} — 확인에 성공한 조회 조건
DEMO_CLOCK_KEY = "demo_clock"     # 시연 모드: {예약번호: 마지막으로 단계가 넘어간 시각}
DEMO_DONE_KEY = "demo_done_at"    # 시연 모드: {예약번호: 운송 완료를 처음 본 시각}

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
        st.session_state.get(DEMO_CLOCK_KEY, {}).pop(booking_id, None)     # 다시 조회하면 시간 새로 세기
        st.session_state.get(DEMO_DONE_KEY, {}).pop(booking_id, None)
        st.session_state.pop(f"rating_dismissed_{booking_id}", None)

auth = st.session_state.get(AUTH_KEY)
if not auth:
    st.stop()

bid = auth["booking_id"]
clock = st.session_state.setdefault(DEMO_CLOCK_KEY, {})
done_at = st.session_state.setdefault(DEMO_DONE_KEY, {})
clock.setdefault(bid, time.time())                          # 처음 조회한 순간부터 시간 세기


def demo_advance(conn) -> bool:
    """시연 모드: 마지막 단계 변경 후 DEMO_STEP_SECONDS초가 지났으면 한 단계 진행 (DB는 그때만 접속)."""
    if time.time() - clock[bid] < bl.DEMO_STEP_SECONDS:
        return False
    new_status = bl.advance_demo_status(conn, bid, auth["phone"], len(bl.STATUS_FLOW))
    if not new_status:
        return False
    clock[bid] = time.time()
    if new_status == "COMPLETED":
        done_at[bid] = time.time()                          # 별점 창 시간 계산용
    return True


try:
    with get_connection() as conn:
        demo_advance(conn)
        booking = bl.find_booking(conn, bid, auth["phone"])
except DBConnectionError as e:
    st.error(str(e))
    st.stop()

if booking is None:
    # 예약번호가 없는 경우와 연락처가 다른 경우를 구분하지 않음 (다른 고객 예약 존재 여부 노출 방지)
    st.error("예약번호 또는 연락처가 일치하는 예약이 없습니다. 입력한 내용을 다시 확인해 주세요.")
    st.session_state.pop(AUTH_KEY, None)
    st.stop()

# ── 상태 알림 (DB 상태 그대로) ─────────────────────────────────────────
status = (booking["status"] or "").strip().upper()
notice = notifications.status_notice(status) if booking["driver_id"] is not None else None
if notice:
    notifications.render_notice(notice)
    notifications.toast_once(f"{booking['booking_id']}:{status}", notice)


# ── 예약 정보 ─────────────────────────────────────────────────────────
def info_row(label: str, value: str) -> None:
    a, b = st.columns([1, 3])
    a.caption(label)
    b.markdown(value)


def vehicle_text(b: dict) -> str:
    """배정 기사님 차량 (운임 기준 차량과 다르면 함께 표시: 더 큰 차량 기사님이 배정될 수 있음)."""
    driver_v, fare_v = b.get("driver_vehicle_type"), b.get("vehicle_type")
    if driver_v and fare_v and driver_v != fare_v:
        return f"{driver_v} (운임은 {fare_v} 기준)"   # 근처에 같은 차종이 없어 더 큰 차량이 배정된 경우
    return driver_v or fare_v or "정보 없음"


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
        name = booking["driver_name"].replace("*", "\\*")   # 마스킹 별표가 굵게 표시로 바뀌지 않게
        info_row("기사님", f"{name} 기사님" + (" · 사업자 확인 완료" if verified else ""))
    info_row("차량 종류", vehicle_text(booking))
    info_row("운임", f"**{booking['estimated_fare']:,}원**" if booking["estimated_fare"] is not None else "-")


# ── 시연 모드: 진행 바 (지니 그림 바로 아래) ─────────────────────────
DEMO_MESSAGES = {
    "BOOKED": "기사님이 출발 준비 중이에요",
    "DEPARTED": "기사님이 출발지로 가고 있어요",
    "IN_TRANSIT": "짐을 싣고 도착지로 이동 중이에요",
}


@st.fragment(run_every="1s")
def demo_progress():
    elapsed = time.time() - clock[bid]
    left = max(0, bl.DEMO_STEP_SECONDS - int(elapsed))
    next_label = bl.STATUS_LABELS[bl.STATUS_FLOW[bl.STATUS_FLOW.index(status) + 1]]
    st.progress(min(elapsed / bl.DEMO_STEP_SECONDS, 1.0),
                text=f"🚚 {DEMO_MESSAGES[status]} · {left}초 뒤 '{next_label}'")
    try:
        with get_connection() as conn:
            if demo_advance(conn):
                st.rerun()
    except DBConnectionError:
        pass


# ── 운송 상태 ─────────────────────────────────────────────────────────
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
        status_stepper([bl.STATUS_LABELS[c] for c in bl.STATUS_FLOW], step,
                       images=[STATUS_GENIES[c] for c in bl.STATUS_FLOW])
        st.caption(f"현재 상태: {bl.STATUS_LABELS[status]}")
        if bl.DEMO_AUTO_PROGRESS and status in bl.STATUS_FLOW[:-1]:
            demo_progress()
    if booking["status_updated_at"]:
        st.caption(f"상태 변경 시각: {booking['status_updated_at']:%Y-%m-%d %H:%M}")
    st.caption("실시간 기사 위치 추적은 제공하지 않습니다.")


# ── 평가: 운송 완료 시 화면 가운데 별점 창 (뒤는 어둡게) ─────────────
RATING_MESSAGES = {
    bl.ALREADY_RATED: "이미 평가한 예약입니다.",
    bl.NOT_COMPLETED: "운송이 완료된 예약만 평가할 수 있습니다.",
    bl.INVALID_RATING: "별점은 0.5 ~ 5점 사이로 선택해 주세요.",
    bl.NOT_FOUND: "예약 정보를 확인할 수 없습니다. 다시 조회해 주세요.",
}
RATING_WORDS = {1: "별로예요", 2: "그저 그래요", 3: "보통이에요", 4: "좋아요", 5: "최고예요"}
DISMISS_KEY = f"rating_dismissed_{bid}"                      # [나중에 하기]를 눌렀는지


def stars_html(value, size: int = 46) -> str:
    """회색 별 5개 위에 금색 별을 점수만큼 덮어 그림 (반 개까지 표시)."""
    pct = float(value) / bl.RATING_MAX * 100
    return (f'<span style="position:relative;display:inline-block;font-size:{size}px;line-height:1.1">'
            f'<span style="color:#e5e7eb">★★★★★</span>'
            f'<span style="position:absolute;top:0;left:0;width:{pct}%;overflow:hidden;white-space:nowrap;'
            f'color:#fbbf24">★★★★★</span></span>')


def rating_modal() -> None:
    """화면 전체를 어둡게 덮고 정가운데 흰 박스에서 별점 입력."""
    st.html("""<style>
    .st-key-rating_modal { position: fixed !important; inset: 0; width: 100vw !important; height: 100vh;
        z-index: 1000000; background: rgba(15, 23, 42, .6);
        display: flex !important; flex-direction: column !important;
        align-items: center !important; justify-content: center !important; }
    .st-key-rating_modal > div { width: 100% !important; }
    .st-key-rating_box { background: #fff; border-radius: 22px; padding: 36px 32px 28px;
        width: min(440px, 90vw) !important; margin: 0 auto !important;
        box-shadow: 0 24px 60px rgba(0, 0, 0, .3); }
    .st-key-rating_value [data-testid="stSliderThumbValue"],
    .st-key-rating_value [data-testid="stSliderTickBarMin"],
    .st-key-rating_value [data-testid="stSliderTickBarMax"] { display: none !important; }
    </style>""")
    driver = html.escape(booking["driver_name"] or "")
    with st.container(key="rating_modal"):
        with st.container(key="rating_box"):
            st.html('<div style="text-align:center">'
                    '<div style="font-size:1.45rem;font-weight:700;color:#0f172a">운송이 완료되었어요</div>'
                    f'<div style="margin-top:.4rem;color:#475569"><b>{driver} 기사님</b>과의 운송은 어떠셨나요?</div></div>')
            stars_slot = st.empty()                          # 슬라이더 값으로 아래에서 채움
            value = st.slider("별점", bl.RATING_MIN, bl.RATING_MAX, bl.RATING_MAX, bl.RATING_STEP,
                              key="rating_value", label_visibility="collapsed")
            stars_slot.html(f'<div style="text-align:center;margin:.6rem 0 .2rem">{stars_html(value)}'
                            f'<div style="margin-top:.3rem;font-weight:600;color:#b45309">'
                            f'{value:.1f}점 · {RATING_WORDS[math.ceil(value)]}</div></div>')
            c1, c2 = st.columns(2)
            if c1.button("나중에 하기", key="rating_later", use_container_width=True):
                st.session_state[DISMISS_KEY] = True
                st.rerun()
            if c2.button("평가 제출하기", key="rating_submit", type="primary", use_container_width=True):
                try:
                    with get_connection() as conn:
                        result = bl.submit_rating(conn, bid, auth["phone"], value)
                except DBConnectionError as e:
                    st.error(str(e))
                    return
                if result != bl.SAVED:
                    st.error(RATING_MESSAGES[result])
                    return
                st.toast("평가해 주셔서 감사합니다!")
                st.rerun()                                   # 창 닫고 '평가 완료' 표시


with st.container(border=True):
    st.subheader("이용 평가")
    if status != "COMPLETED":
        st.info("운송이 완료된 뒤 평가할 수 있습니다.")
    elif booking["rating"] is not None:
        st.html(f'{stars_html(booking["rating"], 26)}'
                f'<span style="margin-left:.6rem;font-weight:600">{float(booking["rating"]):.1f}점 · 평가 완료</span>')
    elif st.button("평가하기", type="primary"):
        st.session_state.pop(DISMISS_KEY, None)              # 닫았던 별점 창 다시 열기
        st.rerun()

# 운송 완료 + 평가 전 + [나중에 하기] 안 누름 → 별점 창 (DEMO_POPUP_DELAY초 뒤)
need_rating = status == "COMPLETED" and booking["rating"] is None and not st.session_state.get(DISMISS_KEY)
if need_rating:
    done_at.setdefault(bid, time.time())
    if time.time() - done_at[bid] >= bl.DEMO_POPUP_DELAY:
        rating_modal()
    elif bl.DEMO_AUTO_PROGRESS:

        @st.fragment(run_every="1s")
        def _popup_wait():
            if time.time() - done_at[bid] >= bl.DEMO_POPUP_DELAY:
                st.rerun()

        _popup_wait()