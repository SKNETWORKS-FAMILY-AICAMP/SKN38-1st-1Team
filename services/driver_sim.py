"""배차 가능 기사 현황 — 시연용 가상 기사(MySQL drivers)의 지역·차종별 현황

1) 가상 기사 생성 기준 (scripts/seed_drivers_excel.py가 사용)
   원본: data/processed/화물차_시군구별_등록현황_202609.xlsx (통계누리 2026년 9월 시군구별 등록현황, 파일은 수정하지 않음)
       4행 머리글: A 시도 · B 시군구 · C 영업용 · D 계 (D = C) → 마지막 열 D(계)를 사용
       시도별 '소계'·'합계/총계' 행은 합산에서 빼고 검증에만 쓴다 → load_driver_simulation()
   이 등록대수 비율로 전국 47,000명을 시군구에 배분해 drivers에 저장 (차종 다마스 40 · 라보 30 · 1톤 30)

2) 화면 표시 (pages/4_Truck_Map.py '배차 가능 기사 현황')
   load_driver_status(): drivers에 실제 저장된 배정 가능(is_active) 가상 기사 수를 시도·시군구·차종별로 집계
   → 예약 매칭(services/matching.py)이 추천·배정하는 것과 같은 기사들이다.
   실제 기사 위치·실시간 운행 상태를 측정한 값은 아니다.

공식 등록 통계 화면은 services/truck_stats.py(MySQL registration_stats)를 그대로 사용한다.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

EXCEL_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "화물차_시군구별_등록현황_202609.xlsx"
HEADER_ROW = 3                      # 0부터 셀 때 4번째 행 = 머리글 (시도·시군구·영업용·계)
VALUE_COLUMN = "계"                 # 마지막 열(D)
SUBTOTAL, TOTAL_SIDO, TOTAL = "소계", "합계", "총계"
VEHICLES = ("다마스", "라보", "1톤")
ASSUMPTION = "엑셀의 시군구별 영업용 화물차 등록대수 비율로 전국 47,000명을 배분하고 차종을 다마스 40%·라보 30%·1톤 30%로 정한 시연용 가상 기사"


class SimulationDataError(RuntimeError):
    """엑셀 구조가 예상과 다르거나 합계 검증에 실패함"""


def _base_month(path: Path) -> date | None:
    m = re.search(r"_(\d{4})(\d{2})\.xlsx$", path.name)   # 파일명 끝의 YYYYMM
    return date(int(m.group(1)), int(m.group(2)), 1) if m else None


@st.cache_data(show_spinner=False)
def _load(path_str: str, mtime: float) -> dict:   # mtime: 파일이 바뀌면 다시 읽음
    path = Path(path_str)
    raw = pd.read_excel(path, header=HEADER_ROW, dtype={"시도": str, "시군구": str})
    missing = {"시도", "시군구", VALUE_COLUMN} - set(raw.columns)
    if missing:
        raise SimulationDataError(f"엑셀 머리글(4행)에서 {sorted(missing)} 열을 찾지 못했습니다.")
    df = raw[["시도", "시군구", VALUE_COLUMN]].rename(
        columns={"시도": "sido_name", "시군구": "sigungu_name", VALUE_COLUMN: "count"})
    df["sido_name"] = df["sido_name"].str.strip()
    df["sigungu_name"] = df["sigungu_name"].str.strip()
    df["count"] = pd.to_numeric(df["count"], errors="coerce")
    df = df.dropna(subset=["sido_name", "sigungu_name", "count"])           # 빈 행 제외

    total_rows = df[(df["sido_name"] == TOTAL_SIDO) | (df["sigungu_name"] == TOTAL)]
    subtotal_rows = df[df["sigungu_name"] == SUBTOTAL]
    sigungu = df[(df["sido_name"] != TOTAL_SIDO) & ~df["sigungu_name"].isin([SUBTOTAL, TOTAL])].copy()
    sigungu["count"] = sigungu["count"].astype("int64")

    # 검증: 시군구 합 == 엑셀 시도 소계, 시군구 전체 합 == 엑셀 전국 총계, 중복 없음
    sido = sigungu.groupby("sido_name", as_index=False)["count"].sum()
    official = dict(zip(subtotal_rows["sido_name"], subtotal_rows["count"].astype("int64")))
    mismatched = [s for s, v in zip(sido["sido_name"], sido["count"]) if official.get(s) != int(v)]
    if mismatched or set(official) != set(sido["sido_name"]):
        raise SimulationDataError(f"시도 소계와 시군구 합계가 맞지 않습니다: {mismatched or sorted(set(official) ^ set(sido['sido_name']))}")
    if len(total_rows) != 1 or int(total_rows["count"].iloc[0]) != int(sigungu["count"].sum()):
        raise SimulationDataError("전국 총계와 시군구 합계가 맞지 않습니다.")
    if sigungu.duplicated(["sido_name", "sigungu_name"]).any():
        raise SimulationDataError("같은 시도·시군구 행이 중복되어 있습니다.")

    return {
        "base_month": _base_month(path),
        # truck_map.build_deck을 그대로 쓰기 위해 공식 통계 화면과 같은 열 이름(truck_count)을 사용
        "sido": sido.rename(columns={"count": "truck_count"}),
        "sigungu": sigungu.rename(columns={"count": "truck_count"}).reset_index(drop=True),
        "check": {"sigungu_rows": len(sigungu), "subtotal_rows": len(subtotal_rows),
                  "excel_total": int(total_rows["count"].iloc[0]), "sum_total": int(sigungu["count"].sum())},
        "source_file": path.name,
    }


def load_driver_simulation() -> dict:
    """반환: {"base_month", "sido"(sido_name, truck_count), "sigungu"(sido_name, sigungu_name, truck_count), "check", "source_file"}"""
    if not EXCEL_PATH.exists():
        raise SimulationDataError(f"원본 엑셀이 없습니다: data/processed/{EXCEL_PATH.name}")
    return _load(str(EXCEL_PATH), EXCEL_PATH.stat().st_mtime)


_STATUS_SQL = """
    SELECT r.sido_name, r.sigungu_name, f.vehicle_type, COUNT(d.driver_id) AS n
    FROM regions r
    LEFT JOIN drivers d ON d.region_id = r.region_id AND d.is_active = TRUE
    LEFT JOIN fare_rules f ON f.fare_rule_id = d.fare_rule_id
    WHERE r.sigungu_name IS NOT NULL
    GROUP BY r.sido_name, r.sigungu_name, f.vehicle_type
"""


@st.cache_data(ttl=60, show_spinner="가상 기사 현황을 불러오는 중...")
def load_driver_status() -> dict:
    """drivers에 저장된 배정 가능 가상 기사 수 (시군구 기준, 차종별 열 포함).

    반환: {"base_month", "sido", "sigungu", "by_type"} — sido·sigungu는 truck_map.build_deck과 같은 truck_count 열 사용
    DB 연결 실패 시 DBConnectionError (캐시되지 않음)
    """
    from services.db import get_connection   # 엑셀만 쓰는 스크립트에서 DB 없이도 이 모듈을 불러올 수 있게

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(_STATUS_SQL)
        rows = pd.DataFrame(cur.fetchall(), columns=["sido_name", "sigungu_name", "vehicle_type", "n"])
    rows["n"] = pd.to_numeric(rows["n"]).astype("int64")
    sigungu = (rows.pivot_table(index=["sido_name", "sigungu_name"], columns="vehicle_type", values="n",
                                aggfunc="sum", fill_value=0)
               .reindex(columns=list(VEHICLES), fill_value=0).reset_index())
    sigungu.columns.name = None
    sigungu["truck_count"] = sigungu[list(VEHICLES)].sum(axis=1)
    sido = sigungu.groupby("sido_name", as_index=False)[["truck_count", *VEHICLES]].sum()
    sido = sido[sido["truck_count"] > 0].reset_index(drop=True)          # 기사가 없는 시도(전국 행 등) 제외
    sigungu = sigungu[sigungu["sido_name"].isin(sido["sido_name"])].reset_index(drop=True)
    return {"base_month": _base_month(EXCEL_PATH), "sido": sido, "sigungu": sigungu,
            "by_type": {v: int(sido[v].sum()) for v in VEHICLES}}
