"""예약 조회 및 운송 완료 후 평점 저장 (bookings / drivers / fare_rules).

- 조회는 반드시 예약번호 + 예약자 연락처가 모두 일치해야 결과를 돌려준다.
  (예약번호만으로 다른 고객 정보가 보이지 않도록, 불일치 이유도 구분하지 않고 None 반환)
- 평점 저장 외에는 예약 데이터를 변경하지 않는다.
- 모든 SQL은 파라미터 바인딩을 사용한다.
- conn을 인자로 받아 테스트에서 별도 연결(임시 테이블)을 주입할 수 있다.
"""

from __future__ import annotations

import hmac
import re

STATUS_LABELS = {
    "BOOKED": "예약 완료",
    "DEPARTED": "기사 출발",
    "IN_TRANSIT": "운송 중",
    "COMPLETED": "운송 완료",
    "CANCELLED": "예약 취소",
}
STATUS_FLOW = ["BOOKED", "DEPARTED", "IN_TRANSIT", "COMPLETED"]
RATING_MIN, RATING_MAX = 1, 5

_LOOKUP_SQL = """
    SELECT b.booking_id, b.customer_phone, b.origin_address, b.dest_address,
           b.scheduled_at, b.estimated_fare, b.status, b.status_updated_at,
           b.rating, b.created_at,
           d.driver_id, d.nickname AS driver_name, d.verification_status,
           fr.vehicle_type, d.fare_rule_id AS driver_fare_rule_id
    FROM bookings b
    LEFT JOIN drivers d ON d.driver_id = b.driver_id
    LEFT JOIN fare_rules fr ON fr.fare_rule_id = b.fare_rule_id      -- 운임 기준 차량
    WHERE b.booking_id = %s
"""


def normalize_phone(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def parse_booking_id(value) -> int | None:
    text = str(value or "").strip()
    if not re.fullmatch(r"\d{1,18}", text):
        return None
    return int(text)


def is_valid_phone(value) -> bool:
    return bool(re.fullmatch(r"0\d{8,10}", normalize_phone(value)))


def _phone_matches(stored, given) -> bool:
    a, b = normalize_phone(stored), normalize_phone(given)
    return bool(a) and hmac.compare_digest(a, b)


def find_booking(conn, booking_id: int, phone: str) -> dict | None:
    """예약번호 + 연락처가 모두 일치하면 예약 정보(dict), 아니면 None."""
    with conn.cursor() as cur:
        cur.execute(_LOOKUP_SQL, (booking_id,))
        row = cur.fetchone()
        if row:  # 배정 기사님 차량 (fare_rules를 한 쿼리에서 두 번 참조하지 않도록 따로 조회)
            cur.execute("SELECT vehicle_type FROM fare_rules WHERE fare_rule_id = %s", (row.pop("driver_fare_rule_id"),))
            found = cur.fetchone()
            row["driver_vehicle_type"] = found["vehicle_type"] if found else None
    conn.rollback()  # 읽기 전용 트랜잭션 종료
    if not row or not _phone_matches(row["customer_phone"], phone):
        return None
    row.pop("customer_phone")  # 화면에 연락처를 다시 노출하지 않음
    return row


# submit_rating 결과 코드
SAVED, INVALID_RATING, NOT_FOUND, NOT_COMPLETED, ALREADY_RATED = (
    "saved", "invalid_rating", "not_found", "not_completed", "already_rated",
)


def submit_rating(conn, booking_id: int, phone: str, rating) -> str:
    """운송 완료(COMPLETED)이고 아직 평가하지 않은 예약에만 평점을 저장한다."""
    if isinstance(rating, bool) or not isinstance(rating, int) or not RATING_MIN <= rating <= RATING_MAX:
        return INVALID_RATING
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT customer_phone, status, rating FROM bookings WHERE booking_id = %s FOR UPDATE",
                (booking_id,),
            )
            row = cur.fetchone()
            if not row or not _phone_matches(row["customer_phone"], phone):
                conn.rollback()
                return NOT_FOUND
            if row["status"] != "COMPLETED":
                conn.rollback()
                return NOT_COMPLETED
            if row["rating"] is not None:
                conn.rollback()
                return ALREADY_RATED
            cur.execute(
                "UPDATE bookings SET rating = %s "
                "WHERE booking_id = %s AND status = 'COMPLETED' AND rating IS NULL",
                (rating, booking_id),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return ALREADY_RATED
        conn.commit()
        return SAVED
    except Exception:
        conn.rollback()
        raise
