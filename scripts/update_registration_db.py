"""영업용 화물차 등록대수 → MySQL 갱신 (regions / data_sources / registration_stats).

사용법 (프로젝트 루트에서)
    python scripts/update_registration_db.py --check     DB 연결·스키마 점검만 (쓰기 없음)
    python scripts/update_registration_db.py --dry-run   API 수집·전처리·지역 매핑까지 확인, DB 쓰기 없음
    python scripts/update_registration_db.py             새 기준월이면 저장, 같은 기준월이면 변경 없이 종료

동작
    1. DB 연결 후 3개 테이블의 실제 컬럼·자료형을 information_schema로 확인
    2. registration_stats에 저장된 최신 기준월(화물·영업용) 조회
    3. API 최신 공표 기준월과 비교 → 새 기준월이 아니면 종료 (exit 0)
    4. 전처리·검증을 DB 쓰기 전에 모두 끝냄 (실패 시 DB는 건드리지 않음)
    5. 하나의 트랜잭션으로 data_sources 기록 → regions 매핑(없으면 추가) → registration_stats 추가
    6. 저장 건수·합계 검증 후 COMMIT, 하나라도 실패하면 ROLLBACK (기존 데이터 유지)

중복 방지: (base_month, region_id, vehicle_kind, usage_type)가 이미 있으면 INSERT 하지 않음.
과거 기준월 데이터는 삭제·수정하지 않는다.

로그: logs/update_registration_db.log (.gitignore의 *.log 규칙으로 업로드 제외)
종료 코드: 0 = 저장 완료 또는 변경 없음, 1 = 오류
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from molit_api import MolitApiError, fetch_latest  # noqa: E402
from preprocess_registration import (  # noqa: E402
    USAGE_TYPE,
    VEHICLE_KIND,
    ValidationError,
    preprocess,
    save_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
LOG_PATH = ROOT / "logs" / "update_registration_db.log"

# ── 저장 값 설정 (팀 규칙과 다르면 여기만 수정) ────────────────────────────
# regions.region_level 값 (VARCHAR(10)) — 다른 코드 컬럼(BOOKED, NOT_VERIFIED…)과 같이 대문자 사용
REGION_LEVEL_NATION = "NATION"
REGION_LEVEL_SIDO = "SIDO"
REGION_LEVEL_SIGUNGU = "SIGUNGU"
# data_sources.region_id가 NOT NULL이므로, 전국 단위 출처는 '전국' 지역 행을 참조한다.
NATION_NAME = "전국"
SOURCE_INFO = {
    "dataset_name": "자동차등록현황보고 - 자동차등록대수현황 시도별",
    "provider": "국토교통부",
    "portal_url": "https://stat.molit.go.kr/portal/cate/statMetaView.do?hRsId=58",
    "collection_method": "OpenAPI",
}

REQUIRED_COLUMNS = {
    "regions": {"region_id", "region_level", "parent_region_id", "sido_name", "sigungu_name", "adm_code"},
    "data_sources": {
        "source_id", "source_code", "dataset_name", "provider", "portal_url", "file_name",
        "base_month", "retrieved_at", "collection_method", "coverage_note", "region_id",
    },
    "registration_stats": {"stat_id", "source_id", "region_id", "base_month", "vehicle_kind", "usage_type", "vehicle_count"},
}
PRIMARY_KEYS = {"regions": "region_id", "data_sources": "source_id", "registration_stats": "stat_id"}

# 기존 regions에 공식 명칭이 들어 있어도 API 표기(약칭)와 매칭되도록 정규화
SIDO_ALIASES = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원도": "강원", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
    "전라북도": "전북", "전북특별자치도": "전북", "경상북도": "경북", "경상남도": "경남",
    "제주도": "제주", "제주특별자치도": "제주",
    "전남광주통합특별시": "전남광주",  # 2026-07 광주·전남 통합 (전국화물운송사업자 데이터 표기)
}

log = logging.getLogger("update_registration_db")


class SchemaError(RuntimeError):
    """DB 스키마가 예상과 다름."""


# ── 공통 ─────────────────────────────────────────────────────────────
def setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    for handler in (logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()):
        handler.setFormatter(fmt)
        log.addHandler(handler)
    log.setLevel(logging.INFO)


def connect():
    cfg = {k: os.getenv(k, "").strip() for k in ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")}
    if not cfg["DB_USER"] or not cfg["DB_NAME"]:
        raise SchemaError("DB_USER / DB_NAME이 .env에 설정되어 있지 않습니다.")
    for k in ("DB_PASSWORD", "DB_NAME"):
        if cfg[k].startswith("실제") or not cfg[k].isascii():
            raise SchemaError(f"{k}가 예시 값 그대로입니다. .env에 실제 MySQL 값을 입력하세요.")
    return pymysql.connect(
        host=cfg["DB_HOST"] or "localhost",
        port=int(cfg["DB_PORT"] or 3306),
        user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"],
        database=cfg["DB_NAME"],
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def norm(value) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def norm_sido(value) -> str:
    v = norm(value)
    return SIDO_ALIASES.get(v, v)


# ── 스키마 점검 ──────────────────────────────────────────────────────
def load_schema(cur) -> dict[str, dict[str, dict]]:
    cur.execute(
        """
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE,
               COLUMN_DEFAULT, EXTRA, CHARACTER_MAXIMUM_LENGTH
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('regions', 'data_sources', 'registration_stats')
        """
    )
    schema: dict[str, dict[str, dict]] = {}
    for r in cur.fetchall():
        schema.setdefault(r["TABLE_NAME"], {})[r["COLUMN_NAME"]] = r

    for table, cols in REQUIRED_COLUMNS.items():
        if table not in schema:
            raise SchemaError(f"테이블 {table}이(가) 없습니다. sql/ 스키마를 먼저 실행하세요.")
        missing = cols - set(schema[table])
        if missing:
            raise SchemaError(f"{table}에 컬럼이 없습니다: {sorted(missing)}")
        # 우리가 채우지 않는 NOT NULL 컬럼(기본값·자동증가 없음)이 있으면 INSERT가 실패하므로 미리 확인
        for name, c in schema[table].items():
            if (name not in cols and c["IS_NULLABLE"] == "NO" and c["COLUMN_DEFAULT"] is None
                    and "auto_increment" not in c["EXTRA"] and "GENERATED" not in c["EXTRA"].upper()):
                raise SchemaError(f"{table}.{name}은(는) NOT NULL인데 이 스크립트가 값을 넣지 않습니다.")
    return schema


def month_to_db(yyyymm: str, col: dict):
    """기준월 'YYYYMM'을 DB 컬럼 자료형에 맞게 변환."""
    t = col["DATA_TYPE"].lower()
    if t in ("date", "datetime", "timestamp"):
        return date(int(yyyymm[:4]), int(yyyymm[4:6]), 1)
    if t in ("int", "bigint", "mediumint", "smallint"):
        return int(yyyymm)
    if (col["CHARACTER_MAXIMUM_LENGTH"] or 0) >= 7:
        return f"{yyyymm[:4]}-{yyyymm[4:6]}"
    return yyyymm


def month_from_db(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return f"{value.year:04d}{value.month:02d}"
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits[:6] if len(digits) >= 6 else None


def check_value(table: str, column: str, value, schema) -> None:
    """ENUM 허용값, 문자열 길이를 INSERT 전에 확인."""
    if value is None:
        return
    col = schema[table][column]
    if col["DATA_TYPE"].lower() == "enum":
        allowed = [v.strip("'") for v in col["COLUMN_TYPE"][5:-1].split("','")]
        if str(value) not in allowed:
            raise SchemaError(f"{table}.{column} ENUM {allowed}에 '{value}' 값이 없습니다. 스크립트 상단 설정을 수정하세요.")
    max_len = col["CHARACTER_MAXIMUM_LENGTH"]
    if max_len and isinstance(value, str) and len(value) > max_len:
        raise SchemaError(f"{table}.{column} 최대 길이 {max_len}자를 넘습니다: {value[:40]}…")


def is_auto_increment(table: str, schema) -> bool:
    return "auto_increment" in schema[table][PRIMARY_KEYS[table]]["EXTRA"].lower()


def next_id(cur, table: str) -> int:
    """PK에 AUTO_INCREMENT가 없을 때 사용. 트랜잭션 안에서 FOR UPDATE로 잠가 동시 실행 충돌을 막는다."""
    pk = PRIMARY_KEYS[table]
    cur.execute(f"SELECT `{pk}` FROM `{table}` ORDER BY `{pk}` DESC LIMIT 1 FOR UPDATE")
    row = cur.fetchone()
    return (row[pk] if row else 0) + 1


def insert(cur, table: str, values: dict, schema) -> int:
    pk = PRIMARY_KEYS[table]
    if not is_auto_increment(table, schema):
        values = {pk: next_id(cur, table), **values}
    for k, v in values.items():
        check_value(table, k, v, schema)
    cols = ", ".join(f"`{k}`" for k in values)
    marks = ", ".join(["%s"] * len(values))
    cur.execute(f"INSERT INTO `{table}` ({cols}) VALUES ({marks})", list(values.values()))
    return values[pk] if pk in values else cur.lastrowid


# ── 단계별 처리 ──────────────────────────────────────────────────────
def stored_latest_month(cur) -> str | None:
    cur.execute(
        "SELECT MAX(base_month) AS m FROM registration_stats WHERE vehicle_kind = %s AND usage_type = %s",
        (VEHICLE_KIND, USAGE_TYPE),
    )
    return month_from_db(cur.fetchone()["m"])


def ensure_nation_region(cur, schema, write: bool) -> int | None:
    """data_sources.region_id용 '전국' 지역 행. 없으면 추가."""
    cur.execute(
        "SELECT region_id FROM regions WHERE sido_name = %s AND (sigungu_name IS NULL OR sigungu_name = '') "
        "ORDER BY region_id LIMIT 1",
        (NATION_NAME,),
    )
    row = cur.fetchone()
    if row:
        return row["region_id"]
    if not write:
        return None
    return insert(cur, "regions", {
        "region_level": REGION_LEVEL_NATION, "parent_region_id": None,
        "sido_name": NATION_NAME, "sigungu_name": None, "adm_code": None,
    }, schema)


def load_regions(cur) -> tuple[dict, dict]:
    """반환: ({sido: region_id}, {(sido, sigungu): region_id}) — 이름은 정규화된 값"""
    cur.execute("SELECT region_id, region_level, sido_name, sigungu_name FROM regions")
    sido_ids, sigungu_ids = {}, {}
    for r in cur.fetchall():
        sido, sigungu = norm_sido(r["sido_name"]), norm(r["sigungu_name"])
        if norm(r["region_level"]).upper() == REGION_LEVEL_NATION or sido == NATION_NAME:
            continue
        if sigungu:
            sigungu_ids[(sido, sigungu)] = r["region_id"]
        else:
            sido_ids.setdefault(sido, r["region_id"])
    return sido_ids, sigungu_ids


def map_regions(cur, df, schema, write: bool) -> tuple[list[int | None], int]:
    """df의 각 행을 region_id에 매핑. write=True면 없는 지역을 regions에 추가."""
    sido_ids, sigungu_ids = load_regions(cur)
    added = 0
    for sido in sorted(df["sido_name"].unique()):
        if sido not in sido_ids:
            added += 1
            sido_ids[sido] = insert(cur, "regions", {
                "region_level": REGION_LEVEL_SIDO, "parent_region_id": None,
                "sido_name": sido, "sigungu_name": None, "adm_code": None,
            }, schema) if write else None
    ids = []
    for sido, sigungu in zip(df["sido_name"], df["sigungu_name"]):
        key = (sido, sigungu)
        if key not in sigungu_ids:
            added += 1
            sigungu_ids[key] = insert(cur, "regions", {
                "region_level": REGION_LEVEL_SIGUNGU, "parent_region_id": sido_ids[sido],
                "sido_name": sido, "sigungu_name": sigungu, "adm_code": None,
            }, schema) if write else None
        ids.append(sigungu_ids[key])
    return ids, added


def upsert_source(cur, month: str, report: dict, file_name: str, schema) -> int:
    source_code = f"MOLIT_REG_5498_{month}"
    cur.execute("SELECT source_id FROM data_sources WHERE source_code = %s", (source_code,))
    row = cur.fetchone()
    if row:
        return row["source_id"]
    note = (f"통계표는 '시도별'이나 시군구 단위 행 제공. {VEHICLE_KIND}>{USAGE_TYPE}만 저장, "
            f"시도 '계' 소계행 제외, 시군구 {report['sigungu_rows']}건, 합계 {report['total_vehicle_count']}대")
    now = datetime.now().replace(microsecond=0)
    retrieved = now.date() if schema["data_sources"]["retrieved_at"]["DATA_TYPE"].lower() == "date" else now
    return insert(cur, "data_sources", {
        "source_code": source_code, **SOURCE_INFO, "file_name": file_name,
        "base_month": month_to_db(month, schema["data_sources"]["base_month"]),
        "retrieved_at": retrieved, "coverage_note": note,
        "region_id": ensure_nation_region(cur, schema, write=True),
    }, schema)


def insert_stats(cur, df, region_ids, source_id, month_value, schema) -> int:
    """(base_month, region_id, vehicle_kind, usage_type)가 이미 있는 행은 건너뛴다."""
    for col, val in (("vehicle_kind", VEHICLE_KIND), ("usage_type", USAGE_TYPE)):
        check_value("registration_stats", col, val, schema)
    cur.execute(
        "SELECT region_id FROM registration_stats "
        "WHERE base_month = %s AND vehicle_kind = %s AND usage_type = %s FOR UPDATE",
        (month_value, VEHICLE_KIND, USAGE_TYPE),
    )
    existing = {r["region_id"] for r in cur.fetchall()}
    rows = [(rid, int(cnt)) for rid, cnt in zip(region_ids, df["vehicle_count"]) if rid not in existing]
    if not rows:
        return 0

    cols = ["source_id", "region_id", "base_month", "vehicle_kind", "usage_type", "vehicle_count"]
    params = [(source_id, rid, month_value, VEHICLE_KIND, USAGE_TYPE, cnt) for rid, cnt in rows]
    if not is_auto_increment("registration_stats", schema):
        start = next_id(cur, "registration_stats")
        cols = ["stat_id", *cols]
        params = [(start + i, *p) for i, p in enumerate(params)]
    sql = (f"INSERT INTO registration_stats ({', '.join(cols)}) "
           f"VALUES ({', '.join(['%s'] * len(cols))})")
    cur.executemany(sql, params)
    return len(params)


def verify_month(cur, month_value, expected_rows: int, expected_total: int) -> None:
    cur.execute(
        """
        SELECT COUNT(*) AS n, COALESCE(SUM(vehicle_count), 0) AS total,
               COUNT(DISTINCT region_id) AS regions
        FROM registration_stats
        WHERE base_month = %s AND vehicle_kind = %s AND usage_type = %s
        """,
        (month_value, VEHICLE_KIND, USAGE_TYPE),
    )
    r = cur.fetchone()
    if (r["n"], int(r["total"]), r["regions"]) != (expected_rows, expected_total, expected_rows):
        raise ValidationError(
            f"저장 검증 실패: 건수 {r['n']}/{expected_rows}, 합계 {r['total']}/{expected_total}, 지역 {r['regions']}"
        )
    # FK 무결성: 모든 행이 존재하는 source/region을 참조하는지
    cur.execute(
        """
        SELECT COUNT(*) AS bad FROM registration_stats s
        LEFT JOIN regions r ON r.region_id = s.region_id
        LEFT JOIN data_sources d ON d.source_id = s.source_id
        WHERE s.base_month = %s AND (r.region_id IS NULL OR d.source_id IS NULL)
        """,
        (month_value,),
    )
    if cur.fetchone()["bad"]:
        raise ValidationError("region_id 또는 source_id가 존재하지 않는 행이 있습니다.")


# ── 실행 ─────────────────────────────────────────────────────────────
def run(check_only: bool = False, dry_run: bool = False) -> int:
    conn = connect()
    try:
        with conn.cursor() as cur:
            schema = load_schema(cur)
            stored = stored_latest_month(cur)
            cur.execute("SELECT COUNT(*) AS n FROM regions")
            n_regions = cur.fetchone()["n"]
            log.info("DB 연결·스키마 확인 OK | regions %d건 | 저장된 최신 기준월: %s", n_regions, stored or "없음")
            if check_only:
                return 0

            month, rows, meta = fetch_latest()
            log.info("API 최신 공표 기준월: %s (%d행, %s)", month, len(rows), meta["form_name"])
            if stored and stored >= month:
                log.info("새 기준월 없음 → 변경 없이 종료")
                return 0

            df, _, report = preprocess(rows, month)
            log.info("전처리 OK: 시군구 %d건, 합계 %d대 (공식 '계' 합 %d대)",
                     report["sigungu_rows"], report["total_vehicle_count"], report["official_total"])

            if dry_run:
                _, to_add = map_regions(cur, df, schema, write=False)
                log.info("[dry-run] regions에 새로 추가될 지역: %d건 | DB 쓰기 없이 종료", to_add)
                conn.rollback()
                return 0

            raw_path, _ = save_outputs(rows, df, month)
            month_value = month_to_db(month, schema["registration_stats"]["base_month"])
            try:
                source_id = upsert_source(cur, month, report, raw_path.name, schema)
                region_ids, added = map_regions(cur, df, schema, write=True)
                inserted = insert_stats(cur, df, region_ids, source_id, month_value, schema)
                verify_month(cur, month_value, report["sigungu_rows"], report["total_vehicle_count"])
                conn.commit()
            except Exception:
                conn.rollback()
                log.error("저장 중 오류 → ROLLBACK (기존 데이터 유지)")
                raise
            log.info("저장 완료: 기준월 %s | source_id %s | regions 추가 %d건 | registration_stats 추가 %d건",
                     month, source_id, added, inserted)
            return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="영업용 화물차 등록대수 MySQL 갱신")
    parser.add_argument("--check", action="store_true", help="DB 연결·스키마 점검만")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 수집·전처리·매핑만 확인")
    args = parser.parse_args()
    setup_logging()
    try:
        return run(check_only=args.check, dry_run=args.dry_run)
    except (MolitApiError, ValidationError, SchemaError) as e:
        log.error("%s: %s", type(e).__name__, e)
    except pymysql.MySQLError as e:
        log.error("MySQL 오류: %s", e)
    except Exception:
        log.exception("예상하지 못한 오류")
    return 1


if __name__ == "__main__":
    sys.exit(main())
