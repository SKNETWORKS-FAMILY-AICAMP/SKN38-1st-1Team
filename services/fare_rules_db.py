"""요금표 조회 (MySQL fare_rules 테이블) — 요금표 화면과 FAQ의 운임 요금표가 공통으로 사용.

services/fare_table.py는 운임 계산용 기준표(예준님 담당)로 바뀌었으므로, DB 조회 함수는 이 파일에 둔다.
운임 '계산' 로직은 services/fare.py 소관이며 여기서는 DB에 등록된 기준을 표로 보여주기만 한다.
fare_rules가 비어 있으면 빈 DataFrame을 돌려주고, 화면에서 '요금표 확정 전'으로 안내한다.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.db import get_connection

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
