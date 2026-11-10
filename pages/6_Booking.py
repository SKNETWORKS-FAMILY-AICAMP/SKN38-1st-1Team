"""예약하기 — 최종 운임·작업 조건 확인 → 사전 동의 → 예약 확정(저장 + 시연용 기사 자동 배정) → 매칭 완료 알림

- 금액·차량·거리: 매칭 결과 화면에서 저장한 견적(request["quote"], 예준님 fare.estimate 결과) 그대로 사용
- 동의: services/agreement.py (조건·운임이 바뀌면 동의 자동 해제, 확정 직전에 다시 검증)
- 저장·배정: services/assignment.py → 예준님 matching.recommend_drivers + booking.create_booking 재사용
- 매칭 완료 알림은 DB에 저장된 예약을 다시 읽어 온 경우에만 표시
- 예약 저장·기사 배정은 이 화면의 [예약 확정하기]에서만 실행 (3단계 [이 기사님으로 예약하기]는 이 화면으로 이동만 함)
- 확정 직후 5단계 완료 화면 + 매칭 완료 팝업(st.dialog, 한 번만). 다시 확정을 눌러도 중복 저장하지 않음
"""

from html import escape

import streamlit as st

from services import agreement, assignment, notifications, settlement
from services import booking_lookup as bl
from services.db import DBConnectionError, get_connection
from services.transport_request import HELPER_OPTIONS, ITEM_SIZES, REQUEST_KEY, SELECTED_DRIVER_KEY
from services.ui import image_data_uri, step_header

RESULT_KEY = "booking_result"   # {"conditions_hash", "booking"(DB 행), "driver_vehicle", "phone"} — 확정 직후에만 존재
POPUP_KEY = "booking_match_popup"  # 매칭 완료 팝업을 띄울 예약번호 (한 번 띄우면 지움 → 다시 실행해도 안 뜸)
LOOKUP_AUTH_KEY = "lookup_auth"  # 예약 조회 화면의 확인 정보 (예약 직후 바로 조회되도록 채움)
SERVICE_NAMES = {"VEHICLE_ONLY": "추가 인력 없음", "DRIVER_HELP": "기사 상하차 도움", "WORKER_1": "추가 작업자 1명"}

request = st.session_state.get(REQUEST_KEY)
if not request:
    step_header(4)
    st.title("예약하기")
    st.warning("운송 조건 입력과 운임 확인을 먼저 완료해 주세요.")
    if st.button("운송 신청하러 가기"):
        st.switch_page("pages/1_Delivery_Request.py")
    st.stop()


def won(value) -> str:
    return f"{value:,}원" if isinstance(value, int) else "별도 협의"


def place(prefix: str, side: str) -> str:
    detail = request.get(f"{side}_detail_address") or ""
    floor = request[f"{prefix}_floor"]
    floor_text = f"지하 {-floor}층" if floor < 0 else f"{floor}층"
    elevator = "엘리베이터 있음" if request[f"{prefix}_has_elevator"] else "엘리베이터 없음"
    addr = request["origin_address" if prefix == "origin" else "dest_address"]
    return f"{escape(addr)}{(' ' + escape(detail)) if detail else ''}<small>{floor_text} · {elevator}</small>"


def vehicle_text(b: dict) -> str:
    """배정 기사님 차량 (운임 기준 차량과 다르면 함께 표시)."""
    driver_v, fare_v = b.get("driver_vehicle_type"), b.get("vehicle_type")
    if driver_v and fare_v and driver_v != fare_v:
        return f"{driver_v} (운임 기준 {fare_v})"
    return driver_v or fare_v or "-"


def matched_title(b: dict) -> str:
    """DB에 저장된 driver_id로 조회한 기사 이름 기준 (조회 실패 시 이름 없이)."""
    name = (b.get("driver_name") or "").strip()
    return f"{name} 기사님이 매칭되었습니다!" if name else "기사님이 매칭되었습니다!"


def open_lookup(b: dict, phone: str) -> None:
    st.session_state[LOOKUP_AUTH_KEY] = {"booking_id": b["booking_id"], "phone": phone}
    st.switch_page("pages/3_Booking_Lookup.py")


@st.dialog("예약 완료", width="small")
def match_popup(b: dict, phone: str) -> None:
    st.html(
        '<div class="jm-match-pop">'
        f'<img src="{image_data_uri("jimni1.png")}" alt="">'
        f'<p class="t">{escape(matched_title(b))}</p>'
        '<p class="d">운송 예약이 완료되었어요.<br>예약 내역에서 자세한 정보를 확인해 주세요.</p>'
        "<dl>"
        f"<div><dt>예약번호</dt><dd>{b['booking_id']}</dd></div>"
        f"<div><dt>차량 종류</dt><dd>{escape(vehicle_text(b))}</dd></div>"
        "</dl></div>"
    )
    c1, c2 = st.columns(2)
    if c1.button("예약 내역 확인하기", type="primary", width="stretch", key="popup_lookup"):
        open_lookup(b, phone)
    if c2.button("닫기", width="stretch", key="popup_close"):
        st.rerun()   # 팝업만 닫히고 5단계 완료 화면 유지


# ── 5단계 예약 완료 화면 (방금 [예약 확정하기]로 저장된 경우에만) ────────────
result = st.session_state.get(RESULT_KEY)
if result and result["conditions_hash"] == agreement.conditions_hash(request):
    step_header(5)
    st.title("예약 완료")
    b = result["booking"]
    notifications.render_notice({**notifications.NOTICES["BOOKED"], "title": matched_title(b)}, [
        ("예약번호", str(b["booking_id"])),
        ("배정 기사님", f"{b['driver_name']} 기사님" if b.get("driver_name") else "-"),
        ("차량 종류", vehicle_text(b)),
        ("운송 일시", f"{b['scheduled_at']:%Y년 %m월 %d일 %H:%M}"),
        ("합의 운임 (결제 금액)", won(b["estimated_fare"])),   # bookings.estimated_fare = 운임 + 이용료
    ])
    c1, c2, _ = st.columns([2, 1, 2])
    if c1.button("예약 조회에서 확인하기", type="primary", width="stretch", icon=":material/event_note:"):
        open_lookup(b, result["phone"])
    if c2.button("홈으로", width="stretch"):
        st.switch_page("pages/0_Home.py")
    if st.session_state.pop(POPUP_KEY, None) == b["booking_id"]:   # 확정 직후 한 번만
        match_popup(b, result["phone"])
    st.stop()

# ── 1. 최종 운임 · 작업 조건 확인 ───────────────────────────────────────
step_header(4)
st.title("예약하기")
quote = request.get("quote")
problem = agreement.quote_problem(request, quote)
if problem:
    st.warning(problem)
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("운임 다시 확인하기", type="primary", width="stretch"):
        st.switch_page("pages/2_Driver_Matching.py")
    if c2.button("운송 조건 수정", width="stretch"):
        st.switch_page("pages/1_Delivery_Request.py")
    st.stop()

items = " · ".join(f"{s} {request.get(f'item_{s.lower()}_count', 0)}개" for s in ITEM_SIZES
                   if request.get(f"item_{s.lower()}_count", 0)) or "-"
distance = f"{quote['distance_km']} km" if quote.get("distance_km") is not None else "-"
if quote.get("estimated_minutes") is not None:
    distance += f" · 약 {round(quote['estimated_minutes'])}분"
if quote.get("distance_estimated"):
    distance += " (추정)"
fare_rows = [
    (f"기본 운임 ({escape(quote['vehicle_type'])} · 거리 구간 {escape(str(quote.get('distance_code') or '-'))})",
     quote.get("base_fare")),
    (f"추가 인력 ({SERVICE_NAMES.get(quote.get('service_type'), '-')})", quote.get("service_fee")),
    ("출발지 계단 작업", quote.get("origin_stair_fee")),
    ("도착지 계단 작업", quote.get("destination_stair_fee")),
    (f"서비스 이용료 ({settlement.SERVICE_FEE_PCT}%)", quote.get("usage_fee")),
]
st.html(
    '<div class="jm-terms"><p class="jm-terms-title">최종 운임 · 작업 조건 확인</p>'
    '<p class="jm-terms-sub">예약을 확정하면 아래 조건과 운임으로 예약이 저장돼요.</p><dl class="grid">'
    f"<div><dt>출발지</dt><dd>{place('origin', 'pickup')}</dd></div>"
    f"<div><dt>도착지</dt><dd>{place('dest', 'dropoff')}</dd></div>"
    f"<div><dt>운송 일시</dt><dd>{request['scheduled_at']:%Y년 %m월 %d일 %H:%M}</dd></div>"
    f"<div><dt>추천 차량</dt><dd>{escape(quote['vehicle_type'])}</dd></div>"
    f"<div><dt>물품</dt><dd>{escape(items)}</dd></div>"
    f"<div><dt>추가 인력</dt><dd>{escape(HELPER_OPTIONS.get(request['helper_option'], request['helper_option']))}</dd></div>"
    f"<div><dt>운송 거리</dt><dd>{escape(distance)}</dd></div>"
    "</dl><table class=\"fare\">"
    + "".join(f"<tr><th>{label}</th><td>{won(v)}</td></tr>" for label, v in fare_rows)
    + f"<tr class=\"total\"><th>최종 합의 운임 (결제 금액)</th><td>{won(quote['payable_total'])}</td></tr></table>"
    "<p class=\"jm-terms-note\">운임은 짐니 운임표(차량·거리 구간, 인력, 계단 작업) 기준으로 계산했고, 서비스 이용료(5%)를 더한 금액을 결제해요. "
    "합의한 조건과 다른 추가 작업은 현장에서 요구할 수 없어요.</p></div>"
)

if quote.get("vehicle_check_note"):
    st.caption(f"차량 확인 안내: 차량은 물품 크기별 개수 기준으로 추천했어요.")

preferred = st.session_state.get(SELECTED_DRIVER_KEY)
if preferred:
    st.caption(f"추천 기사님: {preferred['nickname']} · {preferred['vehicle_type']}")

# ── 2. 예약자 정보 · 동의 · 확정 ────────────────────────────────────────
with st.container(key="jm_booking_form"):
    st.html('<p class="jm-addr-label">예약자 정보</p>')
    c1, c2 = st.columns(2)
    name = c1.text_input("예약자 이름", max_chars=50, key="booking_name")
    phone = c2.text_input("연락처", max_chars=20, placeholder="010-0000-0000", key="booking_phone")

    terms_hash = agreement.terms_hash(request, quote)
    agree_key = f"agree_{terms_hash[:16]}"   # 조건·운임이 바뀌면 새 체크박스 → 기존 동의 자동 해제
    st.checkbox(agreement.AGREEMENT_TEXT, key=agree_key,
                on_change=lambda: agreement.record_agreement(st.session_state, request, quote,
                                                             st.session_state.get(agree_key, False)))
    if not st.session_state.get(agree_key):
        agreement.record_agreement(st.session_state, request, quote, False)
    agreed = agreement.is_agreed(st.session_state, request, quote)
    confirm = st.button("예약 확정하기", type="primary", width="stretch", disabled=not agreed,
                        icon=":material/check_circle:")
    if not agreed:
        st.caption("조건과 운임에 동의해야 예약을 확정할 수 있어요.")

if confirm:
    errors = []
    if not name.strip():
        errors.append("예약자 이름을 입력해 주세요.")
    if not bl.is_valid_phone(phone):
        errors.append("연락처를 정확히 입력해 주세요. (예: 010-1234-5678)")
    if not agreement.is_agreed(st.session_state, request, quote):   # 확정 직전 다시 확인
        errors.append("운송 조건이나 운임이 바뀌어 다시 동의가 필요해요.")
    for msg in errors:
        st.error(msg)
    if not errors:
        try:
            with st.spinner("예약을 저장하고 기사님을 배정하고 있어요..."):
                saved = assignment.confirm_booking(request, quote, {"name": name.strip(), "phone": phone},
                                                   preferred, agreement.agreement_record(st.session_state, request, quote))
                with get_connection() as conn:   # 실제 저장된 예약을 다시 읽어 알림에 사용
                    row = bl.find_booking(conn, saved["booking_id"], bl.normalize_phone(phone))
        except assignment.AssignmentError as e:
            st.error(str(e))
        except DBConnectionError as e:
            st.error(str(e))
        except Exception as e:  # 저장 중 오류: create_booking이 롤백하므로 예약은 남지 않음
            st.error(f"예약을 저장하지 못했어요. 잠시 후 다시 시도해 주세요. ({e})")
        else:
            if row is None:
                st.error("예약 저장 결과를 확인하지 못했어요. 예약 조회에서 확인해 주세요.")
            else:
                st.session_state[RESULT_KEY] = {
                    "conditions_hash": agreement.conditions_hash(request), "booking": row,
                    "driver_vehicle": saved["driver"].get("vehicle_type"), "phone": bl.normalize_phone(phone),
                }
                st.session_state[POPUP_KEY] = row["booking_id"]
                st.session_state.pop(agreement.AGREEMENT_KEY, None)
                st.rerun()

if st.button("운임 다시 확인하기", type="tertiary", icon=":material/arrow_back:"):
    st.switch_page("pages/2_Driver_Matching.py")
