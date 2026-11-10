"""예약 확정 시 기사 자동 배정 — 매칭(matching.recommend_drivers)·예약 저장(booking.create_booking) 재사용

- 후보: recommend_drivers(견적 차량과 같은 차종 우선 · 출발지 주변 · 같은 날 일정 없음 · 가까운 순)를 예약 확정 시점에 다시 조회
- 매칭 결과 화면에서 고른 기사님이 아직 후보에 있으면 그 기사님을 먼저 시도
- create_booking은 기사 행을 잠그고 같은 날 일정을 다시 확인한 뒤 1건만 저장(실패 시 롤백)
  → 그 사이 일정이 생긴 기사면 다음 후보로 넘어감. 모든 후보가 안 되면 아무것도 저장하지 않고 실패
- 후보가 없으면 임의 기사를 만들지 않고 실패로 알림
- 같은 연락처·일시·출발지·도착지의 진행 중 예약이 이미 있으면 새로 저장하지 않음 (중복 예약 방지)
"""

from __future__ import annotations

from services import matching
from services.booking import BookingError, create_booking
from services.booking_lookup import normalize_phone
from services.db import get_connection

# create_booking이 '이 기사는 지금 안 됨'으로 거절하는 경우 → 다음 후보로 시도
_RETRY_MESSAGES = ("방금 다른 예약이 잡힌 기사님", "선택한 기사님을 지금은 예약할 수 없습니다")


class AssignmentError(RuntimeError):
    """기사 배정·예약 저장 실패 (화면에 메시지 그대로 표시, DB에는 아무것도 저장되지 않음)"""


def candidate_drivers(request: dict, quote: dict, preferred: dict | None = None) -> list[dict]:
    """견적 차량 기준 후보 기사 (선호 기사가 후보에 있으면 맨 앞)."""
    drivers = matching.recommend_drivers(request, {"vehicle": {"vehicle_type": quote.get("vehicle_type")}},
                                         limit=matching.NEAR_POOL)   # 별점순으로 고른 기사도 후보에 들어오게 15명
    if preferred:
        drivers.sort(key=lambda d: d["driver_id"] != preferred.get("driver_id"))   # 안정 정렬: 나머지 순서 유지
    return drivers


def find_duplicate(request: dict, phone: str) -> int | None:
    """같은 연락처·일시·경로로 진행 중인 예약이 있으면 그 예약번호."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT booking_id FROM bookings WHERE customer_phone=%s AND scheduled_at=%s AND origin_address=%s "
            "AND dest_address=%s AND status <> 'CANCELLED' ORDER BY booking_id LIMIT 1",
            (normalize_phone(phone), request["scheduled_at"], request["origin_address"], request["dest_address"]),
        )
        row = cur.fetchone()
    return row["booking_id"] if row else None


def confirm_booking(request: dict, quote: dict, customer: dict, preferred: dict | None = None,
                    agreement: dict | None = None) -> dict:
    """예약 저장 + 기사 배정. 성공 시 {"booking_id", "driver", "tried"} (driver는 실제 저장된 기사).

    agreement: agreement.agreement_record() 결과 → create_booking이 bookings 동의 컬럼에 함께 저장
    """
    if find_duplicate(request, customer["phone"]) is not None:
        raise AssignmentError("같은 연락처로 같은 일시·경로의 예약이 이미 있어요. 예약 조회에서 확인해 주세요.")
    request = {**request, "quote": quote, "agreement": agreement}          # create_booking은 request["quote"]·["agreement"] 사용
    candidates = candidate_drivers(request, quote, preferred)
    if not candidates:
        raise AssignmentError("조건에 맞는 기사님이 없어 예약을 저장하지 않았어요. 날짜나 출발지를 바꿔 다시 시도해 주세요.")
    for tried, driver in enumerate(candidates, start=1):
        try:
            booking_id = create_booking(request, driver, customer)
        except BookingError as e:
            if any(m in str(e) for m in _RETRY_MESSAGES):
                continue
            raise AssignmentError(str(e)) from e
        return {"booking_id": booking_id, "driver": driver, "tried": tried}
    raise AssignmentError("후보 기사님 모두 같은 날 일정이 생겨 예약을 저장하지 않았어요. 다른 날짜로 다시 시도해 주세요.")
