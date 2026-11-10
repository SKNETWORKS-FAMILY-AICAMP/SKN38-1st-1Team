"""요금표 조회 (fare_rules 테이블) — 홈과 FAQ의 '요금표 보기'가 공통으로 사용.

운임 '계산' 로직은 services/fare.py (운임 담당) 소관이며 여기서는 등록된 기준을 표로 보여주기만 한다.
fare_rules가 비어 있으면 빈 DataFrame을 돌려주고, 화면에서 '요금표 확정 전'으로 안내한다.
"""

"""운송 차량 및 운임 기준 데이터"""

# 기본 설정
MAX_DISTANCE_KM = 100
LOADING_MINUTES = 30
REQUEST_TIMEOUT = 10

VEHICLE_ORDER = ["다마스", "라보", "1톤"]

# 물품 등급
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

# 차량별 적재함 규격
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

# 차량별 적재 가능 수량
VEHICLE_CAPACITY = {
    "다마스": {
        "S": 6, "M": 3, "L": 0, "XL": 0, "XXL": 0
    },
    "라보": {
        "S": 15, "M": 8, "L": 2, "XL": 0, "XXL": 0
    },
    "1톤": {
        "S": 30, "M": 12, "L": 6, "XL": None, "XXL": None
    }
}

# 거리별 기본 운임
FARE_RULES = [
    {
        "code": "D1",
        "min": 0,
        "max": 5,
        "fares": {"다마스": 30000, "라보": 30000, "1톤": 35000}
    },
    {
        "code": "D2",
        "min": 5,
        "max": 10,
        "fares": {"다마스": 36000, "라보": 36000, "1톤": 42000}
    },
    {
        "code": "D3",
        "min": 10,
        "max": 20,
        "fares": {"다마스": 43000, "라보": 43000, "1톤": 50000}
    },
    {
        "code": "D4",
        "min": 20,
        "max": 30,
        "fares": {"다마스": 50000, "라보": 50000, "1톤": 60000}
    },
    {
        "code": "D5",
        "min": 30,
        "max": 50,
        "fares": {"다마스": 60000, "라보": 60000, "1톤": 70000}
    },
    {
        "code": "D6",
        "min": 50,
        "max": 70,
        "fares": {"다마스": 72000, "라보": 72000, "1톤": 84000}
    },
    {
        "code": "D7",
        "min": 70,
        "max": 100,
        "fares": {"다마스": 90000, "라보": 90000, "1톤": 105000}
    }
]

# 기사 및 추가 작업자 요금
SERVICE_RULES = {
    "VEHICLE_ONLY": {"name": "기사 운전만", "fee": 0},
    "DRIVER_HELP": {"name": "기사 상하차 도움", "fee": 40000},
    "WORKER_1": {"name": "추가 작업자 1명", "fee": 70000},
    "WORKER_2": {"name": "추가 작업자 2명", "fee": 140000}
}

# 계단 작업 요금
STAIR_RULES = {
    -2: 20000,
    -1: 10000,
    1: 0,
    2: 10000,
    3: 20000,
    4: 30000,
    5: 40000
}

MAX_STAIR_FLOOR = 5