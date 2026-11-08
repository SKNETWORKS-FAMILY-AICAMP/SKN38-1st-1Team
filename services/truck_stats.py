"""지역별 영업용 화물차 등록대수 조회 (registration_stats / regions / data_sources).

SQL은 sql/registration_queries.sql을 그대로 읽어 재사용한다 (파일 안의 4개 쿼리 순서 고정).
    1. 최신 기준월  2. 시도별  3. 시군구별  4. 출처

주의: 국토교통부 월별 '등록' 통계이며, 실시간 운행 차량 수나 플랫폼 이용 가능 기사 수가 아니다.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import streamlit as st

from services.db import get_connection

QUERY_FILE = Path(__file__).resolve().parents[1] / "sql" / "registration_queries.sql"
CACHE_TTL_SECONDS = 3600  # 월 단위 통계이므로 1시간 캐시 → 화면 재실행 때마다 DB에 접속하지 않음
DATA_NOTE = "국토교통부 자동차등록현황 월별 통계의 영업용 화물차 '등록대수'입니다. 실시간 운행 차량 수나 짐니 이용 가능 기사 수가 아닙니다."


def _load_queries() -> list[str]:
    text = re.sub(r"--[^\n]*", "", QUERY_FILE.read_text(encoding="utf-8"))
    queries = [q.strip() for q in text.split(";") if q.strip()]
    if len(queries) != 4:
        raise RuntimeError(f"{QUERY_FILE.name}의 쿼리 수가 4개가 아닙니다 ({len(queries)}개).")
    return queries


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="화물차 등록 통계를 불러오는 중...")
def load_truck_stats() -> dict:
    """반환: {"base_month": date|None, "sido": DataFrame, "sigungu": DataFrame, "source": dict|None}

    DB 연결 실패 시 DBConnectionError를 그대로 올린다 (예외는 캐시되지 않음).
    """
    q_latest, q_sido, q_sigungu, q_source = _load_queries()
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(q_latest)
        base_month = cur.fetchone()["latest_month"]
        cur.execute(q_sido)
        sido = pd.DataFrame(cur.fetchall(), columns=["sido_name", "truck_count", "base_month"])
        cur.execute(q_sigungu)
        sigungu = pd.DataFrame(
            cur.fetchall(),
            columns=["region_id", "sido_name", "sigungu_name", "adm_code", "truck_count", "base_month"],
        )
        cur.execute(q_source)
        source = cur.fetchone()

    for df in (sido, sigungu):
        df["truck_count"] = pd.to_numeric(df["truck_count"]).astype("int64")
    return {"base_month": base_month, "sido": sido, "sigungu": sigungu, "source": source}


def format_month(value) -> str:
    return f"{value.year}년 {value.month}월" if value else "-"
