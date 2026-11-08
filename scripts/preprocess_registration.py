"""자동차등록대수현황 API 응답 → 시군구별 영업용 화물차 등록대수 (Pandas 전처리).

처리 기준
    - 지정한 기준월 행만 사용
    - '화물>영업용' 컬럼만 추출
    - 시군구 '계' 행(시도 소계)은 검증에만 쓰고 저장 대상에서 제외 → 중복 집계 방지
    - 시도·시군구 이름 공백 정리 (시도명은 API 표기 그대로: 서울, 경기, 전남광주 …)

검증 (하나라도 실패하면 ValidationError)
    - 필수 컬럼 존재, 이름 NULL 없음, 등록대수 숫자·0 이상
    - (시도, 시군구) 중복 없음
    - 모든 시도에 '계' 행이 있고, 시군구 합계 == '계' 값 (공식 소계와 일치)
    - 행 단위로 화물>계 == 관용 + 자가용 + 영업용

실행: python scripts/preprocess_registration.py
    → 최신 기준월을 수집해 data/raw/, data/processed/ 에 저장하고 시도별 합계 출력
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

VEHICLE_KIND = "화물"
USAGE_TYPE = "영업용"
VALUE_COL = f"{VEHICLE_KIND}>{USAGE_TYPE}"
SUBTOTAL = "계"
USAGES = ("관용", "자가용", "영업용")

OUTPUT_COLUMNS = ["base_month", "sido_name", "sigungu_name", "vehicle_kind", "usage_type", "vehicle_count"]


class ValidationError(ValueError):
    """전처리 결과가 검증 기준을 통과하지 못함."""


def standardize_name(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return " ".join(str(value).split())


def preprocess(rows: list[dict], base_month: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """반환: (시군구 상세 df, 시도별 합계 df, 검증 리포트)"""
    df = pd.DataFrame(rows)
    required = {"date", "시도명", "시군구", VALUE_COL, f"{VEHICLE_KIND}>계", *(f"{VEHICLE_KIND}>{u}" for u in USAGES)}
    missing = required - set(df.columns)
    if missing:
        raise ValidationError(f"API 응답에 필요한 컬럼이 없습니다: {sorted(missing)}")

    df = df[df["date"].astype(str) == str(base_month)].copy()
    if df.empty:
        raise ValidationError(f"{base_month} 기준월 데이터가 없습니다.")

    df["sido_name"] = df["시도명"].map(standardize_name)
    df["sigungu_name"] = df["시군구"].map(standardize_name)
    if (df["sido_name"] == "").any() or (df["sigungu_name"] == "").any():
        raise ValidationError("시도명 또는 시군구가 비어 있는 행이 있습니다.")

    num_cols = [f"{VEHICLE_KIND}>{u}" for u in (*USAGES, "계")]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[num_cols].isna().any().any():
        raise ValidationError("등록대수에 숫자가 아닌 값(NULL)이 있습니다.")
    if (df[num_cols] < 0).any().any():
        raise ValidationError("등록대수에 음수가 있습니다.")

    usage_sum = sum(df[f"{VEHICLE_KIND}>{u}"] for u in USAGES)
    if not (usage_sum == df[f"{VEHICLE_KIND}>계"]).all():
        raise ValidationError("화물>계 ≠ 관용+자가용+영업용 인 행이 있습니다.")

    is_subtotal = df["sigungu_name"] == SUBTOTAL
    subtotal = df[is_subtotal].set_index("sido_name")[VALUE_COL]
    detail = df[~is_subtotal].copy()

    if subtotal.index.duplicated().any():
        raise ValidationError("한 시도에 '계' 행이 여러 개 있습니다.")
    dup = detail.duplicated(["sido_name", "sigungu_name"], keep=False)
    if dup.any():
        raise ValidationError(f"중복 시군구: {detail.loc[dup, ['sido_name', 'sigungu_name']].values.tolist()}")

    detail_sum = detail.groupby("sido_name")[VALUE_COL].sum()
    if set(detail_sum.index) != set(subtotal.index):
        raise ValidationError(
            f"'계' 행과 시군구 행의 시도 목록이 다릅니다: {sorted(set(detail_sum.index) ^ set(subtotal.index))}"
        )
    mismatch = detail_sum.sort_index() != subtotal.sort_index()
    if mismatch.any():
        raise ValidationError(f"시군구 합계가 공식 '계'와 다른 시도: {list(mismatch[mismatch].index)}")

    detail["base_month"] = str(base_month)
    detail["vehicle_kind"] = VEHICLE_KIND
    detail["usage_type"] = USAGE_TYPE
    detail["vehicle_count"] = detail[VALUE_COL].astype("int64")
    out = detail[OUTPUT_COLUMNS].sort_values(["sido_name", "sigungu_name"]).reset_index(drop=True)

    sido = (
        out.groupby("sido_name", as_index=False)["vehicle_count"].sum()
        .sort_values("vehicle_count", ascending=False)
        .reset_index(drop=True)
    )
    report = {
        "base_month": str(base_month),
        "raw_rows": int(len(df)),
        "subtotal_rows": int(is_subtotal.sum()),
        "sigungu_rows": int(len(out)),
        "sido_count": int(out["sido_name"].nunique()),
        "total_vehicle_count": int(out["vehicle_count"].sum()),
        "official_total": int(subtotal.sum()),
    }
    return out, sido, report


def save_outputs(rows: list[dict], out: pd.DataFrame, base_month: str) -> tuple[Path, Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"molit_registration_sido_{base_month}.json"
    csv_path = PROCESSED_DIR / f"truck_business_by_sigungu_{base_month}.csv"
    raw_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return raw_path, csv_path


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from molit_api import fetch_latest

    month, rows, _ = fetch_latest()
    out, sido, report = preprocess(rows, month)
    raw_path, csv_path = save_outputs(rows, out, month)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(sido.to_string(index=False))
    print(f"저장: {raw_path.relative_to(ROOT)}, {csv_path.relative_to(ROOT)}")
