"""MySQL 연결 (프로젝트 루트 .env의 DB_* 값 사용).

사용 예
    from services.db import get_connection, DBConnectionError
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ... WHERE id = %s", (value,))   # 반드시 파라미터 바인딩 사용

연결은 필요할 때 열고 바로 닫는다. 반복 조회 결과는 각 서비스에서 st.cache_data로 캐시한다.
클라우드 MySQL(배포용)은 DB_SSL=true로 암호화 연결 (공인 인증서 목록 certifi 사용, 로컬은 설정하지 않음).
"""

from __future__ import annotations

import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


class DBConnectionError(RuntimeError):
    """MySQL에 연결할 수 없음 (서버 중지, .env 설정 오류 등)."""


def _ssl_options() -> dict:
    if os.getenv("DB_SSL", "").strip().lower() not in ("1", "true", "yes"):
        return {}
    import certifi
    return {"ssl": {"ca": certifi.where()}}


def get_connection():
    try:
        return pymysql.connect(
            host=os.getenv("DB_HOST", "localhost").strip(),
            port=int(os.getenv("DB_PORT", "3306").strip() or 3306),
            user=os.getenv("DB_USER", "").strip(),
            password=os.getenv("DB_PASSWORD", "").strip(),
            database=os.getenv("DB_NAME", "").strip(),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=5,
            **_ssl_options(),
        )
    except (pymysql.MySQLError, ValueError, UnicodeError) as e:
        # 비밀번호 등 접속 정보는 메시지에 넣지 않는다.
        raise DBConnectionError(
            "MySQL에 연결할 수 없습니다. MySQL 서버가 실행 중인지, .env의 DB 설정이 맞는지 확인해 주세요."
        ) from e
