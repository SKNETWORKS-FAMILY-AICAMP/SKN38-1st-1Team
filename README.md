<p align="center">
  <img src="assets/logo_main.png" alt="짐니 JIMNI" width="320">
</p>

<h3 align="center">짐 옮길 땐, 짐니! — 생활 물류·소형 화물 운송 중개 플랫폼</h3>


소비자에게는 투명하고 편리한 운송 경험을, 기사에게는 효율적인 일감 확보와 업무 관리 환경을 제공합니다.

특히 여성·1인 가구가 안심하고 서비스를 이용할 수 있도록 **사전 확정 운임, 기사 정보 확인, 운송 상태 조회**를 핵심 기능으로 기획했습니다.

> 본 서비스는 학습용 시연 서비스입니다. 기사 정보는 시연용 가상 데이터이며, 실제 운송 요청·결제는 이루어지지 않습니다.

## 🎯 프로젝트 목표
- **간편한 예약:** 운송 조건 입력부터 기사 추천·예약 조회까지 연결된 흐름
- **운임 투명성:** 거리·물품·작업 옵션을 반영한 운임 확인과 예약 전 동의
- **안심 서비스:** 기사 정보 및 운송 진행 상태 확인
- **효율적인 중개:** 기사 매칭과 수수료·정산 정보 제공
- **데이터 활용:** 공공데이터 기반 지역별 영업용 화물차 등록 현황 시각화


## 🧭 서비스 이용 방법

<p align="center">
  <img src="docs/readme_2.png" alt="짐니 이용 방법" width="1000" />
</p>

| 단계 | 주요 기능 |
|:---|:---|
| **01 · 정보 입력** | 카카오 주소·장소 검색, 출발지·도착지 선택 및 물품·작업 조건 입력 |
| **02 · 매칭 결과** | 도로 이동 거리, 예상 운임 및 적합한 차량 확인 |
| **03 · 기사님 선택** | 조건에 맞는 시연용 기사 추천·선택 |
| **04 · 예약하기** | 최종 운임·작업 조건 확인, 동의 및 예약 확정 |
| **05 · 예약 완료** | 기사 자동 배정 알림, 예약번호 발급 및 예약 조회 |

<details>
<summary><b>서비스 흐름도 자세히 보기</b></summary>

<p align="center">
  <img src="docs/serviceflow.png" alt="짐니 서비스 흐름도" width="900" />
</p>
</details>

## ✨ 주요 기능

| 기능 | 설명 |
|:---|:---|
| 운송 신청 | 카카오 API를 통한 주소 검색 및 위치 확인, 물품·운송 조건 입력 |
| 운임 계산 및 차량 추천 | 실제 도로 이동 거리, 물품 크기, 층수, 추가 인력을 반영한 예상 운임 계산 |
| 기사 추천 및 매칭 | 운송 조건과 지역을 고려한 시연용 가상 기사 추천 및 예약 확정 시 자동 배정 |
| 사전 운임 동의 | 최종 운임과 작업 조건 확인, 조건 변경 시 운임 재계산 및 재동의 |
| 예약 조회 및 평가 | 예약번호와 연락처로 예약 조회, 운송 상태 확인 및 완료 후 별점 평가 |
| FAQ | 팀에서 작성한 FAQ 29건에 대한 카테고리별 조회 및 키워드 검색 |
| 지역별 화물차 현황 | 국토교통부 공공데이터 기반 시도별 버블 지도 및 시군구 상세 통계 |
| 웹 알림 | 기사 매칭 완료 알림과 예약 상태에 따른 안내 메시지 |

## 📊 데이터 수집 및 전처리

짐니는 국토교통부 공공데이터를 수집하고 전처리하여 지역별 영업용 화물차 등록 현황을 시각화합니다.

### 데이터 수집

- **데이터 출처:** 국토교통부 자동차등록현황 OpenAPI
- **기준월:** 2026년 9월
- **수집 대상:** 시도·시군구별 영업용 화물차 등록대수
- **전국 등록대수:** 472,852대
- **시군구 데이터:** 263건

### 전처리 내용

1. 전체 자동차 등록 통계에서 영업용 화물차 데이터 추출
2. 시도별 소계 행 제거 및 중복 집계 방지
3. 시도·시군구 지역명 정리
4. 누락값 및 중복 데이터 검증
5. 시군구별 합계와 공식 통계 비교
6. 전처리 데이터를 MySQL에 저장

동일 기준월의 중복 저장을 방지하고, 오류 발생 시 트랜잭션을 롤백하여 데이터 정합성을 유지합니다.

자세한 과정은 [데이터 수집 및 전처리 문서](docs/registration_pipeline.md)에서 확인할 수 있습니다.

### 데이터 활용

수집한 데이터는 `registration_stats` 테이블에 저장되며, Streamlit의 지역별 화물차 현황 페이지에서 활용됩니다.

- 전국 영업용 화물차 등록대수 조회
- 시도별 버블 지도 시각화
- 시도 선택 시 시군구별 상세 통계 조회
- 기준월 및 데이터 출처 표시

버블 위치는 SGIS 행정구역 경계 데이터에서 계산한 시도별 대표 좌표를 활용합니다.

> 화물차 등록대수는 공식 등록 통계이며, 실제 운행 중인 차량 수나 실시간 배차 가능한 기사 수를 의미하지 않습니다.

---

## 🗂️ ERD (데이터베이스 설계)

생활 물류·소형 화물 운송 중개 플랫폼의 데이터베이스는
총 **7개 테이블과 9개 외래 키(FK) 관계**로 구성되어 있습니다.

### 📌 ERD 전체 구조

![ERD - 생활 물류 운송 중개 플랫폼](docs/erd_final_1team.png)

### 🎨 테이블 색상 구분

| 색상 | 테이블 | 역할 |
|---|---|---|
| 🔵 파란색 | `regions` | 시도·시군구 지역 정보 |
| 🟢 초록색 | `data_sources`, `registration_stats` | 공공데이터 출처 및 화물차 등록 통계 |
| 🟣 보라색 | `drivers`, `bookings` | 기사 정보 및 운송 예약 |
| 🟡 노란색 | `fare_rules`, `faqs` | 운임 산정 기준 및 자주 묻는 질문 |

### 🔗 주요 테이블 관계

- `regions` → 지역 계층, 기사 활동 지역, 출발지·도착지 관리
- `data_sources` → `registration_stats` : 공공데이터 출처 관리
- `regions` → `registration_stats` : 지역별 화물차 등록 통계
- `fare_rules` → `drivers`, `bookings` : 차종별 운임 기준
- `drivers` → `bookings` : 기사별 운송 예약

## 💻 기술 스택

| 구분 | 기술 |
|:---|:---|
| Language | Python |
| Web Framework | Streamlit |
| Data Processing | Pandas |
| Database | MySQL, PyMySQL |
| Visualization | pydeck |
| Public Data | 국토교통부 자동차등록현황 OpenAPI |
| Location API | Kakao Local API |
| Route API | 카카오모빌리티 길찾기 API |
| Map SDK | Kakao Maps JavaScript SDK |
| Collaboration | Git, GitHub |

## 📁 프로젝트 구조

<details>
<summary><b>폴더 구조 자세히 보기</b></summary>

```text
SKN38-1st-1Team/
│
├── app.py                 # Streamlit 진입점
│
├── pages/                 # 웹페이지
│   ├── 0_Home.py
│   ├── 1_Delivery_Request.py
│   ├── 2_Driver_Matching.py
│   ├── 3_Booking_Lookup.py
│   ├── 4_Truck_Map.py
│   ├── 5_FAQ.py
│   ├── 6_Booking.py
│   └── 7_Fare_Table.py
│
├── services/              # 주요 비즈니스 로직
│   ├── fare.py
│   ├── fare_table.py
│   ├── matching.py
│   ├── booking.py
│   ├── agreement.py
│   ├── assignment.py
│   ├── notifications.py
│   ├── booking_lookup.py
│   ├── kakao_local.py
│   ├── truck_stats.py
│   ├── truck_map.py
│   ├── faq.py
│   └── ui.py
│
├── scripts/               # 공공데이터 수집 및 DB 적재
├── data/                  # 원본·전처리 데이터 및 FAQ
├── sql/                   # DB 스키마 및 SQL
├── docs/                  # ERD 및 프로젝트 문서
├── assets/                # 로고·캐릭터·일러스트
├── .streamlit/            # Streamlit 설정
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

</details>

---


### 🤝 사전 확정 운임 동의 기록 (`bookings`)

| 컬럼 | 타입 | 내용 |
|---|---|---|
| `agreed_at` | DATETIME | 소비자가 동의한 시각 |
| `agreement_hash` | CHAR(64) | 동의한 조건 + 운임 전체의 SHA-256 해시 |
| `agreed_terms` | JSON | 동의 당시 조건(주소·일시·층수·물품·인력)과 운임 내역 스냅샷 |

합의 운임은 `estimated_fare`에 저장됩니다. 이미 만들어 둔 DB에는 [`sql/bookings_agreement_columns.sql`](sql/bookings_agreement_columns.sql)을 한 번 실행합니다.

### 📊 공공데이터 연동

국토교통부 OpenAPI를 통해 지역별 영업용 화물차 등록대수를 수집하고,
Pandas로 전처리한 데이터를 MySQL에 저장합니다.

- **기준 데이터:** 2026년 9월 (전국 영업용 화물차 472,852대)
- **수집 대상:** 영업용 화물차 등록대수
- **수집 주기:** 국토교통부 월별 통계 갱신 기준
- **데이터베이스:** MySQL
- **중복 방지:** 동일 기준월 데이터 중복 저장 방지
- **오류 처리:** 트랜잭션 ROLLBACK으로 기존 데이터 보호

등록대수는 실제 운행 중이거나 지금 예약 가능한 차량 수가 아닙니다.

데이터 수집 및 갱신 과정은
[`docs/registration_pipeline.md`](docs/registration_pipeline.md)에서 확인할 수 있습니다.

DB 테이블 생성 SQL은 [`sql/schema.sql`](sql/schema.sql)에 있습니다.




<h2>👥 팀원 소개</h2>

<p align="center">
  <b>SK Networks Family AI Camp 38기 · 1팀</b>
</p>

<table align="center">
  <tr>
    <td align="center" width="140">
      <img src="assets/jimni2.png" width="110" height="110"><br>
      <b>김예준</b><br>
      <sub>역할</sub><br>
      <sub>담당 기능</sub>
    </td>
    <td align="center" width="140">
      <img src="assets/jimni6.png" width="110" height="110"><br>
      <b>이지우</b><br>
      <sub>역할</sub><br>
      <sub>담당 기능</sub>
    </td>
    <td align="center" width="140">
      <img src="assets/jimni4.png" width="110" height="110"><br>
      <b>정흥기</b><br>
      <sub>역할</sub><br>
      <sub>담당 기능</sub>
    </td>
    <td align="center" width="140">
      <img src="assets/jimni3.png" width="110" height="110"><br>
      <b>최웅</b><br>
      <sub>역할</sub><br>
      <sub>담당 기능</sub>
    </td>
  </tr>
</table>


---
