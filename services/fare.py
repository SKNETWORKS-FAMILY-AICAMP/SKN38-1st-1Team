"""참고 운임 계산 및 차량 추천 로직."""

import os
import math
import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

HEADERS = {
    "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
}

# ============================================================
# 1. 기본 설정
# ============================================================

MAX_DISTANCE_KM = 100
LOADING_MINUTES = 30
REQUEST_TIMEOUT = 10

VEHICLE_ORDER = ["다마스", "라보", "1톤"]

# ============================================================
# 2. 물품 등급 기준 테이블
# ============================================================

# 단위: cm, kg
# 세 변의 합과 최대 무게를 기준으로 물품 등급 분류

ITEM_GRADES = {
    "S": {
        "max_size_sum": 140,
        "max_weight": 10,
        "description": "소형 박스, 소형 수납함"
    },
    "M": {
        "max_size_sum": 180,
        "max_weight": 20,
        "description": "의자, 협탁, 소형 가구"
    },
    "L": {
        "max_size_sum": 220,
        "max_weight": 30,
        "description": "책장, 소형 책상, 소형 가전"
    },
    "XL": {
        "max_size_sum": 260,
        "max_weight": 50,
        "description": "책상, 세탁기, 침대 프레임"
    },
    "XXL": {
        "max_size_sum": 320,
        "max_weight": 80,
        "description": "대형 책상, 침대 프레임, 소파"
    }
}

# ============================================================
# 3. 차량별 적재함 규격 테이블
# ============================================================
# 단위: cm, kg
#
# max_length : 물품 최장변 허용 기준
# max_width  : 물품 폭 허용 기준
# max_height : 적재 높이 허용 기준
# max_payload: 차량 등록상 허용 적재 중량
#
# None은 아직 확인되지 않은 제원

VEHICLE_SPECS = {
    "다마스": {
        "max_length": 160,
        "max_width": 110,
        "max_height": 110,
        "max_payload": None
    },
    "라보": {
        "max_length": 220,
        "max_width": 140,
        "max_height": None,
        "max_payload": None
    },
    "1톤": {
        "max_length": 311,
        "max_width": 160,
        "max_height": None,
        "max_payload": None
    }
}

# ============================================================
# 4. 차량별 등급 수용 수량 테이블
# ============================================================
# 단위: 개
# 단일 등급 물품을 기준으로 한 추천 수량
# 0    : 적재 비추천
# None : 수용 가능 수량 미확정

VEHICLE_CAPACITY = {
    "다마스": {
        "S": 6,
        "M": 3,
        "L": 0,
        "XL": 0,
        "XXL": 0
    },
    "라보": {
        "S": 15,
        "M": 8,
        "L": 2,
        "XL": 0,
        "XXL": 0
    },
    "1톤": {
        "S": 30,
        "M": 12,
        "L": 6,
        "XL": None,
        "XXL": None
    }
}

# ============================================================
# 5. 거리별 기본 운임 테이블
# ============================================================

# 단위: 원
# 차량 1대 / 편도 / 상하차 미포함
#
# 거리 구간:
# D1: 0~5km
# D2: 5~10km
# D3: 10~20km
# D4: 20~30km
# D5: 30~50km
# D6: 50~70km
# D7: 70~100km

FARE_RULES = [
    {
        "code": "D1",
        "min": 0,
        "max": 5,
        "fares": {
            "다마스": 30000,
            "라보": 30000,
            "1톤": 35000
        }
    },
    {
        "code": "D2",
        "min": 5,
        "max": 10,
        "fares": {
            "다마스": 36000,
            "라보": 36000,
            "1톤": 42000
        }
    },
    {
        "code": "D3",
        "min": 10,
        "max": 20,
        "fares": {
            "다마스": 43000,
            "라보": 43000,
            "1톤": 50000
        }
    },
    {
        "code": "D4",
        "min": 20,
        "max": 30,
        "fares": {
            "다마스": 50000,
            "라보": 50000,
            "1톤": 60000
        }
    },
    {
        "code": "D5",
        "min": 30,
        "max": 50,
        "fares": {
            "다마스": 60000,
            "라보": 60000,
            "1톤": 70000
        }
    },
    {
        "code": "D6",
        "min": 50,
        "max": 70,
        "fares": {
            "다마스": 72000,
            "라보": 72000,
            "1톤": 84000
        }
    },
    {
        "code": "D7",
        "min": 70,
        "max": 100,
        "fares": {
            "다마스": 90000,
            "라보": 90000,
            "1톤": 105000
        }
    }
]


# ============================================================
# 6. 기사 및 추가 작업자 요금 테이블
# ============================================================

# 단위: 원 / 편도
#
# VEHICLE_ONLY : 기사 운전만
# DRIVER_HELP  : 기사 상하차 도움
# WORKER_1     : 추가 작업자 1명
# WORKER_2     : 추가 작업자 2명

SERVICE_RULES = {
    "VEHICLE_ONLY": {
        "name": "기사 운전만",
        "fee": 0
    },
    "DRIVER_HELP": {
        "name": "기사 상하차 도움",
        "fee": 40000
    },
    "WORKER_1": {
        "name": "추가 작업자 1명",
        "fee": 70000
    },
    "WORKER_2": {
        "name": "추가 작업자 2명",
        "fee": 140000
    }
}

# ============================================================
# 7. 계단 작업 요금 테이블
# ============================================================

# 단위: 원 / 장소
#
# 출발지와 도착지를 각각 계산
# 엘리베이터 이용 시 계단 요금 없음

STAIR_RULES = {
    1: 0,
    2: 10000,
    3: 20000,
    4: 30000,
    5: 40000
}
MAX_STAIR_FLOOR = 5

# ============================================================
# 8. 주소 및 거리 계산 기능
# ============================================================

def geocode(address):
    """
    카카오 주소 검색 API를 이용해 주소를 좌표로 변환합니다.
    반환값:
        (longitude, latitude)
    """
    if not KAKAO_REST_API_KEY:
        raise ValueError("KAKAO_REST_API_KEY가 설정되지 않았습니다.")

    response = requests.get(
        "https://dapi.kakao.com/v2/local/search/address.json",
        headers=HEADERS,
        params={"query": address},
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()
    documents = response.json().get("documents", [])

    if not documents:
        raise ValueError(f"주소를 찾을 수 없습니다: {address}")

    location = documents[0]["address"]

    return (
        float(location["x"]),
        float(location["y"])
    )

def _kakao_route(origin, destination):
    """
    카카오 자동차 길찾기 API로 실제 자동차 주행거리를 조회.

    origin, destination:
        (longitude, latitude)
    반환값:
        거리(km), 소요시간(분)
    """

    response = requests.get(
        "https://apis-navi.kakaomobility.com/v1/directions",
        headers=HEADERS,
        params={
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "priority": "RECOMMEND"
        },
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()
    data = response.json()
    routes = data.get("routes", [])

    if not routes or routes[0].get("result_code") != 0:
        raise ValueError("자동차 길찾기 경로를 찾을 수 없습니다.")

    summary = routes[0]["summary"]

    distance_km = summary["distance"] / 1000
    duration_minutes = summary["duration"] / 60
    return distance_km, duration_minutes

def get_distance(origin_address, destination_address):
    """
    출발지와 도착지의 자동차 주행거리 및 소요시간을 조회합니다.
    카카오 길찾기 실패 시 자동 견적을 중단합니다.
    """

    origin = geocode(origin_address)
    destination = geocode(destination_address)

    distance, duration = _kakao_route(origin, destination)

    return {
    "distance_km": round(distance, 2),
    "duration_minutes": round(duration, 1),
    "source": "Kakao Mobility",
    "estimated": False
}

# ============================================================
# 9. 물품 입력값 검증 기능
# ============================================================

def validate_items(item_counts):
    """
    등급별 물품 수량을 검증합니다.
    입력 예시:
        {
            "S": 3,
            "M": 2,
            "L": 0,
            "XL": 0,
            "XXL": 0
        }
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
# 10. 단일 등급 차량 매칭 기능
# ============================================================

def _match_single_grade(grade, count):
    """
    단일 등급 물품의 수량을 기준으로 차량을 추천합니다.
    작은 차량부터 순서대로 확인합니다.
    """
    for vehicle in VEHICLE_ORDER:

        capacity = VEHICLE_CAPACITY[vehicle][grade]
        if capacity is None or capacity == 0:
            continue

        if count <= capacity:

            return {
                "vehicle_type": vehicle,
                "manual_check": False,
                "reason": "등급별 수량 기준으로 차량 추천"
            }

    # XL, XXL은 1톤 우선 추천
    if grade in ["XL", "XXL"]:

        return {
            "vehicle_type": "1톤",
            "manual_check": True,
            "reason": "대형 물품의 실제 적재 규격 및 고정 상태 확인 필요"
        }

    return {
        "vehicle_type": None,
        "manual_check": True,
        "reason": "수량 기준에 맞는 차량 없음"
    }


# ============================================================
# 11. 혼합 등급 차량 매칭 기능
# ============================================================

def _match_mixed_grade(counts):
    """
    여러 등급의 물품이 섞인 경우 차량을 추천합니다.

    계산 방식:
        등급별 물품 수량 / 차량별 등급 수용량

    각 등급의 추정 적재 비율을 합산하여
    100% 이하인 가장 작은 차량을 추천합니다.
    """

    # XL, XXL 물품이 있으면 1톤 우선 추천
    if counts["XL"] > 0 or counts["XXL"] > 0:

        return {
            "vehicle_type": "1톤",
            "manual_check": True,
            "reason": "대형 물품 포함: 실제 적재 규격 확인 필요"
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
                "estimated_utilization": round(utilization, 2)
            }

    return {
        "vehicle_type": None,
        "manual_check": True,
        "reason": "혼합 물품의 적재량이 차량 수용 기준 초과"
    }


# ============================================================
# 12. 실제 물품 크기 검증 기능
# ============================================================

def _check_dimensions(vehicle_type, item_dimensions):
    """
    차량 적재함 규격과 개별 물품의 크기를 비교합니다.

    입력 예시:
        [
            {"length": 120, "width": 50, "height": 40},
            {"length": 90, "width": 60, "height": 50}
        ]

    세 변 중 가장 긴 변을 최장변,
    두 번째 변을 폭,
    가장 짧은 변을 높이로 비교합니다.
    """

    specs = VEHICLE_SPECS[vehicle_type]

    if item_dimensions is None:

        return {
            "passed": None,
            "reason": "개별 물품 크기 미입력"
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
            item.get("height")
        ]

        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value <= 0
            for value in dimensions
        ):
            raise ValueError(f"{index}번 물품의 크기를 확인해 주세요.")

        longest, second, shortest = sorted(
            dimensions,
            reverse=True
        )

        if longest > specs["max_length"]:
            errors.append(f"{index}번 물품 최장변 초과")

        if second > specs["max_width"]:
            errors.append(f"{index}번 물품 폭 초과")

        if specs["max_height"] is not None:

            if shortest > specs["max_height"]:
                errors.append(f"{index}번 물품 높이 초과")

    return {
        "passed": len(errors) == 0,
        "reason": errors if errors else "규격 기준 통과"
    }


# ============================================================
# 13. 차량 매칭 통합 기능
# ============================================================

def pick_vehicle(
    item_counts,
    total_weight_kg=None,
    item_dimensions=None
):
    """
    물품 수량, 실제 크기, 전체 무게를 기준으로 차량을 선택합니다.

    수량 기준으로 차량을 우선 추천하고
    실제 크기 및 중량 확인 결과를 함께 반환합니다.

    미확인 제원이 있으면 manual_check=True를 반환합니다.
    """

    counts = validate_items(item_counts)

    active_grades = [
        grade
        for grade, count in counts.items()
        if count > 0
    ]

    # 1) 단일 등급 / 혼합 등급 구분
    if len(active_grades) == 1:

        grade = active_grades[0]

        result = _match_single_grade(
            grade,
            counts[grade]
        )

    else:

        result = _match_mixed_grade(counts)

    vehicle = result["vehicle_type"]

    if vehicle is None:

        return {
            **result,
            "dimension_check": None,
            "weight_check": None
        }

    # 2) 전체 물품 무게 검증
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
                "reason": "차량 등록 적재 중량 미확인"
            }

            result["manual_check"] = True

        elif total_weight_kg > max_payload:

            weight_check = {
                "passed": False,
                "reason": "차량 허용 적재 중량 초과"
            }

            result["vehicle_type"] = None
            result["manual_check"] = True

        else:

            weight_check = {
                "passed": True,
                "reason": "허용 적재 중량 이내"
            }

    else:

        weight_check = {
            "passed": None,
            "reason": "전체 물품 무게 미입력"
        }

        result["manual_check"] = True

    # 3) 개별 물품 크기 검증
    dimension_check = _check_dimensions(
        vehicle,
        item_dimensions
    )

    if dimension_check["passed"] is not True:
        result["manual_check"] = True

    # 4) 최종 매칭 결과
    return {
        **result,
        "dimension_check": dimension_check,
        "weight_check": weight_check
    }


# ============================================================
# 14. 거리 구간별 기본 운임 계산
# ============================================================

def calc_base_fare(vehicle_type, distance_km):
    """
    차량 종류와 주행거리를 기준으로 기본 운임을 계산합니다.

    거리 구간의 경계값은 다음 구간에 포함합니다.

    예:
        5km  -> D1
        5km 초과 -> D2
        10km -> D2
        10km 초과 -> D3
        100km -> D7
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
            "reason": "100km 초과: 별도 견적 필요"
        }

    for rule in FARE_RULES:

        if rule["min"] <= distance_km <= rule["max"]:

            # 정확히 경계값이면 앞 구간에 포함
            if distance_km == rule["min"] and rule["min"] > 0:

                previous_rule = FARE_RULES[
                    FARE_RULES.index(rule) - 1
                ]

                return {
                    "fare": previous_rule["fares"][vehicle_type],
                    "distance_code": previous_rule["code"],
                    "manual_check": False,
                    "reason": "거리 구간별 기본 운임"
                }

            return {
                "fare": rule["fares"][vehicle_type],
                "distance_code": rule["code"],
                "manual_check": False,
                "reason": "거리 구간별 기본 운임"
            }

    raise ValueError("거리 구간을 확인할 수 없습니다.")


# ============================================================
# 15. 기사 및 추가 작업자 비용 계산
# ============================================================

def calc_service_fee(service_type):
    """
    서비스 유형에 따른 기사 및 작업자 비용을 계산합니다.
    """

    if service_type not in SERVICE_RULES:
        raise ValueError("올바르지 않은 서비스 유형입니다.")

    rule = SERVICE_RULES[service_type]

    return {
        "service_type": service_type,
        "service_name": rule["name"],
        "fee": rule["fee"]
    }


# ============================================================
# 16. 계단 작업 비용 계산
# ============================================================

def calc_stair_fee(floor, has_elevator):
    """
    출발지 또는 도착지의 계단 작업 비용을 계산합니다.

    엘리베이터가 있으면 0원
    2~5층은 층수별 추가요금
    6층 이상은 별도 협의
    """

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
            "reason": "엘리베이터 이용"
        }

    if floor > MAX_STAIR_FLOOR:

        return {
            "fee": None,
            "manual_check": True,
            "reason": "6층 이상: 별도 협의"
        }

    return {
        "fee": STAIR_RULES[floor],
        "manual_check": False,
        "reason": f"{floor}층 계단 작업"
    }


# ============================================================
# 17. 최종 운임 계산 기능
# ============================================================

def calc_fare(
    vehicle_type,
    distance_km,
    service_type="VEHICLE_ONLY",
    origin_floor=1,
    origin_elevator=True,
    destination_floor=1,
    destination_elevator=True
):
    """
    기본 운임 + 기사/작업자 비용 + 계단 비용을 계산합니다.

    반환값:
        기본 운임
        서비스 비용
        출발지 계단 비용
        도착지 계단 비용
        최종 예상 운임
    """

    # 1) 기본 운임
    base = calc_base_fare(
        vehicle_type,
        distance_km
    )

    if base["fare"] is None:

        return {
            "success": False,
            "total_fare": None,
            "reason": base["reason"]
        }

    # 2) 서비스 비용
    service = calc_service_fee(service_type)

    # 3) 출발지 계단 비용
    origin_stair = calc_stair_fee(
        origin_floor,
        origin_elevator
    )

    # 4) 도착지 계단 비용
    destination_stair = calc_stair_fee(
        destination_floor,
        destination_elevator
    )

    # 5) 수동 확인이 필요한 조건 확인
    manual_check = (
        origin_stair["manual_check"]
        or destination_stair["manual_check"]
    )

    # 6) 총액 계산
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
            "destination_stair_fee": destination_stair["fee"]
        },

        "total_fare": total_fare,
        "manual_check": manual_check,

        "reason": (
            "정상 계산"
            if not manual_check
            else "6층 이상 계단 작업 등 별도 확인 필요"
        )
    }


# ============================================================
# 18. 전체 견적 통합 실행 기능
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
    destination_elevator=True
):
    """
    전체 견적 실행 함수입니다.

    실행 순서:
        1. 물품 등급 및 수량 확인
        2. 차량 매칭
        3. 출발지 / 도착지 거리 계산
        4. 거리별 기본 운임 계산
        5. 서비스 및 계단 추가요금 계산
        6. 최종 견적 결과 반환
    """

    # --------------------------------------------------------
    # 1) 물품 기준 차량 매칭
    # --------------------------------------------------------

    vehicle_result = pick_vehicle(
        item_counts=item_counts,
        total_weight_kg=total_weight_kg,
        item_dimensions=item_dimensions
    )

    vehicle_type = vehicle_result["vehicle_type"]

    if vehicle_type is None:

        return {
            "success": False,
            "vehicle": vehicle_result,
            "reason": "적합한 차량을 찾지 못했습니다."
        }

    # 중량 초과 등으로 차량 매칭이 실패한 경우
    if (
        vehicle_result.get("weight_check")
        and vehicle_result["weight_check"]["passed"] is False
    ):

        return {
            "success": False,
            "vehicle": vehicle_result,
            "reason": "차량 허용 적재 중량 초과"
        }

    # --------------------------------------------------------
    # 2) 출발지 / 도착지 거리 계산
    # --------------------------------------------------------

    try:
        distance_result = get_distance(
            origin_address,
            destination_address
        )

    except (requests.RequestException, ValueError, KeyError) as error:
        return {
            "success": False,
            "reason": f"거리 계산 실패: {error}"
        }
    distance_km = distance_result["distance_km"]

    # --------------------------------------------------------
    # 3) 거리 및 작업 조건별 운임 계산
    # --------------------------------------------------------

    fare_result = calc_fare(
        vehicle_type=vehicle_type,
        distance_km=distance_km,
        service_type=service_type,
        origin_floor=origin_floor,
        origin_elevator=origin_elevator,
        destination_floor=destination_floor,
        destination_elevator=destination_elevator
    )

    # --------------------------------------------------------
    # 4) 수동 확인 조건 통합
    # --------------------------------------------------------

    manual_check = (
    vehicle_result["manual_check"]
    or fare_result.get("manual_check", False)
)
    # --------------------------------------------------------
    # 5) 최종 견적 결과
    # --------------------------------------------------------

    return {
        "success": fare_result["success"] and not manual_check,

        "vehicle": {
            "vehicle_type": vehicle_type,
            "manual_check": vehicle_result["manual_check"],
            "reason": vehicle_result["reason"],
            "dimension_check": vehicle_result["dimension_check"],
            "weight_check": vehicle_result["weight_check"]
        },

        "distance": {
            "origin": origin_address,
            "destination": destination_address,
            "distance_km": distance_km,
            "duration_minutes": distance_result["duration_minutes"],
            "source": distance_result["source"],
            "estimated": distance_result["estimated"]
        },

        "fare": fare_result,

        "total_fare": fare_result["total_fare"],

        "manual_check": manual_check,

        "warning": (
            distance_result.get("warning")
            if distance_result["estimated"]
            else None
        )
    }