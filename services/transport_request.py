"""운송 요청 입력값 정의·검증 및 페이지 간 전달 (st.session_state).

운송 요청은 st.session_state[REQUEST_KEY]에 아래 dict 형태로 저장된다.
기사 매칭·운임 계산 담당은 이 dict를 입력으로 사용하면 된다.

    {
        # 카카오 주소 검색에서 사용자가 선택한 위치 (좌표는 카카오 응답 x=경도, y=위도를 변환한 값)
        "pickup_address": str, "pickup_lat": float, "pickup_lng": float,
        "dropoff_address": str, "dropoff_lat": float, "dropoff_lng": float,
        "pickup_detail_address": str, "dropoff_detail_address": str,   # 동·호수 등 (선택, 기본 주소와 분리)

        # 기존 키 (운임 계산 fare.estimate_request, bookings 컬럼명과 호환) — 상세주소를 붙이지 않은 기본 주소
        "origin_address": str, "dest_address": str,
        "origin_floor": int, "origin_has_elevator": bool,
        "dest_floor": int, "dest_has_elevator": bool,
        "item_s_count": int, "item_m_count": int, "item_l_count": int, "item_xl_count": int,
        "scheduled_at": datetime, "helper_option": str (HELPER_OPTIONS 키),
    }
bookings 테이블의 origin_lat/origin_lng/dest_lat/dest_lng에는 pickup_*/dropoff_* 좌표를 저장하면 된다.
"""

from __future__ import annotations

from datetime import datetime

from services.kakao_local import is_valid_location

VEHICLE_TYPES = ("다마스", "라보", "1톤")  # 운송 차량 종류 고정
ITEM_SIZES = ("S", "M", "L", "XL")
HELPER_OPTIONS = {  # bookings.helper_option (VARCHAR(20), 기본값 'NONE')
    "NONE": "추가 인력 없음",
    "DRIVER_HELP": "기사님 운반 도움",
    "EXTRA_WORKER": "추가 인력 1명",
}
FLOOR_MIN, FLOOR_MAX = -2, 6   # 운임표 계단 요금 범위 (지하 2층 ~ 5층) + 6층 = '6층 이상'(별도 협의)


def floor_label(floor: int) -> str:
    """층수 표시 (-2 → 지하 2층, 6 → 6층 이상). 입력·매칭·예약 화면 공통."""
    if floor >= FLOOR_MAX:
        return f"{FLOOR_MAX}층 이상"
    return f"지하 {-floor}층" if floor < 0 else f"{floor}층"
ITEM_MAX = 50

REQUEST_KEY = "transport_request"        # 운송 요청 입력값
SELECTED_DRIVER_KEY = "selected_driver"  # 매칭 화면에서 고른 기사 (매칭 담당이 채움)


def location_of(req: dict, side: str) -> dict:
    """request에서 pickup/dropoff 위치만 꺼낸다."""
    return {"address": req.get(f"{side}_address"), "lat": req.get(f"{side}_lat"), "lng": req.get(f"{side}_lng")}


def same_place(a: dict, b: dict) -> bool:
    """같은 주소이거나 좌표가 사실상 같으면(약 10m 이내) 같은 위치로 본다."""
    if str(a["address"]).strip() == str(b["address"]).strip():
        return True
    return abs(a["lat"] - b["lat"]) < 1e-4 and abs(a["lng"] - b["lng"]) < 1e-4


def validate_request(req: dict, now: datetime | None = None) -> list[str]:
    """오류 메시지 목록 (비어 있으면 통과)."""
    errors = []
    pickup = location_of(req, "pickup")
    dropoff = location_of(req, "dropoff")
    if not is_valid_location(pickup):
        errors.append("출발지를 주소 검색으로 찾아 선택해 주세요.")
    if not is_valid_location(dropoff):
        errors.append("도착지를 주소 검색으로 찾아 선택해 주세요.")
    if is_valid_location(pickup) and is_valid_location(dropoff) and same_place(pickup, dropoff):
        errors.append("출발지와 도착지가 같은 위치입니다. 주소를 다시 확인해 주세요.")
    for key, label in (("origin_floor", "출발지"), ("dest_floor", "도착지")):
        floor = req.get(key)
        if not isinstance(floor, int) or not FLOOR_MIN <= floor <= FLOOR_MAX or floor == 0:
            errors.append(f"{label} 층수를 확인해 주세요 (지하 2층 ~ 6층 이상 중에서 선택).")
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
