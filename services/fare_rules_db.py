"""요금표 화면용 표 — services/fare_table.py 기준표를 화면 표로 바꾼다 (services/fare_view.py가 사용).

운임 '계산' 로직은 services/fare.py 소관이며 여기서는 기준을 표로 보여주기만 한다.
load_fare_rules(): MySQL fare_rules 조회 (현재 화면에서는 사용하지 않음).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.db import get_connection
from services.fare_table import (
    FARE_RULES, ITEM_GRADES, MAX_STAIR_FLOOR, SERVICE_RULES, STAIR_RULES,
    VEHICLE_CAPACITY, VEHICLE_ORDER,
)

COLUMNS = {
    "vehicle_type": "차종",
    "max_load_kg": "최대 적재량(kg)",
    "base_fare": "기본요금(원)",
    "base_distance_km": "기본거리(km)",
    "per_km_fare": "km당 요금(원)",
    "effective_from": "적용일",
}


@st.cache_data(ttl=300, show_spinner=False)
def load_fare_rules() -> pd.DataFrame:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT vehicle_type, max_load_kg, base_fare, base_distance_km, per_km_fare, effective_from "
            "FROM fare_rules WHERE is_active = TRUE ORDER BY max_load_kg, fare_rule_id"
        )
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=list(COLUMNS)).rename(columns=COLUMNS)


# ── 요금표 페이지용: fare_table.py 기준표 → 화면용 표 (DB 없이 동작) ──
def _plus(fee: int) -> str:
    return "추가 없음" if fee == 0 else f"+{fee:,}원"          # 0원 → '추가 없음', 그 외 → '+10,000원'


def fare_band_table() -> list[dict]:
    """① 거리별 기본 운임 (D1~D7)"""
    return [
        {"거리": f"{r['min']}~{r['max']}km", **{v: f"{r['fares'][v]:,}원" for v in VEHICLE_ORDER}}
        for r in FARE_RULES
    ]


def stair_fee_table() -> list[dict]:
    """② 엘리베이터 없을 때 계단 작업 요금 (지하 포함)"""
    rows = [
        {"층수": f"지하 {-f}층" if f < 0 else f"{f}층", "추가 요금": _plus(STAIR_RULES[f])}
        for f in sorted(STAIR_RULES)                               # 지하 2층 → 5층 순서
    ]
    rows.append({
        "층수": f"{MAX_STAIR_FLOOR + 1}층 이상 · 지하 {-min(STAIR_RULES) + 1}층 이하",
        "추가 요금": "별도 협의",
    })
    return rows


def item_size_table() -> list[dict]:
    """③ 짐 크기 등급별 차량 적재 가능 수량 (차량이 정해지면 ① 거리별 운임 적용)"""
    def _count(n):
        return "불가" if n == 0 else ("가능 (수량 별도 확인)" if n is None else f"최대 {n}개")
    return [
        {"등급": g, "크기 합(가로+세로+높이)": f"{s['max_size_sum']}cm 이하",
         "무게": f"{s['max_weight']}kg 이하", "예시": s["description"],
         **{v: _count(VEHICLE_CAPACITY[v][g]) for v in VEHICLE_ORDER}}
        for g, s in ITEM_GRADES.items()
    ]


def extra_fee_table() -> list[dict]:
    """④ 인력 추가 요금 (기사 상하차 도움·추가 작업자)"""
    return [{"항목": r["name"], "추가 요금": _plus(r["fee"])} for r in SERVICE_RULES.values()]