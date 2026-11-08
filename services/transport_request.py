"""운송 요청 입력값 정의·검증 및 페이지 간 전달 (st.session_state).

운송 요청은 st.session_state[REQUEST_KEY]에 아래 dict 형태로 저장된다.
기사 매칭·운임 계산 담당은 이 dict를 입력으로 사용하면 된다.

    {
        "origin_address": str, "dest_address": str,
        "origin_floor": int, "origin_has_elevator": bool,
        "dest_floor": int, "dest_has_elevator": bool,
        "item_s_count": int, "item_m_count": int, "item_l_count": int, "item_xl_count": int,
        "scheduled_at": datetime, "helper_option": str (HELPER_OPTIONS 키),
    }
키 이름은 bookings 테이블 컬럼명과 같게 맞췄다.
"""

from __future__ import annotations

from datetime import datetime

VEHICLE_TYPES = ("다마스", "라보", "1톤")  # 운송 차량 종류 고정
ITEM_SIZES = ("S", "M", "L", "XL")
HELPER_OPTIONS = {  # bookings.helper_option (VARCHAR(20), 기본값 'NONE')
    "NONE": "추가 인력 없음",
    "DRIVER_HELP": "기사님 운반 도움",
    "EXTRA_WORKER": "추가 인력 1명",
}
FLOOR_MIN, FLOOR_MAX = -5, 99
ITEM_MAX = 50

REQUEST_KEY = "transport_request"        # 운송 요청 입력값
SELECTED_DRIVER_KEY = "selected_driver"  # 매칭 화면에서 고른 기사 (매칭 담당이 채움)


def validate_request(req: dict, now: datetime | None = None) -> list[str]:
    """오류 메시지 목록 (비어 있으면 통과)."""
    errors = []
    origin = (req.get("origin_address") or "").strip()
    dest = (req.get("dest_address") or "").strip()
    if not origin:
        errors.append("출발지를 입력해 주세요.")
    if not dest:
        errors.append("도착지를 입력해 주세요.")
    if origin and dest and origin == dest:
        errors.append("출발지와 도착지가 같습니다.")
    for key, label in (("origin_floor", "출발지"), ("dest_floor", "도착지")):
        floor = req.get(key)
        if not isinstance(floor, int) or not FLOOR_MIN <= floor <= FLOOR_MAX or floor == 0:
            errors.append(f"{label} 층수를 확인해 주세요 (지하는 -1, -2 …, 0층 없음).")
    counts = [req.get(f"item_{s.lower()}_count", 0) for s in ITEM_SIZES]
    if any(not isinstance(c, int) or c < 0 or c > ITEM_MAX for c in counts):
        errors.append(f"물품 개수는 크기별 0~{ITEM_MAX}개로 입력해 주세요.")
    elif sum(counts) == 0:
        errors.append("물품을 1개 이상 입력해 주세요.")
    scheduled = req.get("scheduled_at")
    if not isinstance(scheduled, datetime):
        errors.append("희망 운송 날짜와 시간을 선택해 주세요.")
    elif scheduled <= (now or datetime.now()):
        errors.append("희망 운송 일시는 현재 이후로 선택해 주세요.")
    if req.get("helper_option") not in HELPER_OPTIONS:
        errors.append("추가 인력 옵션을 선택해 주세요.")
    return errors
