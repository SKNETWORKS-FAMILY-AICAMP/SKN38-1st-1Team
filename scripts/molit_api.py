"""국토교통부 통계누리 OpenAPI 호출 — 자동차등록대수현황 시도별 (form_id=5498, style_num=2).

환경변수(.env)
    MOLIT_API_KEY : 인증키
    MOLIT_API_URL : 인증키를 제외한 요청 URL (form_id, style_num 포함)
                    URL에 key/start_dt/end_dt가 들어 있어도 무시하고 코드에서 다시 붙인다.

응답 특징 (2026-11 실제 호출로 확인)
    - JSON, result_status.status_code: INFO-000 정상 / INFO-200 데이터 없음 / ERROR-xxx 오류
    - 페이지네이션 없음 (요청 기간 전체가 한 번에 반환), 한 번에 최대 5년까지 요청 가능
    - 행 단위: date(YYYYMM), 시도명, 시군구 ('계' = 시도 소계 행)
    - 값 컬럼: '{차종}>{용도}' — 차종: 승용/승합/화물/특수/총계, 용도: 관용/자가용/영업용/계
    - result_data.cert_id 는 인증키와 같은 값이므로 저장·출력하지 않는다.

실행: python scripts/molit_api.py   → 최신 공표 기준월과 행 수 출력
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DEFAULT_URL = "https://stat.molit.go.kr/portal/openapi/service/rest/getList.do?form_id=5498&style_num=2"
STATUS_OK = "INFO-000"
STATUS_NO_DATA = "INFO-200"
MAX_LOOKBACK_MONTHS = 60  # API 제한: 한 번에 최대 5년
TIMEOUT = 60


class MolitApiError(RuntimeError):
    """API 호출 실패 또는 비정상 응답."""


def _config() -> tuple[str, dict, str]:
    key = os.getenv("MOLIT_API_KEY", "").strip()
    if not key:
        raise MolitApiError("MOLIT_API_KEY가 .env에 설정되어 있지 않습니다.")
    url = os.getenv("MOLIT_API_URL", "").strip() or DEFAULT_URL
    parts = urlsplit(url)
    params = {k: v for k, v in parse_qsl(parts.query) if k not in ("key", "start_dt", "end_dt")}
    params.setdefault("form_id", "5498")
    params.setdefault("style_num", "2")
    # 인증키가 평문으로 전송되지 않도록 https 사용 (http URL도 https로 변환)
    base = urlunsplit(("https", parts.netloc, parts.path, "", ""))
    return base, params, key


def _mask(text: str, key: str) -> str:
    return text.replace(key, "***") if key else text


def shift_month(yyyymm: str, months: int) -> str:
    y, m = int(yyyymm[:4]), int(yyyymm[4:6])
    idx = y * 12 + (m - 1) + months
    return f"{idx // 12:04d}{idx % 12 + 1:02d}"


def fetch_raw(start_month: str, end_month: str) -> dict:
    """start_month~end_month(YYYYMM) 구간 조회. 데이터가 없으면 rows=[]."""
    base, params, key = _config()
    query = {**params, "key": key, "start_dt": start_month, "end_dt": end_month}
    try:
        resp = requests.get(base, params=query, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise MolitApiError(_mask(f"API 요청 실패: {e}", key)) from None

    # 주의: 이 API는 '데이터 없음(INFO-200)', '인증키 오류(INFO-100)'도 HTTP 500 + JSON 본문으로 응답한다.
    # 그래서 HTTP 코드보다 본문의 status_code를 먼저 확인한다.
    try:
        payload = json.loads(resp.content.decode("utf-8"))
    except ValueError:
        raise MolitApiError(
            _mask(f"JSON이 아닌 응답 (HTTP {resp.status_code}): {resp.text[:200]!r}", key)
        ) from None
    if not isinstance(payload, dict) or "result_status" not in payload:
        raise MolitApiError(f"예상하지 못한 응답 형식 (HTTP {resp.status_code})")

    status = payload.get("result_status") or {}
    code = status.get("status_code")
    if code not in (STATUS_OK, STATUS_NO_DATA):
        raise MolitApiError(f"API 오류 {code}: {status.get('message')}")

    data = payload.get("result_data") or {}
    rows = (data.get("formList") or []) if code == STATUS_OK else []
    return {
        "status_code": code,
        "message": status.get("message"),
        "form_name": data.get("formName"),
        "unit": data.get("unitName"),
        "rows": rows,
    }


def fetch_latest(lookback_months: int = 12, today: date | None = None) -> tuple[str, list[dict], dict]:
    """최근 lookback_months 개월을 조회해 가장 최근 공표 기준월과 그 달의 행만 반환."""
    lookback_months = max(1, min(lookback_months, MAX_LOOKBACK_MONTHS))
    today = today or date.today()
    end = f"{today.year:04d}{today.month:02d}"
    start = shift_month(end, -(lookback_months - 1))
    res = fetch_raw(start, end)
    if not res["rows"]:
        raise MolitApiError(f"{start}~{end} 기간에 공표된 데이터가 없습니다.")
    latest = max(str(r["date"]) for r in res["rows"])
    latest_rows = [r for r in res["rows"] if str(r["date"]) == latest]
    meta = {k: v for k, v in res.items() if k != "rows"} | {"requested": f"{start}~{end}"}
    return latest, latest_rows, meta


if __name__ == "__main__":
    month, rows, meta = fetch_latest()
    print(f"통계표: {meta['form_name']} (단위: {meta['unit']})")
    print(f"조회 기간: {meta['requested']} → 최신 공표 기준월: {month}, 행 수: {len(rows)}")
