"""플랫폼 수수료 및 기사 예상 정산액 계산

운임 구성 (운임 = fare.estimate가 계산한 운송비)
    고객 결제 예상액 = 운임 + 서비스 이용료(운임 × 5%)
    기사 예상 정산액 = 운임 − 기사 수수료(운임 × 18%)
    플랫폼 수익     = 서비스 이용료 + 기사 수수료 (운임의 23%)
- 금액은 100원 단위 반올림
- 수수료율 근거: 퀵 업계 평균 기사 수수료 약 23% → 플랫폼 몫은 23% 유지,
  그중 5%를 고객 이용료로 나눠 기사 부담을 18%로 낮춤 (고객 별도 수수료 예: 크몽 구매자 3.5%)
- 화면 사용: 2페이지 결제 예상액 / 7_Fare_Table·FAQ 수수료 안내표 / 예약 저장(bookings.commission_*, driver_payout)
라이브러리: decimal(반올림 오차 없는 금액 계산)
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

# ── 수수료 정책 (여기만 바꾸면 화면·저장 모두 반영) ─────────────────────
SERVICE_FEE_PCT = 5      # 고객 서비스 이용료 (운임에 추가)
DRIVER_FEE_PCT = 18      # 기사 수수료 (운임에서 차감)
ROUND_UNIT = 100         # 100원 단위 반올림
EXAMPLE_FARE = 50_000    # 안내표 예시 운임


def _won(value: Decimal) -> int:                                  # 100원 단위 반올림
    return int((value / ROUND_UNIT).quantize(Decimal("1"), ROUND_HALF_UP) * ROUND_UNIT)


# ── 1. 운임 1건 계산 ───────────────────────────────────────────────
def calc_settlement(fare: int) -> dict:
    """운임 → 고객 결제액·기사 정산액·플랫폼 수익"""
    fare = int(fare)
    service_fee = _won(Decimal(fare) * SERVICE_FEE_PCT / 100)
    driver_fee = _won(Decimal(fare) * DRIVER_FEE_PCT / 100)
    return {
        "fare": fare,                                     # 운임 (운송비)
        "service_fee": service_fee,                       # 고객 서비스 이용료
        "customer_total": fare + service_fee,             # 고객 결제 예상액
        "driver_fee": driver_fee,                         # 기사 수수료
        "driver_payout": fare - driver_fee,               # 기사 예상 정산액
        "platform_revenue": service_fee + driver_fee,     # 플랫폼 수익
        "platform_rate": SERVICE_FEE_PCT + DRIVER_FEE_PCT,  # 운임 대비 플랫폼 몫(%, 23) → bookings.commission_rate
    }


# ── 2. 화면용 표 ───────────────────────────────────────────────────
def fee_policy_table(example_fare: int = EXAMPLE_FARE) -> list[dict]:
    """수수료 안내표 (운임표·FAQ 화면에서 st.table(...)로 표시)"""
    s = calc_settlement(example_fare)
    return [
        {"항목": "운임", "부담": "-", "기준": "거리·차량·추가 작업으로 계산", f"예시 ({example_fare:,}원)": f"{s['fare']:,}원"},
        {"항목": "서비스 이용료", "부담": "고객", "기준": f"운임의 {SERVICE_FEE_PCT}%", f"예시 ({example_fare:,}원)": f"+{s['service_fee']:,}원"},
        {"항목": "고객 결제 예상액", "부담": "고객", "기준": "운임 + 서비스 이용료", f"예시 ({example_fare:,}원)": f"{s['customer_total']:,}원"},
        {"항목": "기사 수수료", "부담": "기사", "기준": f"운임의 {DRIVER_FEE_PCT}%", f"예시 ({example_fare:,}원)": f"−{s['driver_fee']:,}원"},
        {"항목": "기사 예상 정산액", "부담": "기사", "기준": "운임 − 기사 수수료", f"예시 ({example_fare:,}원)": f"{s['driver_payout']:,}원"},
    ]


def settlement_rows(fare: int) -> list[dict]:
    """예약 1건의 금액 구성 (고객 화면용: 운임·이용료·결제액만)"""
    s = calc_settlement(fare)
    return [
        {"항목": "운임", "금액": f"{s['fare']:,}원"},
        {"항목": f"서비스 이용료 ({SERVICE_FEE_PCT}%)", "금액": f"{s['service_fee']:,}원"},
        {"항목": "결제 예상 금액", "금액": f"{s['customer_total']:,}원"},
    ]