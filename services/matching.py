"""출발지 기준 기사 추천 — 2_Driver_Matching.py에서 recommend_drivers(request, estimate, sort_by) 호출

- 조회만 함 (DB 저장 X): 견적만 보고 나가는 사용자도 있으므로, 저장은 예약 확정(6_Booking) 때만
- 별점: drivers.avg_rating(평균), rating_count(개수) → 별점 입력 시 booking_lookup에서 갱신
- 반환 예: [{"driver_id": 1, "nickname": "김**", "vehicle_type": "라보",
            "rating": 4.6, "rating_count": 12, "distance_km": 1.2}, ...]
라이브러리: math(거리 계산)
"""
import math

from services.db import get_connection
from services.kakao_local import search_address       # 팀 카카오 주소 검색
from services.transport_request import VEHICLE_TYPES  # 작은 차 → 큰 차 순서 (다마스, 라보, 1톤)

# ── 설정: 팀 DB 테이블·컬럼 이름에 맞게 수정 ─────────────────────────
DRIVER_TABLE = "drivers"        # 기사: driver_id, nickname, base_lat, base_lng, is_active, fare_rule_id, avg_rating, rating_count
FARE_TABLE = "fare_rules"       # 차종: fare_rule_id → vehicle_type
VEHICLE_COL = "vehicle_type"    # fare_rules 안의 차종 컬럼 이름
BOOKING_TABLE = "bookings"      # 예약: driver_id, scheduled_at, status
DONE_STATUS = ("CANCELLED", "COMPLETED")  # 이 상태의 예약은 기사 일정에서 제외
TOP_N = 5                       # 추천 인원
NEAR_POOL = 15                  # 별점순일 때 가까운 몇 명 안에서 고를지 (너무 먼 기사 제외)
SEARCH_DEG = 0.3                # 출발지 주변 검색 범위 (위경도 ±0.3도 ≈ 30km)
SORT_OPTIONS = {"distance": "가까운 순", "rating": "별점 높은 순"}


# ── 1. 필요한 차량 결정 ──────────────────────────────────────────────
def required_vehicle(request: dict, estimate: dict | None = None) -> str:
    """fare.estimate 결과가 있으면 그 추천 차량을 쓰고, 없으면 짐 개수로 직접 판단"""
    if estimate and estimate.get("vehicle", {}).get("vehicle_type") in VEHICLE_TYPES:
        return estimate["vehicle"]["vehicle_type"]
    l, xl = request.get("item_l_count", 0), request.get("item_xl_count", 0)
    idx = 2 if xl >= 1 else 1 if l >= 2 else 0                   # XL → 1톤 / L 2개↑ → 라보 / 그 외 다마스
    return VEHICLE_TYPES[min(idx, len(VEHICLE_TYPES) - 1)]


# ── 2. 좌표: 1페이지가 넘겨준 좌표 사용, 없을 때만 팀 카카오 검색(kakao_local) 사용
def geocode(address: str) -> tuple[float, float] | None:          # 주소 → (위도, 경도)
    results = search_address(address)
    return (results[0]["lat"], results[0]["lng"]) if results else None


def haversine_km(lat1, lng1, lat2, lng2) -> float:                 # 두 좌표 직선거리(km)
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


# ── 3. 후보 기사 조회 (차량 조건 + 출발지 주변 + 같은 날 일정 없음) ─────
def _fetch_candidates(lat, lng, vehicle_types, scheduled_at) -> list[dict]:
    placeholders = ", ".join(["%s"] * len(vehicle_types))
    sql = f"""
        SELECT d.driver_id, d.nickname, f.{VEHICLE_COL} AS vehicle_type, d.base_lat, d.base_lng,
               d.avg_rating, d.rating_count                              -- 기사 테이블의 평균 별점
        FROM {DRIVER_TABLE} d
        JOIN {FARE_TABLE} f ON f.fare_rule_id = d.fare_rule_id          -- 기사 차종은 운임 규칙에서
        WHERE d.is_active = 1
          AND f.{VEHICLE_COL} IN ({placeholders})                        -- 필요 차량 이상만
          AND d.base_lat BETWEEN %s AND %s AND d.base_lng BETWEEN %s AND %s       -- 출발지 주변만 (속도용)
          AND NOT EXISTS (                                              -- 같은 날 진행 중인 예약 있는 기사 제외
                SELECT 1 FROM {BOOKING_TABLE} x
                WHERE x.driver_id = d.driver_id
                  AND DATE(x.scheduled_at) = DATE(%s)
                  AND x.status NOT IN ({", ".join(["%s"] * len(DONE_STATUS))}))
    """
    params = [*vehicle_types, lat - SEARCH_DEG, lat + SEARCH_DEG, lng - SEARCH_DEG, lng + SEARCH_DEG,
              scheduled_at, *DONE_STATUS]
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# ── 4. 추천 (페이지·자동 배정에서 호출하는 함수) ─────────────────────
def recommend_drivers(request: dict, estimate: dict | None = None, sort_by: str = "distance",
                      limit: int = TOP_N) -> list[dict]:
    if request.get("pickup_lat") is not None:                       # 1페이지에서 이미 찾은 좌표
        origin = (request["pickup_lat"], request["pickup_lng"])
    else:
        origin = geocode(request["origin_address"])
    if origin is None:
        raise ValueError("출발지 주소를 찾을 수 없습니다. 도로명 주소로 다시 입력해 주세요.")

    need = required_vehicle(request, estimate)
    usable = VEHICLE_TYPES[VEHICLE_TYPES.index(need):]              # 필요 차량과 그보다 큰 차량
    rows = _fetch_candidates(*origin, usable, request["scheduled_at"])

    drivers = [{
        "driver_id": r["driver_id"],
        "nickname": r["nickname"],
        "vehicle_type": r["vehicle_type"],
        "rating": float(r["avg_rating"]) if r["avg_rating"] is not None else None,   # None = 신규 기사
        "rating_count": r["rating_count"] or 0,
        "distance_km": round(haversine_km(*origin, float(r["base_lat"]), float(r["base_lng"])), 1),
    } for r in rows]

    # 기본: 가까운 순 → 같은 거리면 작은 차 먼저 (운임 부담 적게)
    drivers.sort(key=lambda d: (d["distance_km"], VEHICLE_TYPES.index(d["vehicle_type"])))
    if sort_by == "rating":
        # 가까운 NEAR_POOL명 안에서 별점 높은 순 → 별점 개수 많은 순 → 가까운 순 (신규 기사는 맨 뒤)
        drivers = sorted(drivers[:NEAR_POOL],
                         key=lambda d: (d["rating"] is None, -(d["rating"] or 0), -d["rating_count"], d["distance_km"]))
    return drivers[:limit]


# ── 5. 기사 프로필 이미지 (DiceBear 캐릭터, driver_id로 고정 → 같은 기사는 항상 같은 얼굴)
def avatar_html(driver: dict, size: int = 96) -> str:
    url = f"https://api.dicebear.com/9.x/avataaars/svg?seed={driver['driver_id']}"
    return f'<img src="{url}" width="{size}" height="{size}" style="border-radius:50%" alt="{driver["nickname"]} 기사님">'