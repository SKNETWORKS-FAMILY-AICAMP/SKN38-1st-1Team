# 영업용 화물차 등록대수 수집 파이프라인

국토교통부 OpenAPI → Python 수집 → Pandas 전처리 → MySQL 저장 → 최신 기준월 자동 갱신

| 파일 | 역할 |
|---|---|
| `scripts/molit_api.py` | API 호출, 최신 공표 기준월 확인 |
| `scripts/preprocess_registration.py` | 화물·영업용 추출, 소계 제외, 검증, CSV 저장 |
| `scripts/update_registration_db.py` | MySQL 저장·중복 방지·트랜잭션 갱신 |
| `scripts/run_update_registration.bat` | Windows 작업 스케줄러용 실행 파일 |
| `sql/registration_queries.sql` | 지도 페이지용 조회 SQL |
| `sql/registration_stats_unique.sql` | (권장) 중복 방지 UNIQUE 인덱스 |

## 1. API 확인 결과 (2026-11-08 실제 호출)

- **출처:** 국토교통부 통계누리, 자동차등록현황보고 → 자동차등록대수현황 시도별 (`form_id=5498`, `style_num=2`)
- **요청:** `GET https://stat.molit.go.kr/portal/openapi/service/rest/getList.do?key=…&form_id=5498&style_num=2&start_dt=YYYYMM&end_dt=YYYYMM`
  - 인증 방식은 쿼리 파라미터 `key`입니다. `.env`의 `MOLIT_API_KEY`에서 읽습니다.
  - http, https 모두 동작합니다. 키가 평문으로 전송되지 않도록 코드는 https를 사용합니다.
- **응답:** JSON. `result_status.status_code` 값은 다음과 같습니다.
  - `INFO-000` 정상
  - `INFO-200` 데이터 없음
  - `INFO-100` 인증키 오류
  - `ERROR-335` 5년 초과 요청
  - ⚠️ "데이터 없음"과 "인증키 오류"도 HTTP 500으로 옵니다. 그래서 HTTP 코드가 아니라 본문의 `status_code`로 판단합니다.
- **페이지네이션:** 없습니다. 요청 기간 전체가 한 번에 반환되며, 최대 5년까지 요청할 수 있습니다.
- **최신 공표 기준월:** `202609` (202610, 202611은 `INFO-200`)
- **지역 단위:** 통계표 이름은 "시도별"이지만 실제로는 **시군구 행을 제공**합니다.
  - 202609 기준 279행 = 16개 시도의 '계'(소계) 16행 + 시군구 263행 (전국 합계 행은 없음)
- **차종:** 승용 / 승합 / 화물 / 특수 / 총계
- **용도:** 관용 / 자가용 / 영업용 / 계
- **값 컬럼명:** `"{차종}>{용도}"` 형식 (예: `화물>영업용`). 단위는 대.
- **누락·정합성:** NULL 0건, 시군구 중복 0건, 모든 시도에서 시군구 합계와 '계' 값이 일치하고, 차종·용도 합계도 일치합니다.
- `result_data.cert_id`는 인증키와 같은 값이므로 저장하거나 출력하지 않습니다.

### 202609 영업용 화물차 등록대수 (실제 API 값)

| 시도 | 대수 | 시도 | 대수 |
|---|---:|---|---:|
| 경기 | 139,236 | 충남 | 20,379 |
| 서울 | 58,486 | 전북 | 16,930 |
| 전남광주 | 36,340 | 충북 | 16,275 |
| 부산 | 36,320 | 대전 | 12,667 |
| 인천 | 35,725 | 울산 | 10,552 |
| 경남 | 28,053 | 강원 | 9,403 |
| 경북 | 25,311 | 제주 | 4,415 |
| 대구 | 20,750 | 세종 | 2,010 |
| **전국** | **472,852** | | |

## 2. ERD와의 점검 결과

`registration_stats`가 시군구 단위로 설계된 것은 실제 API와 **맞습니다.** 다만 다음 사항을 확인해야 합니다.

1. **`sql/schema.sql` 기준으로 맞춘 사항**
   - PK(`region_id`, `source_id`, `stat_id`)에 AUTO_INCREMENT가 없습니다. 그래서 스크립트가 트랜잭션 안에서 `MAX + 1`로 번호를 매깁니다 (`FOR UPDATE`로 잠금).
   - `data_sources.region_id`가 NOT NULL입니다. 전국 단위 출처이므로 `regions`에 **'전국'(region_level `NATION`) 행**을 하나 만들어 참조합니다. 스키마는 바꾸지 않습니다.
   - 기준월은 `base_month DATE`이므로 `2026-09-01`처럼 해당 월 1일로 저장합니다. `retrieved_at DATE`는 수집일로 저장합니다.
   - UNIQUE 제약이 없으므로 중복 방지는 스크립트가 담당합니다. DB 차원에서도 막으려면 `registration_stats_unique.sql`을 실행하세요.
   - 실행할 때마다 `information_schema`로 실제 컬럼과 자료형을 다시 확인하고, 다르면 쓰기 전에 중단합니다.
2. **API에 행정구역 코드가 없습니다.** `regions.adm_code`는 NULL로 저장됩니다.
   - 지도에서 코드로 연결해야 한다면, 행정표준코드 파일로 따로 매핑해야 합니다.
3. **2026년 7월부터 광주와 전남이 `전남광주` 하나로 합쳐졌습니다.** 202606까지는 '광주'와 '전남'이 따로 있습니다.
   - `regions`에 광주·전남이 따로 들어 있다면, 202609 데이터는 `전남광주` 지역으로 새로 추가됩니다.
4. **공식 통계에 남아 있는 비표준 행**이 있습니다. 공식 '계'에 포함된 값이므로 그대로 저장합니다.
   - 경기 `부천시`와 `화성시`: 구 단위 행과 함께 있지만, 겹치는 소계가 아니라 별도 잔여분입니다.
   - 충북 `청원군`, 경북 `군위군`
   - 군위군은 대구에도 있으므로, 지도에서 경계 데이터와 연결할 때 주의해야 합니다.
5. **시도명 표기:** API 약칭(서울, 경기, 전남광주 …)을 그대로 씁니다.
   - 기존 `regions`에 "서울특별시" 같은 공식 명칭이 있어도 자동으로 매칭됩니다 (`SIDO_ALIASES`).
6. **중복 방지:** 스크립트가 직접 막습니다. DB 차원에서도 막으려면 `sql/registration_stats_unique.sql`을 실행하세요 (선택).

### 저장 값

| 테이블 | 저장 내용 |
|---|---|
| `registration_stats` | 시군구 행만 저장. `vehicle_kind='화물'`, `usage_type='영업용'`. 시도 '계' 행은 저장하지 않으며, 시도 합계는 SQL로 계산합니다. |
| `regions` | 없는 지역만 추가. `region_level` = `NATION` / `SIDO` / `SIGUNGU`. 시군구의 `parent_region_id`는 시도 `region_id` |
| `data_sources` | 기준월마다 1행. `source_code = MOLIT_REG_5498_YYYYMM`, `region_id` = '전국' 행 |

팀에서 `region_level` 값을 다르게 정했다면 `update_registration_db.py` 상단 설정만 수정하면 됩니다.

### 함께 있는 엑셀 파일 (`data/processed/`)

| 파일 | 내용 | 확인 결과 |
|---|---|---|
| `화물차_시군구별_등록현황_202609.xlsx` | 같은 통계를 통계누리에서 엑셀로 내려받은 버전 (시군구·소계·총계) | 시군구 263건이 API와 **모두 일치**, 총계 472,852대도 같음. API 장애 시 대체·대조용으로 사용 가능 |
| `전국화물운송사업자.xlsx` | 전국화물자동차운송사업자 표준데이터 (2026-11-07): 사업소 16,168곳, 보유 차량 151,289대 | **등록대수 통계와는 다른 데이터**이므로 섞어 쓰면 안 됨. 완전히 같은 중복 행 50건, 운영 중지(N) 15건, 도로명주소 결측 604건 |

## 3. 실행 방법

먼저 `.env`에 `MOLIT_API_KEY`, `MOLIT_API_URL`, `DB_*` 값을 입력합니다. 프로젝트 루트에서 가상환경을 활성화한 뒤 실행합니다.

```powershell
python scripts/molit_api.py                     # API 최신 기준월 확인
python scripts/preprocess_registration.py       # 수집·전처리 → data/raw, data/processed 저장
python scripts/update_registration_db.py --check     # DB 연결·스키마 점검 (쓰기 없음)
python scripts/update_registration_db.py --dry-run   # 수집·전처리·지역 매핑 확인 (쓰기 없음)
python scripts/update_registration_db.py             # 새 기준월이면 저장, 아니면 변경 없음
```

- 로그는 `logs/update_registration_db.log`에 남습니다 (`*.log`는 GitHub 업로드에서 제외).
- 종료 코드: `0` = 저장 또는 변경 없음, `1` = 오류
- 오류가 나면 ROLLBACK하므로 기존 데이터는 유지됩니다.
- API, 전처리, 검증 단계에서 실패하면 DB에 아무것도 쓰지 않습니다.

## 4. Windows 작업 스케줄러 등록 (직접 등록)

통계는 보통 다음 달 중순에 공표됩니다. 매월 20일과 말일에 두 번 실행하도록 등록하는 것을 권장합니다. 새 기준월이 없으면 아무것도 바꾸지 않으므로 여러 번 실행해도 안전합니다.

1. 작업 스케줄러 → **기본 작업 만들기**
2. 트리거: **매월**, 날짜 20일 (필요하면 트리거를 하나 더 추가)
3. 동작: **프로그램 시작**
   - 프로그램: `C:\Jiwoo\SKNS\SKN38-1st-1team\SKN38-1st-1Team\scripts\run_update_registration.bat`
   - 시작 위치: `C:\Jiwoo\SKNS\SKN38-1st-1team\SKN38-1st-1Team`
4. 속성 → **"예약된 시작 시간을 놓친 경우 가능한 대로 빨리 작업 시작"** 체크

명령어로 등록하려면 다음과 같이 합니다.

```powershell
schtasks /Create /TN "SKN38_UpdateRegistration" /SC MONTHLY /D 20 /ST 10:00 /TR "C:\Jiwoo\SKNS\SKN38-1st-1team\SKN38-1st-1Team\scripts\run_update_registration.bat"
```

⚠️ 로컬 MySQL을 쓰는 경우, 실행 시각에 **PC가 켜져 있고 MySQL 서비스가 실행 중**이어야 합니다. 꺼져 있으면 실패 로그만 남고, 다음 실행 때 다시 시도합니다.

## 5. 지도 페이지(`pages/4_Truck_Map.py`)에서 사용하는 방법

`sql/registration_queries.sql`의 2번(시도별) 또는 3번(시군구별) 쿼리를 사용하세요.

```python
import os

import pandas as pd
import pymysql
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

QUERY_SIDO = """
SELECT r.sido_name, SUM(s.vehicle_count) AS truck_count, s.base_month
FROM registration_stats s
JOIN regions r ON r.region_id = s.region_id
WHERE s.vehicle_kind = '화물' AND s.usage_type = '영업용'
  AND s.base_month = (SELECT MAX(base_month) FROM registration_stats
                      WHERE vehicle_kind = '화물' AND usage_type = '영업용')
GROUP BY r.sido_name, s.base_month
ORDER BY truck_count DESC
"""

@st.cache_data(ttl=3600)
def load_truck_counts_by_sido() -> pd.DataFrame:
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"), port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"), charset="utf8mb4",
    )
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(QUERY_SIDO)
            return pd.DataFrame(cur.fetchall())
    finally:
        conn.close()
```

- 화면에는 **"영업용 화물차 등록대수(국토교통부, 기준월 YYYY-MM)"**와 **"플랫폼 이용 가능 기사 수(drivers)"**를 서로 다른 지표로 구분해 표시해야 합니다.
- 출처 문구에는 4번 쿼리 결과(`dataset_name`, `provider`, `portal_url`, `base_month`)를 사용할 수 있습니다.
