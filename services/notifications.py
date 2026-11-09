"""웹사이트 내부 알림 (카카오톡·SMS·이메일 발송 없음)

- 예약 상태(bookings.status) 값에 맞는 알림 문구만 고른다. 상태를 바꾸거나 시간 경과로 알림을 만들지 않는다.
- ① 매칭 완료: 예약·기사 배정이 DB에 저장된 직후 (예약하기 화면)
- ② 기사 출발 / ③ 운송 완료: 예약 조회에서 DB 상태가 DEPARTED / COMPLETED일 때
"""

from __future__ import annotations

from html import escape

import streamlit as st

NOTICES = {
    "BOOKED": {"icon": "✅", "title": "기사님이 매칭되었습니다!",
               "lines": ["운송을 담당할 기사님이 배정되었어요.", "예약 내역에서 기사님과 차량 정보를 확인해 주세요."]},
    "DEPARTED": {"icon": "🚚", "title": "기사님이 출발했어요!",
                 "lines": ["기사님이 출발지로 이동 중이에요.", "예약 내역에서 운송 상태를 확인해 주세요."]},
    "IN_TRANSIT": {"icon": "📦", "title": "운송 중이에요",
                   "lines": ["짐을 싣고 도착지로 이동 중이에요.", "예약 내역에서 운송 상태를 확인해 주세요."]},
    "COMPLETED": {"icon": "🎉", "title": "운송이 완료되었습니다!",
                  "lines": ["운송이 완료되었어요.", "이용 경험을 별점으로 남겨 주세요."]},
}


def status_notice(status: str | None) -> dict | None:
    """DB 상태값에 해당하는 알림 (CANCELLED·알 수 없는 값은 None)."""
    return NOTICES.get((status or "").strip().upper())


def render_notice(notice: dict, details: list[tuple[str, str]] | None = None) -> None:
    rows = "".join(f"<div><dt>{escape(k)}</dt><dd>{escape(v)}</dd></div>" for k, v in (details or []))
    st.html(
        f'<div class="jm-notice" role="status"><div class="ic">{notice["icon"]}</div><div class="body">'
        f'<p class="t">{escape(notice["title"])}</p><p class="d">{"<br>".join(escape(x) for x in notice["lines"])}</p>'
        + (f"<dl>{rows}</dl>" if rows else "") + "</div></div>"
    )


def toast_once(key: str, notice: dict) -> None:
    """같은 예약·같은 상태 알림은 세션에서 한 번만 토스트로 띄운다."""
    seen = st.session_state.setdefault("notified", set())
    if key not in seen:
        seen.add(key)
        st.toast(notice["title"], icon=notice["icon"])
