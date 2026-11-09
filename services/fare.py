"""운송 거리 계산, 차량 추천 및 운임 계산 로직.

운임/차량 기준 데이터는 services/fare_table.py에서 가져옵니다.
기사 검색 및 실제 기사 매칭은 matching.py에서 처리합니다.
"""

import os

import requests
from dotenv import load_dotenv

from services.fare_table import (
    FARE_RULES,
    ITEM_GRADES,
    MAX_DISTANCE_KM,
    MAX_STAIR_FLOOR,
    REQUEST_TIMEOUT,
    SERVICE_RULES,
    STAIR_RULES,
    VEHICLE_CAPACITY,
    VEHICLE_ORDER,
    VEHICLE_SPECS,
)


# ============================================================
# 1. 카카오 API 설정
# ============================================================

load_dotenv()
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")


def _get_kakao_headers():
    """카카오 API 요청에 사용할 인증 헤더를 반환합니다."""
    if not KAKAO_REST_API_KEY:
        raise ValueError("KAKAO_REST_API_KEY가 설정되지 않았습니다.")

    return {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}


# ============================================================
# 2. 주소 및 거리 계산
# ============================================================

def geocode(address):
    """카카오 주소 검색 API를 이용해 주소를 (경도, 위도)로 변환합니다."""
    if not isinstance(address, str) or not address.strip():
        raise ValueError("주소를 입력해 주세요.")

    response = requests.get(
        "https://dapi.kakao.com/v2/local/search/address.json",
        headers=_get_kakao_headers(),
        params={"query": address.strip()},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    documents = response.json().get("documents", [])
    if not documents:
        raise ValueError(f"주소를 찾을 수 없습니다: {address}")

    location = documents[0].get("address")
    if not location:
        raise ValueError(f"주소의 좌표 정보를 찾을 수 없습니다: {address}")

    return float(location["x"]), float(location["y"])


def _kakao_route(origin, destination):
    """카카오 자동차 길찾기 API로 실제 주행거리(km)와 시간(분)을 조회합니다."""
    response = requests.get(
        "https://apis-navi.kakaomobility.com/v1/directions",
        headers=_get_kakao_headers(),
        params={
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "priority": "RECOMMEND",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    routes = response.json().get("routes", [])
    if not routes or routes[0].get("result_code") != 0:
        raise ValueError("자동차 길찾기 경로를 찾을 수 없습니다.")

    summary = routes[0]["summary"]
    distance_km = summary["distance"] / 1000
    duration_minutes = summary["duration"] / 60

    return distance_km, duration_minutes


def get_distance(origin_address, destination_address):
    """출발지와 도착지의 자동차 주행거리 및 예상 소요시간을 조회합니다."""
    origin = geocode(origin_address)
    destination = geocode(destination_address)
    distance, duration = _kakao_route(origin, destination)

    return {
        "distance_km": round(distance, 2),
        "duration_minutes": round(duration, 1),
        "source": "Kakao Mobility",
        "estimated": False,
    }


# ============================================================
# 3. 물품 입력값 검증
# ============================================================

def validate_items(item_counts):
    """등급별 물품 수량을 검증하고 누락된 등급은 0으로 채웁니다.

    입력 예시:
        {"S": 3, "M": 2, "L": 0, "XL": 0, "XXL": 0}
    """
    if not isinstance(item_counts, dict):
        raise ValueError("물품 수량은 딕셔너리로 입력해야 합니다.")

    unknown = set(item_counts) - set(ITEM_GRADES)
    if unknown:
        raise ValueError(f"지원하지 않는 물품 등급: {unknown}")

    normalized = {}
    for grade in ITEM_GRADES:
        count = item_counts.get(grade, 0)

        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(f"{grade} 등급 수량은 정수여야 합니다.")
        if count < 0:
            raise ValueError(f"{grade} 등급 수량은 음수일 수 없습니다.")

        normalized[grade] = count

    if sum(normalized.values()) == 0:
        raise ValueError("최소 1개 이상의 물품을 입력해야 합니다.")

    return normalized


# ============================================================
# 4. 차량 매칭
# ============================================================

def _match_single_grade(grade, count):
    """단일 등급 물품 수량을 기준으로 작은 차량부터 추천합니다."""
    for vehicle in VEHICLE_ORDER:
        capacity = VEHICLE_CAPACITY[vehicle][grade]

        # None은 수용 가능 수량 미확정, 0은 적재 비추천
        if capacity is None or capacity == 0:
            continue

        if count <= capacity:
            return {
                "vehicle_type": vehicle,
                "manual_check": False,
                "reason": "등급별 수량 기준으로 차량 추천",
            }

    if grade in ["XL", "XXL"]:
        return {
            "vehicle_type": "1톤",
            "manual_check": True,
            "reason": "대형 물품의 실제 적재 규격 및 고정 상태 확인 필요",
        }

    return {
        "vehicle_type": None,
        "manual_check": True,
        "reason": "수량 기준에 맞는 차량 없음",
    }


def _match_mixed_grade(counts):
    """혼합 등급 물품의 추정 적재 비율을 합산해 차량을 추천합니다."""
    if counts["XL"] > 0 or counts["XXL"] > 0:
        return {
            "vehicle_type": "1톤",
            "manual_check": True,
            "reason": "대형 물품 포함: 실제 적재 규격 확인 필요",
        }

    for vehicle in VEHICLE_ORDER:
        utilization = 0
        possible = True

        for grade, count in counts.items():
            if count == 0:
                continue

            capacity = VEHICLE_CAPACITY[vehicle][grade]
            if capacity is None or capacity == 0:
                possible = False
                break

            utilization += count / capacity

        if possible and utilization <= 1:
            return {
                "vehicle_type": vehicle,
                "manual_check": False,
                "reason": "혼합 물품 추정 적재량 기준",
                "estimated_utilization": round(utilization, 2),
            }

    return {
        "vehicle_type": None,
        "manual_check": True,
        "reason": "혼합 물품의 적재량이 차량 수용 기준 초과",
    }


def _check_dimensions(vehicle_type, item_dimensions):
    """개별 물품 크기와 차량 적재함 규격을 비교합니다.

    item_dimensions 예시:
        [
            {"length": 120, "width": 50, "height": 40},
            {"length": 90, "width": 60, "height": 50},
        ]
    """
    specs = VEHICLE_SPECS[vehicle_type]

    if item_dimensions is None:
        return {
            "passed": None,
            "reason": "개별 물품 크기 미입력",
        }

    if not isinstance(item_dimensions, list) or not item_dimensions:
        raise ValueError("물품 크기는 리스트 형태로 입력해야 합니다.")

    errors = []
    for index, item in enumerate(item_dimensions, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{index}번 물품 크기 정보가 올바르지 않습니다.")

        dimensions = [
            item.get("length"),
            item.get("width"),
            item.get("height"),
        ]

        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value <= 0
            for value in dimensions
        ):
            raise ValueError(f"{index}번 물품의 크기를 확인해 주세요.")

        longest, second, shortest = sorted(dimensions, reverse=True)

        if longest > specs["max_length"]:
            errors.append(f"{index}번 물품 최장변 초과")
        if second > specs["max_width"]:
            errors.append(f"{index}번 물품 폭 초과")
        if specs["max_height"] is not None and shortest > specs["max_height"]:
            errors.append(f"{index}번 물품 높이 초과")

    return {
        "passed": len(errors) == 0,
        "reason": errors if errors else "규격 기준 통과",
    }


def pick_vehicle(item_counts, total_weight_kg=None, item_dimensions=None):
    """물품 수량, 실제 크기 및 전체 무게를 기준으로 차량을 추천합니다."""
    counts = validate_items(item_counts)

    active_grades = [
        grade for grade, count in counts.items() if count > 0
    ]

    if len(active_grades) == 1:
        grade = active_grades[0]
        result = _match_single_grade(grade, counts[grade])
    else:
        result = _match_mixed_grade(counts)

    vehicle = result["vehicle_type"]
    if vehicle is None:
        return {
            **result,
            "dimension_check": None,
            "weight_check": None,
        }

    # 전체 물품 무게 검증
    if total_weight_kg is not None:
        if (
            isinstance(total_weight_kg, bool)
            or not isinstance(total_weight_kg, (int, float))
            or total_weight_kg < 0
        ):
            raise ValueError("전체 물품 무게는 0 이상의 숫자여야 합니다.")

        max_payload = VEHICLE_SPECS[vehicle]["max_payload"]

        if max_payload is None:
            weight_check = {
                "passed": None,
                "reason": "차량 등록 적재 중량 미확인",
            }
            result["manual_check"] = True
        elif total_weight_kg > max_payload:
            weight_check = {
                "passed": False,
                "reason": "차량 허용 적재 중량 초과",
            }
            result["vehicle_type"] = None
            result["manual_check"] = True
        else:
            weight_check = {
                "passed": True,
                "reason": "허용 적재 중량 이내",
            }
    else:
        weight_check = {
            "passed": None,
            "reason": "전체 물품 무게 미입력",
        }
        result["manual_check"] = True

    # 개별 물품 크기 검증
    dimension_check = _check_dimensions(vehicle, item_dimensions)
    if dimension_check["passed"] is not True:
        result["manual_check"] = True

    return {
        **result,
        "dimension_check": dimension_check,
        "weight_check": weight_check,
    }


# ============================================================
# 5. 거리 구간별 기본 운임 계산
# ============================================================

def calc_base_fare(vehicle_type, distance_km):
    """차량 종류와 주행거리를 기준으로 거리 구간별 기본 운임을 계산합니다.

    기존 운임표 기준으로 정확히 5km, 10km 등의 경계값은 앞 구간에 포함합니다.
    """
    if vehicle_type not in VEHICLE_ORDER:
        raise ValueError("올바르지 않은 차량 종류입니다.")

    if (
        isinstance(distance_km, bool)
        or not isinstance(distance_km, (int, float))
        or distance_km < 0
    ):
        raise ValueError("주행거리는 0 이상의 숫자여야 합니다.")

    if distance_km > MAX_DISTANCE_KM:
        return {
            "fare": None,
            "distance_code": None,
            "manual_check": True,
            "reason": f"{MAX_DISTANCE_KM}km 초과: 별도 견적 필요",
        }

    for index, rule in enumerate(FARE_RULES):
        if rule["min"] <= distance_km <= rule["max"]:
            # 0km를 제외한 정확한 구간 경계는 앞 구간 운임 적용
            if distance_km == rule["min"] and rule["min"] > 0:
                previous_rule = FARE_RULES[index - 1]
                return {
                    "fare": previous_rule["fares"][vehicle_type],
                    "distance_code": previous_rule["code"],
                    "manual_check": False,
                    "reason": "거리 구간별 기본 운임",
                }

            return {
                "fare": rule["fares"][vehicle_type],
                "distance_code": rule["code"],
                "manual_check": False,
                "reason": "거리 구간별 기본 운임",
            }

    raise ValueError("거리 구간을 확인할 수 없습니다.")


# ============================================================
# 6. 기사 및 추가 작업자 비용 계산
# ============================================================

def calc_service_fee(service_type):
    """서비스 유형에 따른 기사 및 작업자 비용을 계산합니다."""
    if service_type not in SERVICE_RULES:
        raise ValueError(f"올바르지 않은 서비스 유형입니다: {service_type}")

    rule = SERVICE_RULES[service_type]
    return {
        "service_type": service_type,
        "service_name": rule["name"],
        "fee": rule["fee"],
    }


# ============================================================
# 7. 계단 작업 비용 계산
# ============================================================

def calc_stair_fee(floor, has_elevator):
    """출발지 또는 도착지의 계단 작업 비용을 계산합니다."""
    if not isinstance(has_elevator, bool):
        raise ValueError("엘리베이터 여부는 True 또는 False여야 합니다.")

    if (
        isinstance(floor, bool)
        or not isinstance(floor, int)
        or floor < 1
    ):
        raise ValueError("층수는 1 이상의 정수여야 합니다.")

    if has_elevator:
        return {
            "fee": 0,
            "manual_check": False,
            "reason": "엘리베이터 이용",
        }

    if floor > MAX_STAIR_FLOOR:
        return {
            "fee": None,
            "manual_check": True,
            "reason": f"{MAX_STAIR_FLOOR + 1}층 이상: 별도 협의",
        }

    return {
        "fee": STAIR_RULES[floor],
        "manual_check": False,
        "reason": f"{floor}층 계단 작업",
    }


# ============================================================
# 8. 최종 운임 계산
# ============================================================

def calc_fare(
    vehicle_type,
    distance_km,
    service_type="VEHICLE_ONLY",
    origin_floor=1,
    origin_elevator=True,
    destination_floor=1,
    destination_elevator=True,
):
    """기본 운임 + 서비스 비용 + 출발/도착지 계단 비용을 계산합니다."""
    base = calc_base_fare(vehicle_type, distance_km)

    if base["fare"] is None:
        return {
            "success": False,
            "vehicle_type": vehicle_type,
            "total_fare": None,
            "manual_check": True,
            "reason": base["reason"],
        }

    service = calc_service_fee(service_type)
    origin_stair = calc_stair_fee(origin_floor, origin_elevator)
    destination_stair = calc_stair_fee(
        destination_floor,
        destination_elevator,
    )

    manual_check = (
        origin_stair["manual_check"]
        or destination_stair["manual_check"]
    )

    if manual_check:
        total_fare = None
    else:
        total_fare = (
            base["fare"]
            + service["fee"]
            + origin_stair["fee"]
            + destination_stair["fee"]
        )

    return {
        "success": not manual_check,
        "vehicle_type": vehicle_type,
        "distance_km": distance_km,
        "distance_code": base["distance_code"],
        "fare_breakdown": {
            "base_fare": base["fare"],
            "service_fee": service["fee"],
            "origin_stair_fee": origin_stair["fee"],
            "destination_stair_fee": destination_stair["fee"],
        },
        "total_fare": total_fare,
        "manual_check": manual_check,
        "reason": (
            "정상 계산"
            if not manual_check
            else "6층 이상 계단 작업 등 별도 확인 필요"
        ),
    }


# ============================================================
# 9. 전체 견적 통합 실행
# ============================================================

def estimate(
    origin_address,
    destination_address,
    item_counts,
    service_type="VEHICLE_ONLY",
    total_weight_kg=None,
    item_dimensions=None,
    origin_floor=1,
    origin_elevator=True,
    destination_floor=1,
    destination_elevator=True,
):
    """차량 추천, 거리 조회, 운임 계산을 순서대로 실행합니다.

    주의:
        이 함수는 차량 추천 및 운임 계산을 수행합니다.
        실제 기사 검색/매칭은 별도의 matching.py에서 처리해야 합니다.
    """
    # 1) 물품 기준 차량 매칭
    vehicle_result = pick_vehicle(
        item_counts=item_counts,
        total_weight_kg=total_weight_kg,
        item_dimensions=item_dimensions,
    )

    vehicle_type = vehicle_result["vehicle_type"]
    if vehicle_type is None:
        return {
            "success": False,
            "vehicle": vehicle_result,
            "reason": "적합한 차량을 찾지 못했습니다.",
        }

    if (
        vehicle_result.get("weight_check")
        and vehicle_result["weight_check"]["passed"] is False
    ):
        return {
            "success": False,
            "vehicle": vehicle_result,
            "reason": "차량 허용 적재 중량 초과",
        }

    # 2) 출발지/도착지 거리 계산
    try:
        distance_result = get_distance(
            origin_address,
            destination_address,
        )
    except (requests.RequestException, ValueError, KeyError) as error:
        return {
            "success": False,
            "vehicle": vehicle_result,
            "reason": f"거리 계산 실패: {error}",
        }

    distance_km = distance_result["distance_km"]

    # 3) 거리 및 작업 조건별 운임 계산
    fare_result = calc_fare(
        vehicle_type=vehicle_type,
        distance_km=distance_km,
        service_type=service_type,
        origin_floor=origin_floor,
        origin_elevator=origin_elevator,
        destination_floor=destination_floor,
        destination_elevator=destination_elevator,
    )

    # 4) 수동 확인 조건 통합
    manual_check = (
        vehicle_result["manual_check"]
        or fare_result.get("manual_check", False)
    )

    # 5) 최종 견적 결과
    return {
        "success": fare_result["success"] and not manual_check,
        "vehicle": {
            "vehicle_type": vehicle_type,
            "manual_check": vehicle_result["manual_check"],
            "reason": vehicle_result["reason"],
            "dimension_check": vehicle_result["dimension_check"],
            "weight_check": vehicle_result["weight_check"],
        },
        "distance": {
            "origin": origin_address,
            "destination": destination_address,
            "distance_km": distance_km,
            "duration_minutes": distance_result["duration_minutes"],
            "source": distance_result["source"],
            "estimated": distance_result["estimated"],
        },
        "fare": fare_result,
        "total_fare": fare_result["total_fare"],
        "manual_check": manual_check,
        "warning": (
            distance_result.get("warning")
            if distance_result["estimated"]
            else None
        ),
    }


# ============================================================
# 10. Streamlit 운송 신청 데이터 연결용 어댑터
# ============================================================

def estimate_request(request):
    """transport_request.py에서 저장한 request 딕셔너리를 estimate에 연결합니다.

    Streamlit 입력 키(item_s_count 등)를 운임 계산에서 사용하는
    등급 키(S, M, L, XL, XXL)로 변환합니다.
    """
    if not isinstance(request, dict):
        raise ValueError("운송 신청 데이터는 딕셔너리여야 합니다.")

    item_counts = {
        grade: request.get(f"item_{grade.lower()}_count", 0)
        for grade in ITEM_GRADES
    }

    # 화면의 helper_option 값이 SERVICE_RULES 키와 다를 수 있어
    # 현재 확인 가능한 NONE만 VEHICLE_ONLY로 변환합니다.
    helper_option = request.get("helper_option", "NONE")
    service_type = (
        "VEHICLE_ONLY" if helper_option == "NONE" else helper_option
    )

    return estimate(
        origin_address=request.get("origin_address", ""),
        destination_address=request.get("dest_address", ""),
        item_counts=item_counts,
        service_type=service_type,
        total_weight_kg=request.get("total_weight_kg"),
        item_dimensions=request.get("item_dimensions"),
        origin_floor=request.get("origin_floor", 1),
        origin_elevator=request.get("origin_has_elevator", True),
        destination_floor=request.get("dest_floor", 1),
        destination_elevator=request.get("dest_has_elevator", True),
    )
