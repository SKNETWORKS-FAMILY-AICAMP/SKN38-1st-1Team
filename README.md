
<p align="center">
  <img src="assets/logo_main.png" alt="짐니 JIMNI" width="320">
</p>

<h3 align="center">짐 옮길 땐, 짐니! — 생활 물류·소형 화물 운송 중개 플랫폼</h3>

소비자에게는 투명하고 편리한 운송 경험을, 기사에게는 효율적인 일감 확보와 업무 관리 환경을 제공하는 생활 물류 중개 플랫폼입니다.

특히 여성·1인 가구가 안심하고 서비스를 이용할 수 있도록 **사전 운임 동의, 기사 정보 확인, 운송 상태 조회**를 핵심 기능으로 기획했습니다.

> 본 서비스는 학습용 시연 프로젝트입니다. 기사 정보는 시연용 가상 데이터이며, 실제 운송 요청·결제는 이루어지지 않습니다.

---

## 💡 Why JIMNI?

- **간편한 예약:** 운송 조건 입력부터 기사 추천·예약 조회까지 연결된 흐름
- **운임 투명성:** 거리·물품·작업 옵션을 반영한 운임 확인과 예약 전 동의
- **안심 서비스:** 기사 정보 및 운송 진행 상태 확인
- **효율적인 중개:** 운송 조건에 맞는 기사 추천과 자동 배정
- **데이터 활용:** 공공데이터 기반 지역별 화물차 등록 현황 시각화

---

## How It Works

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

---
## Fare Guide

다마스·라보·1톤 차량별 거리 구간 운임과 추가 작업 비용을 안내합니다.

[운임 기준표 자세히 보기](docs/fare_table.md)

## Key Features

| 기능 | 설명 |
|:---|:---|
| 운송 신청 | 카카오 API 기반 주소 검색과 위치 확인, 물품·운송 조건 입력 |
| 운임 계산 및 차량 추천 | 도로 이동 거리, 물품 크기, 층수, 추가 인력을 반영한 예상 운임 계산 |
| 기사 추천 및 매칭 | 운송 조건과 지역을 고려한 시연용 기사 추천 및 예약 확정 시 자동 배정 |
| 사전 운임 동의 | 최종 운임과 작업 조건 확인, 조건 변경 시 운임 재계산 및 재동의 |
| 예약 조회 및 평가 | 예약번호와 연락처로 예약 조회, 상태 확인 및 운송 완료 후 별점 평가 |
| 웹 알림 | 기사 매칭 완료 알림 및 예약 상태별 안내 메시지 |
| FAQ | 팀에서 작성한 FAQ 29건에 대한 카테고리별 조회 및 키워드 검색 |
| 화물차 등록 현황 | 국토교통부 공공데이터 기반 버블 지도 및 시군구별 상세 조회 |

---

## Tech Stack

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" />
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL" />
  <img src="https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white" alt="Git" />
  <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" />
</p>

<p align="center">
  <sub>Visualization: pydeck · API: 국토교통부 OpenAPI, Kakao Local API, 카카오모빌리티 길찾기 API, Kakao Maps JavaScript SDK</sub>
</p>

---

## Data Collection & Processing

### Data Sources

| 데이터 | 제공 기관 | 활용 목적 |
|:---|:---|:---|
| [자동차등록현황보고](https://stat.molit.go.kr/portal/cate/statMetaView.do?hRsId=58) | 국토교통부 | 시도·시군구별 영업용 화물차 등록대수 수집 및 시각화 |
| [전국 화물자동차 운송사업자 표준데이터](https://www.data.go.kr/data/15129433/standard.do) | 공공데이터포털 | 운송사업자 데이터 조사 및 지역명 표기 참고 |

두 자료는 집계 기준이 다르므로 차량대수를 합산하지 않았습니다. 운송사업자 표준데이터는 현재 서비스의 기사 매칭 및 등록대수 집계에 직접 사용하지 않습니다.

### Data Collection

국토교통부 자동차등록현황 OpenAPI를 활용하여 지역별 영업용 화물차 등록 통계를 수집했습니다.

| 항목 | 내용 |
|:---|:---|
| 기준월 | 2026년 9월 |
| 수집 대상 | 시도·시군구별 영업용 화물차 등록대수 |
| 전국 등록대수 | **472,852대** |
| 시군구 데이터 | **263건** |
| 데이터 저장 | MySQL |

### Data Preprocessing

수집한 JSON 데이터를 Pandas로 정제한 뒤 MySQL에 저장했습니다.

1. 전체 자동차 등록 통계에서 영업용 화물차 데이터 추출
2. 시도별 소계 행을 제외하여 중복 집계 방지
3. 시도·시군구 지역명 표기 정리
4. 누락값 및 중복 데이터 검증
5. 시군구 합계와 공식 통계 대조
6. 전처리 결과 CSV 생성 및 MySQL 적재

동일 기준월 데이터의 중복 저장을 방지하고, 오류 발생 시 트랜잭션을 롤백하도록 구현했습니다.

### Data Utilization

수집한 등록 통계는 MySQL `registration_stats` 테이블에 저장하고 Streamlit에서 조회합니다.

- 전국 영업용 화물차 등록대수 표시
- 시도별 버블 지도 시각화
- 시도 선택 시 시군구별 상세 통계 조회
- 통계 기준월 및 데이터 출처 표시

버블의 위치에는 **SGIS 행정구역 경계 데이터**를 이용해 계산한 시도별 대표 좌표를 사용했습니다.

> 화물차 등록대수는 공식 등록 통계로, 실제 운행 차량이나 실시간 배차 가능한 기사 수와는 다릅니다.

자세한 수집 및 갱신 과정은 [데이터 파이프라인 문서](docs/registration_pipeline.md)에서 확인할 수 있습니다.

---

## Database Design & ERD

짐니는 MySQL 기반의 관계형 데이터베이스를 사용하며, 총 **7개 테이블과 9개 외래 키(FK) 관계**로 구성되어 있습니다.

<p align="center">
  <img src="docs/erd_final_1team.png" alt="짐니 데이터베이스 ERD" width="1000" />
</p>

<p align="center">
  <a href="docs/erd_original.png">초기설계 ERD</a> ·
  <a href="sql/schema.sql">테이블 생성 SQL</a>
</p>

### Database Tables

| 테이블 | 역할 |
|:---|:---|
| `regions` | 시도·시군구 지역 정보 |
| `data_sources` | 공공데이터 출처 및 수집 정보 |
| `registration_stats` | 지역별 영업용 화물차 등록 통계 |
| `drivers` | 시연용 기사 및 차량 정보 |
| `bookings` | 예약, 운송 조건, 기사 배정 및 평가 |
| `fare_rules` | 차종별 운임 규칙 |
| `faqs` | 자주 묻는 질문 및 답변 |

### 사전 운임 동의 기록

예약 확정 시 동의한 조건과 운임 기록을 `bookings` 테이블에 저장하는 구조입니다.

| 컬럼 | 타입 | 역할 |
|:---|:---|:---|
| `agreed_at` | `DATETIME` | 운임 및 운송 조건 동의 시각 |
| `agreement_hash` | `CHAR(64)` | 동의 조건과 운임의 SHA-256 해시 |
| `agreed_terms` | `JSON` | 동의 당시 조건·운임 내역 스냅샷 |

합의한 운임은 `estimated_fare`에 저장합니다.

테이블 생성 SQL은 [`sql/schema.sql`](sql/schema.sql), 기존 DB용 컬럼 추가 SQL은 [`sql/bookings_agreement_columns.sql`](sql/bookings_agreement_columns.sql)에서 확인할 수 있습니다.

---

## Project Structure

<details>
<summary><b>폴더 구조 자세히 보기</b></summary>

```text
SKN38-1st-1Team/
├── app.py                 # Streamlit 진입점
├── pages/                 # 웹페이지
│   ├── 0_Home.py
│   ├── 1_Delivery_Request.py
│   ├── 2_Driver_Matching.py
│   ├── 3_Booking_Lookup.py
│   ├── 4_Truck_Map.py
│   ├── 5_FAQ.py
│   ├── 6_Booking.py
│   ├── 7_Fare_Table.py
│   └── 8_Driver_Login.py
├── services/              # 비즈니스 로직
│   ├── __init__.py
│   ├── db.py
│   ├── transport_request.py
│   ├── fare.py
│   ├── fare_table.py
│   ├── fare_rules_db.py
│   ├── settlement.py
│   ├── matching.py
│   ├── booking.py
│   ├── agreement.py
│   ├── assignment.py
│   ├── notifications.py
│   ├── booking_lookup.py
│   ├── kakao_local.py
│   ├── truck_stats.py
│   ├── truck_map.py
│   ├── driver_map.py
│   ├── driver_sim.py
│   ├── faq.py
│   └── ui.py
├── scripts/               # 데이터 수집 및 DB 적재
├── data/                  # 원본·전처리 데이터 및 FAQ
├── sql/                   # DB 스키마 및 쿼리
├── docs/                  # ERD 및 프로젝트 문서
├── assets/                # 로고·캐릭터·일러스트
├── .streamlit/            # Streamlit 설정
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

</details>

---

## Meet the Team

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


