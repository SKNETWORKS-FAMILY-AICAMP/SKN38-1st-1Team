"""예약 저장 — 6_Booking.py의 [예약 확정]에서 create_booking(request, driver, customer) 호출

- 저장 시점: 예약 확정 때 한 번만 (견적만 보고 나간 사용자는 저장하지 않음)
- 저장 내용: 운송 입력값 + 견적(차량·거리·운임) + 매칭 기사 + 고객 정보 → bookings 1행
- 예약번호(booking_id): 날짜 6자리 + 그날 순번 4자리 (예: 2611090001) → 예약 조회 화면에서 숫자로 조회
- 같은 기사가 같은 날 이미 예약돼 있으면 저장하지 않고 BookingError
"""
from __future__ import annotations

from datetime import date

from services.booking_lookup import normalize_phone
from services.db import get_connection
from services.settlement import calc_settlement          # 수수료 계산

DONE_STATUS = ("CANCELLED", "COMPLETED")          # 끝난 예약은 기사 일정에서 제외
# 주소의 시도 표기 → DB(regions) 표기 (팀 적재 스크립트는 약칭 사용, 광주·전남은 2026-07 통합)
SIDO_TO_DB = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북", "경상북도": "경북",
    "경상남도": "경남", "제주특별자치도": "제주", "광주": "전남광주", "광주광역시": "전남광주",
    "전남": "전남광주", "전라남도": "전남광주", "전남광주통합특별시": "전남광주",
}


class BookingError(RuntimeError):
    """예약할 수 없음 (기사 일정 겹침, 운임 정보 없음 등) — 화면에 메시지 그대로 표시"""


# ── 1. 주소 → region_id (주소 글자에서 시도·시군구를 읽음 → 시군구 → 시도 → 전국 순서로 찾기)
def _split_region(address: str) -> tuple[str, str, str]:
    """'서울 용산구 한강대로 405' → ('서울', '용산구', '서울') / '경기 수원시 영통구 ...' → ('경기', '수원시 영통구', '경기')"""
    t = (address or "").split()
    if not t:
        return "", "", ""
    sido = SIDO_TO_DB.get(t[0], t[0])
    if len(t) > 2 and t[1].endswith("시") and t[2].endswith("구"):      # 일반구가 있는 시
        return sido, f"{t[1]} {t[2]}", t[0]
    return sido, (t[1] if len(t) > 1 else ""), t[0]


def _region_id(cur, address: str) -> int:
    sido, sigungu, raw_sido = _split_region(address)
    for sql, params in (
        ("SELECT region_id FROM regions WHERE sido_name=%s AND sigungu_name=%s", (sido, sigungu)),
        ("SELECT region_id FROM regions WHERE sido_name=%s AND sigungu_name=%s", (sido, raw_sido)),  # 세종특별자치시
        ("SELECT region_id FROM regions WHERE sido_name=%s AND sigungu_name IS NULL", (sido,)),
        ("SELECT region_id FROM regions WHERE sido_name='전국'", ()),
    ):
        cur.execute(sql + " ORDER BY region_id LIMIT 1", params)
        row = cur.fetchone()
        if row:
            return row["region_id"]
    raise BookingError("지역 정보를 찾을 수 없습니다. 관리자에게 문의해 주세요.")


# ── 2. 예약번호: 오늘 날짜(YYMMDD) × 10000 + 순번 → 2611090001, 2611090002 ...
def _next_booking_id(cur) -> int:
    base = int(f"{date.today():%y%m%d}") * 10000
    cur.execute("SELECT MAX(booking_id) AS m FROM bookings WHERE booking_id BETWEEN %s AND %s FOR UPDATE",
                (base, base + 9999))
    last = cur.fetchone()["m"]
    return (last or base) + 1


# ── 3. 예약 저장 (페이지에서 호출하는 함수)
def create_booking(request: dict, driver: dict, customer: dict) -> int:
    quote = request.get("quote")                                       # 2페이지에서 기사 선택 시 함께 저장
    if not quote or quote.get("estimated_fare") is None:
        raise BookingError("운임 정보가 없습니다. 매칭 결과 화면에서 다시 기사님을 선택해 주세요.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 3-1. 기사 행 잠금 → 같은 날 다른 예약이 있으면 중단 (동시에 두 명이 예약하는 경우 방지)
            cur.execute("SELECT driver_id FROM drivers WHERE driver_id=%s AND is_active=TRUE FOR UPDATE",
                        (driver["driver_id"],))
            if not cur.fetchone():
                raise BookingError("선택한 기사님을 지금은 예약할 수 없습니다.")
            cur.execute(f"""SELECT 1 FROM bookings WHERE driver_id=%s AND DATE(scheduled_at)=DATE(%s)
                            AND status NOT IN ({", ".join(["%s"] * len(DONE_STATUS))}) LIMIT 1""",
                        (driver["driver_id"], request["scheduled_at"], *DONE_STATUS))
            if cur.fetchone():
                raise BookingError("방금 다른 예약이 잡힌 기사님입니다. 매칭 결과에서 다른 기사님을 선택해 주세요.")

            # 3-2. 견적 차량 → fare_rule_id (예약 조회 화면의 '차량 종류'가 여기서 나옴)
            cur.execute("SELECT fare_rule_id FROM fare_rules WHERE vehicle_type=%s AND is_active=TRUE "
                        "ORDER BY fare_rule_id LIMIT 1", (quote.get("vehicle_type") or driver["vehicle_type"],))
            rule = cur.fetchone()
            if not rule:
                raise BookingError("차량 요금 규칙을 찾을 수 없습니다.")

            booking_id = _next_booking_id(cur)
            money = calc_settlement(quote["estimated_fare"])   # 운임 → 결제액·수수료·기사 정산액

            # 3-3. bookings 1행 저장
            row = {
                "booking_id": booking_id,
                "customer_name": customer["name"],
                "customer_phone": normalize_phone(customer["phone"]),     # 숫자만 저장 (조회 화면과 같은 규칙)
                "origin_address": request["origin_address"], "origin_lat": request.get("pickup_lat"), "origin_lng": request.get("pickup_lng"),
                "origin_floor": request["origin_floor"], "origin_has_elevator": request["origin_has_elevator"],
                "dest_address": request["dest_address"], "dest_lat": request.get("dropoff_lat"), "dest_lng": request.get("dropoff_lng"),
                "dest_floor": request["dest_floor"], "dest_has_elevator": request["dest_has_elevator"],
                "item_s_count": request.get("item_s_count", 0), "item_m_count": request.get("item_m_count", 0),
                "item_l_count": request.get("item_l_count", 0), "item_xl_count": request.get("item_xl_count", 0),
                "helper_option": request.get("helper_option", "NONE"),
                "distance_km": quote.get("distance_km"), "estimated_minutes": quote.get("estimated_minutes"),
                "scheduled_at": request["scheduled_at"],
                "estimated_fare": money["customer_total"],          # 고객 결제액 (운임 + 이용료 5%)
                "commission_amount": money["platform_revenue"],     # 이용료 + 기사 수수료
                "driver_payout": money["driver_payout"],            # 기사 정산액 (운임 − 18%)
                "origin_region_id": _region_id(cur, request["origin_address"]),
                "dest_region_id": _region_id(cur, request["dest_address"]),
                "fare_rule_id": rule["fare_rule_id"], "driver_id": driver["driver_id"],
                "status": "BOOKED",
            }
            cols = ", ".join(row)
            cur.execute(f"INSERT INTO bookings ({cols}, status_updated_at) VALUES ({', '.join(['%s'] * len(row))}, NOW())",
                        list(row.values()))
        conn.commit()
        return booking_id
    except Exception:
        conn.rollback()                                                # 실패하면 아무것도 저장 안 됨
        raise
    finally:
        conn.close()