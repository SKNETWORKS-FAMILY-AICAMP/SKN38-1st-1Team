"""시연용 가상 기사 47,000명 생성 → MySQL drivers (통계누리 엑셀의 시군구별 영업용 화물차 등록대수 비율로 배분)

기준
    - 원본: data/processed/화물차_시군구별_등록현황_202609.xlsx 마지막 열 '계' (services/driver_sim.py가 소계·총계 제외·검증)
    - 전국 47,000명(등록대수 472,852대의 약 10%)을 시군구 263곳에 등록대수 비율대로 배분 (최대 나머지 방식 → 합계가 정확히 47,000)
    - 차종: 다마스 40% · 라보 30% · 1톤 30% (전국 18,800 · 14,100 · 14,100명, 각 지역도 이 순서로 섞어 배분)
    - 좌표: 그 시군구 안의 실제 장소 좌표(data/processed/driver_places.csv, scripts/collect_driver_places.py가 카카오로 수집)를
            기사마다 하나씩 배정 (무작위 이동 없음 → 점이 시군구 밖·바다로 나가지 않음). 장소가 인원보다 적으면 같은 장소를 함께 씀.
            장소 파일이 없는 시군구만 예전처럼 시군구 중심 ± 약 2km
    - 출처: data_sources 'DEMO_DRIVERS_XLSX' 1행 (짐니 팀 자체 생성)
    - 별점: seed_drivers.py와 같은 규칙 (평균 3.5~5.0 · 개수 3~30건, 10%는 신규 기사) → drivers.avg_rating · rating_count
            별점 칸이 없으면 먼저 추가 (seed_drivers.ensure_rating_columns, 표 구조 변경이라 --dry-run이어도 적용됨)

기존 가상 기사(seed_drivers.py, 출처 DEMO_DRIVERS) 정리
    - 예약에 쓰이지 않은 기사는 삭제, 예약에 쓰인 기사는 is_active=0(배정 불가)로 남겨 예약 기록 보존
    - 같은 출처(DEMO_DRIVERS_XLSX)의 이전 생성분도 같은 규칙으로 정리 → 여러 번 실행해도 활성 기사는 47,000명
    - 한 트랜잭션: 검증(합계 47,000, 차종 18,800/14,100/14,100)에 실패하면 전부 롤백

실행 (프로젝트 루트)
    python -m scripts.seed_drivers_excel --dry-run   배분 결과만 확인 (DB 쓰기 없음)
    python -m scripts.seed_drivers_excel             DB 반영
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from collections import Counter

import pandas as pd

from scripts.seed_drivers import (CACHE, COUNT_MAX, COUNT_MIN, NEW_DRIVER_RATIO, RATING_MAX, RATING_MIN,  # 예준님 규칙 재사용
                                  RATING_MODE, SIDO_CENTER, SURNAMES, ensure_rating_columns, region_center)
from services.db import get_connection
from services.driver_sim import EXCEL_PATH, load_driver_simulation

TOTAL_DRIVERS = 47_000
VEHICLE_PATTERN = ["다마스", "라보", "1톤", "다마스", "라보", "1톤", "다마스", "라보", "1톤", "다마스"]  # 10명당 4:3:3
SOURCE_CODE = "DEMO_DRIVERS_XLSX"
OLD_SOURCE_CODES = ("DEMO_DRIVERS", SOURCE_CODE)
JITTER = 0.02                       # 장소 파일이 없는 시군구만: 시군구 중심에서 ±0.02도 (약 2km)
PLACES = os.path.join("data", "processed", "driver_places.csv")
SEED = 4700
DATASET_NAME = "시연용 가상 기사 데이터 (등록대수 비율 47,000명)"
COVERAGE_NOTE = ("통계누리 시군구별 영업용 화물차 등록대수(2026-09)의 약 10% 비율로 47,000명 배분, "
                 "차종 다마스40·라보30·1톤30 가정, 좌표는 카카오 장소 좌표. 실제 사업자·주소 아님")


def allocate(sigungu: pd.DataFrame, total: int = TOTAL_DRIVERS) -> pd.DataFrame:
    """등록대수 비율로 total명 배분 (최대 나머지 방식: 내림 후 소수점이 큰 지역부터 1명씩)."""
    df = sigungu.copy()
    quota = df["truck_count"] / df["truck_count"].sum() * total
    df["drivers"] = quota.astype(int)
    rest = total - int(df["drivers"].sum())
    order = (quota - df["drivers"]).sort_values(ascending=False, kind="stable").index[:rest]
    df.loc[order, "drivers"] += 1
    return df


def demo_rating(rnd: random.Random) -> tuple:
    """시연용 (평균 별점, 별점 개수) — seed_drivers.demo_rating과 같은 규칙, 같은 결과가 나오게 rnd 사용."""
    if rnd.random() < NEW_DRIVER_RATIO:
        return None, 0
    return round(rnd.triangular(RATING_MIN, RATING_MAX, RATING_MODE), 2), rnd.randint(COUNT_MIN, COUNT_MAX)


def build_rows(alloc: pd.DataFrame, region_ids: dict, fare_rule_ids: dict, source_id: int, start_id: int) -> list[tuple]:
    rnd = random.Random(SEED)
    cache = {}
    if os.path.exists(CACHE):
        cache = {k: (la, ln) for k, la, ln in pd.read_csv(CACHE).itertuples(index=False)}
    sido_points = pd.read_csv(SIDO_CENTER)
    places = {}
    if os.path.exists(PLACES):
        for rid, grp in pd.read_csv(PLACES).groupby("region_id"):
            places[int(rid)] = list(zip(grp["lat"], grp["lng"]))
    rows, cursor, next_id = [], 0, start_id
    fallback = []
    for r in alloc[alloc["drivers"] > 0].itertuples(index=False):
        region_id = region_ids[(r.sido_name, r.sigungu_name)]
        spots = list(places.get(region_id, []))
        rnd.shuffle(spots)
        center = None
        if not spots:
            fallback.append(f"{r.sido_name} {r.sigungu_name}")
            center = region_center({"region_id": region_id, "sido_name": r.sido_name, "sigungu_name": r.sigungu_name},
                                   cache, sido_points)
            if center is None:
                raise SystemExit(f"좌표를 찾지 못했습니다: {r.sido_name} {r.sigungu_name}")
        for i in range(int(r.drivers)):
            vehicle = VEHICLE_PATTERN[cursor % len(VEHICLE_PATTERN)]   # 전국 순서대로 4:3:3 → 합계 정확
            cursor += 1
            if spots:                                                   # 실제 장소 좌표 그대로 (모자라면 돌려 씀)
                lat, lng = spots[i % len(spots)]
            else:
                lat = float(center[0]) + rnd.uniform(-JITTER, JITTER)
                lng = float(center[1]) + rnd.uniform(-JITTER, JITTER)
            rows.append((next_id, f"{rnd.choice(SURNAMES)}**", round(float(lat), 6), round(float(lng), 6),
                         source_id, region_id, fare_rule_ids[vehicle], *demo_rating(rnd)))
            next_id += 1
    if fallback:
        print("장소 파일이 없어 시군구 중심 ±2km로 배치:", ", ".join(fallback))
    return rows


def ensure_source(cur) -> int:
    cur.execute("SELECT source_id FROM data_sources WHERE source_code = %s", (SOURCE_CODE,))
    row = cur.fetchone()
    if row:   # 이미 있으면 설명만 지금 기준으로 갱신
        cur.execute("UPDATE data_sources SET dataset_name = %s, coverage_note = %s WHERE source_id = %s",
                    (DATASET_NAME, COVERAGE_NOTE, row["source_id"]))
        return row["source_id"]
    cur.execute("SELECT COALESCE(MAX(source_id), 0) + 1 AS n FROM data_sources")
    sid = cur.fetchone()["n"]
    cur.execute("""INSERT INTO data_sources (source_id, source_code, dataset_name, provider, portal_url, file_name,
                   base_month, retrieved_at, collection_method, coverage_note, region_id)
                   VALUES (%s, %s, %s, '짐니 팀 자체 생성', '-',
                           'scripts/seed_drivers_excel.py', '2026-09-01', CURDATE(), 'GENERATED', %s,
                           (SELECT region_id FROM regions WHERE sido_name = '전국' ORDER BY region_id LIMIT 1))""",
                (sid, SOURCE_CODE, DATASET_NAME, COVERAGE_NOTE))
    return sid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="배분 결과만 출력하고 DB에 쓰지 않음")
    args = parser.parse_args()

    sim = load_driver_simulation()                       # 엑셀 읽기 + 소계·총계 제외 + 합계 검증
    alloc = allocate(sim["sigungu"])
    by_sido = alloc.groupby("sido_name")["drivers"].sum().sort_values(ascending=False)
    print(f"원본: {EXCEL_PATH.name} · 시군구 {len(alloc)}곳 · 등록대수 {sim['check']['sum_total']:,}대 → 가상 기사 {int(alloc['drivers'].sum()):,}명")
    print("시도별:", ", ".join(f"{s} {n}" for s, n in by_sido.items()))

    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                ensure_rating_columns(cur)                   # 별점 칸 (이미 있으면 넘어감, 표 구조 변경은 바로 반영됨)
                cur.execute("SELECT region_id, sido_name, sigungu_name FROM regions WHERE sigungu_name IS NOT NULL")
                region_ids = {(r["sido_name"], r["sigungu_name"]): r["region_id"] for r in cur.fetchall()}
                missing = [k for k in zip(alloc["sido_name"], alloc["sigungu_name"]) if k not in region_ids]
                if missing:
                    raise SystemExit(f"regions에 없는 시군구: {missing}")
                cur.execute("SELECT fare_rule_id, vehicle_type FROM fare_rules WHERE is_active = TRUE")
                fare_rule_ids = {r["vehicle_type"]: r["fare_rule_id"] for r in cur.fetchall()}
                if not set(VEHICLE_PATTERN) <= set(fare_rule_ids):
                    raise SystemExit(f"fare_rules에 차종이 없습니다: {set(VEHICLE_PATTERN) - set(fare_rule_ids)}")

                source_id = ensure_source(cur)
                # 기존 가상 기사 정리: 예약에 안 쓰인 기사는 삭제, 쓰인 기사는 배정 불가로 보존
                placeholders = ", ".join(["%s"] * len(OLD_SOURCE_CODES))
                old = f"source_id IN (SELECT source_id FROM data_sources WHERE source_code IN ({placeholders}))"
                deleted = cur.execute(f"DELETE FROM drivers WHERE {old} AND driver_id NOT IN "
                                      "(SELECT driver_id FROM (SELECT DISTINCT driver_id FROM bookings) b)", OLD_SOURCE_CODES)
                kept = cur.execute(f"UPDATE drivers SET is_active = FALSE WHERE {old}", OLD_SOURCE_CODES)
                cur.execute("SELECT COALESCE(MAX(driver_id), 0) AS m FROM drivers")
                rows = build_rows(alloc, region_ids, fare_rule_ids, source_id, cur.fetchone()["m"] + 1)
                cur.executemany("""INSERT INTO drivers (driver_id, nickname, base_lat, base_lng, source_id, region_id,
                                                           fare_rule_id, avg_rating, rating_count)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", rows)

                # 검증: 활성 가상 기사 = 47,000, 차종 18,800/14,100/14,100
                cur.execute("""SELECT f.vehicle_type, COUNT(*) AS n FROM drivers d JOIN fare_rules f USING (fare_rule_id)
                               WHERE d.source_id = %s AND d.is_active = TRUE GROUP BY f.vehicle_type""", (source_id,))
                types = {r["vehicle_type"]: r["n"] for r in cur.fetchall()}
                expected = Counter(VEHICLE_PATTERN[i % len(VEHICLE_PATTERN)] for i in range(TOTAL_DRIVERS))
                if sum(types.values()) != TOTAL_DRIVERS or types != dict(expected):
                    raise SystemExit(f"검증 실패: {types}")
            if args.dry_run:
                conn.rollback()
                print(f"[dry-run] 삭제 예정 {deleted}명 · 배정 불가로 보존 {kept}명 · 생성 {len(rows)}명 · 차종 {types} — DB 변경 없음")
                return
            conn.commit()
            rated = sum(1 for row in rows if row[-1] > 0)
            print(f"완료: 기존 가상 기사 삭제 {deleted}명 · 예약 연결로 보존(배정 불가) {kept}명 · 새 가상 기사 {len(rows)}명 "
                  f"(별점 있음 {rated:,}명) · 차종 {types}")
        except BaseException:
            conn.rollback()
            raise


if __name__ == "__main__":
    sys.exit(main())
