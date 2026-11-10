"""기사 주소지 후보 좌표 수집 — 카카오 로컬 키워드 검색으로 시군구마다 실제 장소(아파트·주민센터 등) 좌표를 모은다

목적: 가상 기사 좌표를 시군구 중심 ± 무작위 대신 '그 시군구 안의 실제 장소 좌표'로 두어
      지도에서 점이 바다·다른 시군구로 나가지 않게 한다 (scripts/seed_drivers_excel.py가 사용).

수집 기준
    - 검색어: '{시군구} {키워드}' (아파트·주민센터·주차장·마트·공원·편의점 … 20개 순서대로), 시군구 중심 반경 20km 안
    - 장소 주소(address_name)의 시군구 표기가 그 시군구와 같고, 중심에서 40km 이내인 것만 사용 (같은 이름 구 구분)
    - 같은 좌표는 한 번만. 시군구별 필요 인원(10,000명 배분)만큼 모이면 다음 시군구로
    - 행정구역 개편으로 주소 표기가 바뀐 시군구(예: 2026 인천 중구·동구·서구 → 제물포구·영종구·서해구)는
      이름이 맞는 장소가 없으므로, 같은 시도 주소이면서 통계 중심 좌표 3km 안의 장소를 사용
    - 저장: data/processed/driver_places.csv (region_id, lat, lng) — 장소 이름은 저장하지 않음

실행 (프로젝트 루트, .env의 KAKAO_REST_API_KEY 필요)
    python -m scripts.collect_driver_places
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

from scripts.seed_drivers_excel import allocate
from services.db import get_connection
from services.driver_sim import load_driver_simulation
from services.kakao_local import _get
from services.matching import haversine_km

OUT = Path(__file__).resolve().parents[1] / "data" / "processed" / "driver_places.csv"
CENTERS = Path(__file__).resolve().parents[1] / "data" / "processed" / "sigungu_coordinates.csv"
KEYWORDS = ("아파트", "주민센터", "주차장", "마트", "공원", "편의점", "카페", "학교", "병원", "약국",
            "은행", "교회", "음식점", "빌라", "오피스텔", "주유소", "세탁소", "미용실", "체육관", "도서관")
SEARCH_RADIUS_M = 20_000
MAX_KM = 40
MIN_PLACES = 10
TARGET_RATIO = 1.0          # 필요 인원만큼 모이면 다음 시군구로 (모자라면 같은 장소를 여러 기사가 함께 씀)
NEAR_KM = 3


def _matches(address: str, sigungu: str) -> bool:
    tokens = (address or "").split()
    parts = sigungu.split()
    if not tokens:
        return False
    if sigungu.endswith("특별자치시"):                      # 세종: 시도 = 시군구
        return tokens[0] == sigungu
    return " ".join(tokens[1:1 + len(parts)]) == sigungu


def collect_region(sigungu: str, center: tuple[float, float] | None, need: int, sido: str = "",
                   by_name: bool = True) -> list[tuple[float, float]]:
    found: dict[tuple[float, float], None] = {}
    for kw in KEYWORDS:
        for page in (1, 2, 3):
            params = {"query": f"{sigungu} {kw}", "size": 15, "page": page}
            if center:
                params.update({"y": center[0], "x": center[1], "radius": SEARCH_RADIUS_M})
            data = _get("keyword", params)
            for d in data.get("documents", []):
                try:
                    lat, lng = float(d["y"]), float(d["x"])
                except (KeyError, TypeError, ValueError):
                    continue
                if by_name:
                    if not _matches(d.get("address_name", ""), sigungu):
                        continue
                    if center and haversine_km(center[0], center[1], lat, lng) > MAX_KM:
                        continue
                elif not (d.get("address_name", "").startswith(sido)
                          and haversine_km(center[0], center[1], lat, lng) <= NEAR_KM):
                    continue
                found[(round(lat, 6), round(lng, 6))] = None
            time.sleep(0.05)
            if data.get("meta", {}).get("is_end", True):
                break
        if len(found) >= max(MIN_PLACES, int(need * TARGET_RATIO)):
            break
    return list(found)


def main() -> None:
    alloc = allocate(load_driver_simulation()["sigungu"])
    centers = pd.read_csv(CENTERS).set_index("region_id") if CENTERS.exists() else pd.DataFrame()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT region_id, sido_name, sigungu_name FROM regions WHERE sigungu_name IS NOT NULL")
        region_ids = {(r["sido_name"], r["sigungu_name"]): r["region_id"] for r in cur.fetchall()}
    rows, short = [], []
    for r in alloc[alloc["drivers"] > 0].itertuples(index=False):
        rid = region_ids[(r.sido_name, r.sigungu_name)]
        center = (float(centers.loc[rid, "lat"]), float(centers.loc[rid, "lng"])) if rid in centers.index else None
        places = collect_region(r.sigungu_name, center, int(r.drivers))
        if not places and center:                       # 주소 표기가 바뀐 시군구: 같은 시도 + 중심 3km 안
            places = collect_region(r.sigungu_name, center, int(r.drivers), r.sido_name, by_name=False)
        rows += [(rid, lat, lng) for lat, lng in places]
        if len(places) < int(r.drivers):
            short.append(f"{r.sido_name} {r.sigungu_name} {len(places)}/{int(r.drivers)}")
        print(f"{r.sido_name} {r.sigungu_name}: 필요 {int(r.drivers)}명 · 장소 {len(places)}곳")
    pd.DataFrame(rows, columns=["region_id", "lat", "lng"]).to_csv(OUT, index=False)
    print(f"저장: {OUT.name} · 장소 {len(rows)}곳 · 시군구 {len(set(x[0] for x in rows))}곳")
    if short:
        print("장소가 필요 인원보다 적은 곳 (같은 장소를 여러 기사가 함께 씀):", ", ".join(short))


if __name__ == "__main__":
    sys.exit(main())
