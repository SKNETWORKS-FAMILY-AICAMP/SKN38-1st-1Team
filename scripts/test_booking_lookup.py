"""예약 조회·평점 저장 테스트 — 실제 테이블에 데이터를 넣지 않는다.

방법: 한 연결(세션) 안에서 bookings / drivers / fare_rules와 같은 이름의 TEMPORARY TABLE을 만든다.
      MySQL은 그 세션에서 임시 테이블을 우선 사용하므로 테스트 데이터는 임시 테이블에만 들어가고,
      연결을 닫으면 자동으로 사라진다. 실행 전후로 실제 테이블 건수가 같은지도 확인한다.

실행: python scripts/test_booking_lookup.py
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import booking_lookup as bl  # noqa: E402
from services import db  # noqa: E402

TABLES = ("fare_rules", "drivers", "bookings")
PHONE = "010-1234-5678"
results: list[tuple[str, bool]] = []


def check(name: str, cond: bool) -> None:
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def real_counts() -> dict:
    with db.get_connection() as c, c.cursor() as cur:  # 새 세션 = 임시 테이블이 보이지 않는 실제 테이블
        out = {}
        for t in TABLES:
            cur.execute(f"SELECT COUNT(*) AS n FROM `{t}`")
            out[t] = cur.fetchone()["n"]
        return out


PRIMARY_KEYS = {"fare_rules": "fare_rule_id", "drivers": "driver_id", "bookings": "booking_id"}


def temp_ddl(table: str) -> str:
    """sql/schema.sql의 CREATE TABLE 문을 TEMPORARY TABLE로 바꿔 사용 (실제 DB 구조와 동일함을 확인함)."""
    ddl = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    m = re.search(rf"CREATE TABLE `{table}` \((.*?)\n\);", ddl, re.S)
    if not m:
        raise RuntimeError(f"schema.sql에서 {table} 정의를 찾지 못했습니다.")
    return f"CREATE TEMPORARY TABLE `{table}` ({m.group(1)}, PRIMARY KEY (`{PRIMARY_KEYS[table]}`))"


def setup_temp(conn) -> None:
    with conn.cursor() as cur:
        for t in TABLES:
            cur.execute(temp_ddl(t))
        cur.execute("SHOW CREATE TABLE bookings")
        assert "TEMPORARY" in cur.fetchone()["Create Table"].upper(), "임시 테이블 생성 확인 실패 — 중단"
        cur.execute("INSERT INTO fare_rules (fare_rule_id, vehicle_type, max_load_kg, base_fare, base_distance_km, "
                    "per_km_fare, effective_from) VALUES (1, 'TEST_라보', 500, 0, 0, 0, '2026-01-01')")
        cur.execute("INSERT INTO drivers (driver_id, nickname, base_lat, base_lng, verification_status, source_id, "
                    "region_id, fare_rule_id) VALUES (1, 'TEST_기사', 0, 0, 'NOT_VERIFIED', 1, 1, 1)")
        rows = [  # booking_id, status, driver_id(999 = 존재하지 않는 기사)
            (900001, "BOOKED", 1), (900002, "DEPARTED", 1), (900003, "IN_TRANSIT", 1),
            (900004, "COMPLETED", 1), (900005, "CANCELLED", 1), (900006, "UNKNOWN_X", 1), (900007, "BOOKED", 999),
        ]
        for bid, status, drv in rows:
            cur.execute(
                "INSERT INTO bookings (booking_id, customer_name, customer_phone, origin_address, dest_address, "
                "scheduled_at, estimated_fare, origin_region_id, dest_region_id, fare_rule_id, driver_id, status) "
                "VALUES (%s, 'TEST', '01012345678', 'TEST 출발', 'TEST 도착', %s, 50000, 1, 1, 1, %s, %s)",
                (bid, datetime(2026, 12, 1, 9, 0), drv, status),
            )
    conn.commit()


def run_service_tests(conn) -> None:
    b = bl.find_booking(conn, 900001, PHONE)
    check("조회 성공 (하이픈 포함 연락처)", b is not None and b["status"] == "BOOKED")
    check("조회 결과에 연락처 미포함", b is not None and "customer_phone" not in b)
    check("기사·차량 정보 조인", b is not None and b["driver_name"] == "TEST_기사" and b["vehicle_type"] == "TEST_라보")
    check("연락처 불일치 → None", bl.find_booking(conn, 900001, "010-9999-9999") is None)
    check("없는 예약번호 → None", bl.find_booking(conn, 123, PHONE) is None)
    for bid, st in [(900002, "DEPARTED"), (900003, "IN_TRANSIT"), (900004, "COMPLETED"), (900005, "CANCELLED")]:
        check(f"상태 조회 {st}", bl.find_booking(conn, bid, PHONE)["status"] == st)
    check("기사 미배정(없는 driver_id) → driver_id None", bl.find_booking(conn, 900007, PHONE)["driver_id"] is None)
    check("예약번호 형식 검사", bl.parse_booking_id("12a") is None and bl.parse_booking_id(" 900001 ") == 900001)

    for bad in (0, 6, "3", True, 3.5):
        check(f"잘못된 평점 {bad!r} 거부", bl.submit_rating(conn, 900004, PHONE, bad) == bl.INVALID_RATING)
    check("미완료 운송 평가 거부", bl.submit_rating(conn, 900001, PHONE, 5) == bl.NOT_COMPLETED)
    check("취소 예약 평가 거부", bl.submit_rating(conn, 900005, PHONE, 5) == bl.NOT_COMPLETED)
    check("연락처 불일치 평가 거부", bl.submit_rating(conn, 900004, "010-0000-0000", 5) == bl.NOT_FOUND)
    check("완료 운송 평가 저장", bl.submit_rating(conn, 900004, PHONE, 4) == bl.SAVED)
    check("저장된 평점 확인", bl.find_booking(conn, 900004, PHONE)["rating"] == 4)
    check("중복 평가 거부", bl.submit_rating(conn, 900004, PHONE, 1) == bl.ALREADY_RATED)
    check("중복 평가 후 평점 유지", bl.find_booking(conn, 900004, PHONE)["rating"] == 4)


class _KeepOpen:
    """페이지의 `with get_connection() as conn:`이 테스트 연결을 닫지 않도록 감싼다."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *exc):
        return False


def run_page_tests(conn) -> None:
    from streamlit.testing.v1 import AppTest

    original = db.get_connection
    db.get_connection = lambda: _KeepOpen(conn)
    try:
        page = str(ROOT / "pages" / "3_Booking_Lookup.py")

        def lookup(bid, phone):
            at = AppTest.from_file(page).run(timeout=30)
            at.text_input[0].input(str(bid))
            at.text_input[1].input(phone)
            at.button[0].click().run(timeout=30)
            return at

        def text(at):
            parts = [e.value for kind in ("markdown", "error", "warning", "info", "success", "caption")
                     for e in getattr(at, kind)]
            parts += [f"{m.label} {m.value}" for m in at.metric]
            return " ".join(str(p) for p in parts)

        at = lookup(900003, PHONE)
        check("[화면] 조회 → 운송 중 표시", not at.exception and "운송 중" in text(at) and "TEST 출발" in text(at))
        at = lookup(900001, "010-1111-2222")
        check("[화면] 연락처 불일치 안내", "일치하는 예약이 없습니다" in text(at) and "TEST 출발" not in text(at))
        at = lookup(900005, PHONE)
        check("[화면] 취소 예약 안내", "취소된 예약" in text(at))
        at = lookup(900006, PHONE)
        check("[화면] 알 수 없는 상태 안내", "확인되지 않은 운송 상태" in text(at))
        at = lookup(900007, PHONE)
        check("[화면] 기사 미배정 안내", "배정된 기사가 없습니다" in text(at))
        at = lookup(900004, PHONE)
        check("[화면] 평가 완료 예약은 평점 표시", "평가 완료: 4점" in text(at) and len(at.radio) == 0)

        with conn.cursor() as cur:  # 완료·미평가 예약 하나 더 (임시 테이블)
            cur.execute("UPDATE bookings SET status='COMPLETED' WHERE booking_id=900003")
        conn.commit()
        at = lookup(900003, PHONE)
        at.radio[0].set_value(5)
        at.button[1].click().run(timeout=30)
        check("[화면] 평점 저장 → 평가 완료 표시", not at.exception and "평가 완료: 5점" in text(at))
    finally:
        db.get_connection = original


def main() -> int:
    before = real_counts()
    conn = db.get_connection()
    try:
        setup_temp(conn)
        run_service_tests(conn)
        run_page_tests(conn)
    finally:
        conn.close()  # 임시 테이블 자동 삭제
    after = real_counts()
    check(f"실제 테이블 변경 없음 {after}", before == after)
    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} 통과")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
