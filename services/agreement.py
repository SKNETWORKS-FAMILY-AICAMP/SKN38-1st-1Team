"""사전 확정 운임 — 예약 전 최종 운임·작업 조건 확인과 소비자 동의 상태 관리

흐름
    1) 매칭 결과 화면(2_Driver_Matching)에서 예준님 운임 계산(fare.estimate) 결과로 build_quote() → request["quote"]
       견적에는 '견적을 낼 때의 운송 조건 해시(conditions_hash)'를 함께 저장한다.
    2) 예약하기 화면(6_Booking)에서 quote_problem()으로 견적이 지금 조건과 맞는지·확정 운임인지 확인
    3) 동의 체크 → record_agreement() (조건+운임 전체의 terms_hash와 동의 시각을 세션에 저장)
    4) 예약 확정 직전 is_agreed()로 다시 확인 → 동의한 terms_hash와 지금 조건이 같을 때만 저장

조건(주소·좌표·상세주소·일시·층수·엘리베이터·물품·인력)이 하나라도 바뀌면 해시가 달라져
기존 견적과 동의는 자동으로 무효가 된다. (금액은 새로 만들지 않고 fare.estimate 결과만 사용)

DB 저장: 예약 확정 시 agreement_record()를 bookings.agreed_at · agreement_hash · agreed_terms에 저장
      (sql/bookings_agreement_columns.sql). 합의 운임은 estimated_fare, 조건은 기존 컬럼에 그대로 저장된다.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

AGREEMENT_KEY = "fare_agreement"   # {"terms_hash": str, "agreed_at": datetime}
AGREEMENT_TEXT = "위 운송 조건과 최종 운임을 확인했으며, 해당 내용에 동의합니다."

# 동의 대상 운송 조건 (transport_request의 키 그대로)
CONDITION_FIELDS = (
    "origin_address", "pickup_lat", "pickup_lng", "pickup_detail_address",
    "dest_address", "dropoff_lat", "dropoff_lng", "dropoff_detail_address",
    "scheduled_at", "origin_floor", "origin_has_elevator", "dest_floor", "dest_has_elevator",
    "item_s_count", "item_m_count", "item_l_count", "item_xl_count", "helper_option",
)
# 동의 대상 견적 값 (fare.estimate 결과에서 옮겨 온 값)
QUOTE_FIELDS = ("vehicle_type", "distance_km", "estimated_minutes", "service_type", "distance_code",
                "base_fare", "service_fee", "origin_stair_fee", "destination_stair_fee", "estimated_fare")


def _canonical(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="minutes")
    if isinstance(value, float):
        return round(value, 6)
    return value


def _hash(data: dict) -> str:
    text = json.dumps({k: _canonical(v) for k, v in data.items()}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def condition_snapshot(request: dict) -> dict:
    return {k: request.get(k) for k in CONDITION_FIELDS}


def conditions_hash(request: dict) -> str:
    return _hash(condition_snapshot(request))


def build_quote(request: dict, estimate: dict | None, service_type: str | None) -> dict | None:
    """fare.estimate 결과를 예약에 쓸 견적으로 옮긴다 (금액 계산은 하지 않음)."""
    if not estimate:
        return None
    vehicle = estimate.get("vehicle") or {}
    distance = estimate.get("distance") or {}
    fare = estimate.get("fare") or {}
    breakdown = fare.get("fare_breakdown") or {}
    return {
        "vehicle_type": vehicle.get("vehicle_type"),
        "distance_km": distance.get("distance_km"),
        "estimated_minutes": distance.get("duration_minutes"),
        "distance_estimated": bool(distance.get("estimated")),
        "service_type": service_type,
        "distance_code": fare.get("distance_code"),
        "base_fare": breakdown.get("base_fare"),
        "service_fee": breakdown.get("service_fee"),
        "origin_stair_fee": breakdown.get("origin_stair_fee"),
        "destination_stair_fee": breakdown.get("destination_stair_fee"),
        "estimated_fare": estimate.get("total_fare"),
        # 운임 확정 여부는 운임 계산 결과(fare.success: 거리 구간·계단 작업이 표준 요금표 안)로 판단.
        # 차량 쪽 manual_check(물품 무게 미입력 등)는 적재 확인 안내일 뿐 금액에는 영향이 없어 별도 표시만 한다.
        "fare_confirmed": bool(fare.get("success")) and estimate.get("total_fare") is not None,
        "vehicle_check_note": vehicle.get("reason") if vehicle.get("manual_check") else None,
        "conditions_hash": conditions_hash(request),
    }


def quote_problem(request: dict, quote: dict | None) -> str | None:
    """견적으로 예약(동의)할 수 없는 이유. 문제가 없으면 None."""
    if not quote:
        return "견적 정보가 없습니다. 매칭 결과 화면에서 운임을 다시 확인해 주세요."
    if quote.get("conditions_hash") != conditions_hash(request):
        return "운송 조건이 바뀌어 기존 견적과 동의가 무효가 되었습니다. 운임을 다시 확인해 주세요."
    if not quote.get("fare_confirmed") or quote.get("estimated_fare") is None:
        return "계단 작업 층수 등 별도 확인이 필요한 조건이 있어 최종 운임을 확정할 수 없습니다."
    return None


def terms_hash(request: dict, quote: dict) -> str:
    """동의 대상 전체(운송 조건 + 견적 금액)의 해시."""
    return _hash({**condition_snapshot(request), **{f"quote_{k}": quote.get(k) for k in QUOTE_FIELDS}})


def record_agreement(state, request: dict, quote: dict, agreed: bool) -> None:
    if agreed and quote_problem(request, quote) is None:
        state[AGREEMENT_KEY] = {"terms_hash": terms_hash(request, quote), "agreed_at": datetime.now()}
    else:
        state.pop(AGREEMENT_KEY, None)


def is_agreed(state, request: dict, quote: dict | None) -> bool:
    """지금 조건·견적이 동의한 내용과 정확히 같을 때만 True."""
    agreement = state.get(AGREEMENT_KEY)
    return bool(agreement) and quote_problem(request, quote) is None \
        and agreement["terms_hash"] == terms_hash(request, quote)


def agreement_record(state, request: dict, quote: dict) -> dict | None:
    """예약 저장용 동의 증거 (bookings.agreed_at · agreement_hash · agreed_terms). 동의가 유효하지 않으면 None."""
    if not is_agreed(state, request, quote):
        return None
    agreement = state[AGREEMENT_KEY]
    terms = {
        "text": AGREEMENT_TEXT,
        "conditions": {k: _canonical(v) for k, v in condition_snapshot(request).items()},
        "quote": {k: quote.get(k) for k in QUOTE_FIELDS},
    }
    return {"agreed_at": agreement["agreed_at"], "agreement_hash": agreement["terms_hash"], "agreed_terms": terms}
