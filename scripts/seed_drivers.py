"""시연용 데이터 준비 (한 번에): 차종(fare_rules) → 시연 출처(data_sources) → 가상 기사(drivers)
- 먼저 필요: regions · registration_stats (팀 update_registration_db.py로 적재)
- 기사 수: 시군구별 영업용 화물차 등록대수 비율 / 차종: 가정 비율 / 좌표: 시군구 중심 ±약 2km (실제 주소 아님)
- 여러 번 실행해도 중복 없음
실행: python -m scripts.seed_drivers
"""
import os
import random
from datetime import date

import pandas as pd

from services.db import get_connection
from services.fare_table import FARE_RULES, VEHICLE_ORDER   # 팀 운임표 재사용 (숫자 중복 X)
from services.matching import geocode                        # 팀 매칭과 같은 카카오 좌표 함수
from services.truck_stats import _load_queries               # 팀 지도와 같은 시군구 쿼리

# ── 설정 ─────────────────────────────────────────────────────────────
MAX_LOAD_KG = {"다마스": 450, "라보": 550, "1톤": 1000}      # fare_table에 적재량(max_payload)이 비어 있어 공칭값
SOURCE_CODE = "DEMO_DRIVERS"
RATIO, MIN_N, MAX_N = 0.005, 1, 25                          # 등록대수의 0.5% (지역별 1~25명)
VEHICLE_RATIO = [0.4, 0.3, 0.3]                             # VEHICLE_ORDER 순서 (다마스:라보:1톤) 가정 비율
CACHE = "data/processed/sigungu_coordinates.csv"                 # 시군구 좌표 캐시 (카카오 재호출 방지)
SIDO_CENTER = "data/processed/sido_bubble_points.csv"
GWANGJU_GU = {"광산구", "남구", "동구", "북구", "서구"}
SURNAMES = list("김이박최정강조윤장임한오서신권황안송류홍")
random.seed(42)                                             # 실행할 때마다 같은 결과


# ── 1. 차종: fare_table.py 값 → fare_rules (없으면 추가, 있으면 갱신)
def ensure_fare_rules(cur) -> dict:
    first, last = FARE_RULES[0], FARE_RULES[-1]
    for fid, vt in enumerate(VEHICLE_ORDER, start=1):
        base = first["fares"][vt]
        per_km = round((last["fares"][vt] - base) / (last["max"] - first["max"]))   # km당 참고값
        vals = (vt, MAX_LOAD_KG[vt], base, first["max"], per_km, date.today(), fid)
        cur.execute("SELECT 1 FROM fare_rules WHERE fare_rule_id = %s", (fid,))
        if cur.fetchone():
            cur.execute("""UPDATE fare_rules SET vehicle_type=%s, max_load_kg=%s, base_fare=%s, base_distance_km=%s,
                           per_km_fare=%s, is_active=TRUE, effective_from=%s WHERE fare_rule_id=%s""", vals)
        else:
            cur.execute("""INSERT INTO fare_rules (vehicle_type, max_load_kg, base_fare, base_distance_km,
                           per_km_fare, is_active, effective_from, fare_rule_id)
                           VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s)""", vals)
    return {vt: fid for fid, vt in enumerate(VEHICLE_ORDER, start=1)}


# ── 2. 시연 출처 1건 (없을 때만 추가) → source_id
def ensure_demo_source(cur) -> int:
    cur.execute("SELECT source_id FROM data_sources WHERE source_code = %s", (SOURCE_CODE,))
    row = cur.fetchone()
    if row:
        return row["source_id"]
    cur.execute("SELECT COALESCE(MAX(source_id), 0) + 1 AS n FROM data_sources")
    sid = cur.fetchone()["n"]
    cur.execute("""INSERT INTO data_sources (source_id, source_code, dataset_name, provider, portal_url, file_name,
                   base_month, retrieved_at, collection_method, coverage_note, region_id)
                   VALUES (%s, %s, '시연용 가상 기사 데이터', '짐니 팀 자체 생성', '-', 'scripts/seed_drivers.py',
                           NULL, CURDATE(), 'GENERATED', '등록대수 비율로 생성한 가상 기사, 실제 사업자·주소 아님',
                           (SELECT region_id FROM regions WHERE sido_name = '전국'      -- 팀 규칙: 전국 단위 출처는 '전국' 지역
                            ORDER BY region_id LIMIT 1))""", (sid, SOURCE_CODE))
    return sid


# ── 3. 시군구 중심 좌표 (캐시 → 카카오 → 시도 중심 순서)
def region_center(r: dict, cache: dict, sido: pd.DataFrame):
    key = r["region_id"]
    if key not in cache:
        s, g = r["sido_name"], r["sigungu_name"]
        if s == "전남광주":                                   # 통합 시도명은 카카오가 모름
            s = "광주" if g in GWANGJU_GU else "전남"
        try:
            cache[key] = geocode(s if s == g else f"{s} {g}")
        except Exception:
            cache[key] = None
        if cache[key] is None:                                # 실패 → 시도 중심
            row = sido[(sido["sido_name"] == r["sido_name"]) | (sido["sgis_sido_nm"] == r["sido_name"])]
            cache[key] = (row["lat"].iloc[0], row["lon"].iloc[0]) if len(row) else None
    return cache[key]


def main():
    cache = {}
    if os.path.exists(CACHE):
        cache = {k: (la, ln) for k, la, ln in pd.read_csv(CACHE).itertuples(index=False)}
    sido = pd.read_csv(SIDO_CENTER)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(_load_queries()[2])                       # 팀 쿼리 3번: 시군구별 등록대수
        regions = [r for r in cur.fetchall() if r["truck_count"]]
        if not regions:
            raise SystemExit("regions·registration_stats가 비어 있습니다. update_registration_db.py를 먼저 실행하세요.")

        rules = ensure_fare_rules(cur)
        source_id = ensure_demo_source(cur)

        # 4. 예전 시연 기사 삭제 (예약에 쓰인 기사는 남김) → 새 번호부터 생성
        cur.execute("""DELETE FROM drivers WHERE source_id = %s
                       AND driver_id NOT IN (SELECT driver_id FROM bookings)""", (source_id,))
        cur.execute("SELECT COALESCE(MAX(driver_id), 0) AS m FROM drivers")
        next_id = cur.fetchone()["m"] + 1

        rows = []
        for r in regions:
            center = region_center(r, cache, sido)
            if center is None:
                continue
            for _ in range(min(max(round(r["truck_count"] * RATIO), MIN_N), MAX_N)):
                vt = random.choices(VEHICLE_ORDER, weights=VEHICLE_RATIO)[0]
                rows.append((next_id, f"{random.choice(SURNAMES)}**",
                             round(center[0] + random.uniform(-0.02, 0.02), 6),
                             round(center[1] + random.uniform(-0.02, 0.02), 6),
                             source_id, r["region_id"], rules[vt]))
                next_id += 1

        cur.executemany("""INSERT INTO drivers (driver_id, nickname, base_lat, base_lng, source_id, region_id, fare_rule_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""", rows)
        conn.commit()

    pd.DataFrame([(k, *v) for k, v in cache.items() if v], columns=["region_id", "lat", "lng"]).to_csv(CACHE, index=False)
    print(f"차종 {len(rules)}종, 지역 {len(regions)}곳, 가상 기사 {len(rows)}명 준비 완료")


if __name__ == "__main__":
    main()