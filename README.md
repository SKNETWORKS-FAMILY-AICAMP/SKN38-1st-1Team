# 🚚 생활 물류·소형 화물 운송 중개 플랫폼 (서비스명 미정)

여성·1인 가구가 안심하고 이용할 수 있도록 소비자와 용달·화물차 기사를 연결하는 플랫폼입니다.
SKN38 1st 1Team 프로젝트 (데이터 수집·전처리 → ERD 설계 → MySQL 구축 → Streamlit 구현)

## 핵심 기능

| # | 기능 | 내용 |
|---|------|------|
| 1 | 운송 조건 입력 및 참고 운임 계산 | 출발지·도착지, 층수·엘리베이터, 물품 크기(S/M/L/XL)·수량, 희망 일시, 인력 옵션 → 거리·소요시간, 차량 추천, 예상 운임 |
| 2 | 용달 기사·차량 조회 및 매칭 | 출발지 기준 기사 추천, 차량·평점·완료 건수·거리 표시, 지역별 화물차 현황 지도 |
| 3 | 사전 확정 운임제 | 최종 운임 합의·저장, 일방적 추가요금 변경 제한, 조건 변경 시 양측 재동의 |
| 4 | 투명 수수료 및 기사 정산 | 수수료율 공개, 확정 금액·수수료·기사 예상 정산액 표시 |
| 5 | 여성·1인 가구 안심 운송 | 사업자 확인 배지, 확인 기사 우선 추천, 운송 상태 확인, 완료 후 평가 |
| 6 | 예약 및 조회 | 로그인 없이 이름·전화번호로 예약, 예약번호 + 추가 확인으로 조회 |
| 7 | FAQ | 요금 / 예약·취소 / 파손·분실 / 기사·안전 카테고리, 키워드 검색, 출처 링크 |

## 기술 스택

Python · Pandas · MySQL · Streamlit · GitHub · 국토교통부 OpenAPI · 카카오 로컬 API(추후 검토)

## 폴더 구조

```text
SKN38-1st-1Team/
├── app.py                 # Streamlit 메인 페이지
├── pages/                 # 기능별 페이지 (팀원별 담당)
│   ├── 1_Delivery_Request.py
│   ├── 2_Driver_Matching.py
│   ├── 3_Booking_Lookup.py
│   ├── 4_Truck_Map.py
│   └── 5_FAQ.py
├── services/              # 공통 비즈니스 로직 (운임 계산, 매칭, 운임 확정, 정산)
├── data/
│   ├── raw/               # 수집한 원본 공공데이터
│   └── processed/         # Pandas 전처리 데이터
├── scripts/               # OpenAPI 수집 및 전처리 코드
├── sql/                   # MySQL 스키마·쿼리
├── docs/                  # ERD, 데이터 출처, 기획 문서
├── requirements.txt
├── .env.example           # 환경변수 이름 예시 (실제 값 X)
└── README.md
```

## 팀원별 담당

| 파일 | 담당 |
|------|------|
| `app.py` | (미정) |
| `pages/1_Delivery_Request.py` · `services/fare.py` | (미정) |
| `pages/2_Driver_Matching.py` · `services/matching.py`, `agreement.py`, `settlement.py` | (미정) |
| `pages/3_Booking_Lookup.py` | (미정) |
| `pages/4_Truck_Map.py` · `scripts/` | (미정) |
| `pages/5_FAQ.py` | (미정) |

> main 브랜치 하나에서 작업하므로 **자기 담당 파일만 수정**하고, 작업 전 항상 `git pull`을 먼저 실행해 주세요.

## 실행 방법

Python 3.13 기준 (3.10 이상 권장)

### 1. 저장소 Clone

```bash
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN38-1st-1Team.git
cd SKN38-1st-1Team
```

### 2. 가상환경 생성 및 활성화

```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

> PowerShell에서 실행 정책 오류가 나면: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 3. 패키지 설치

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 환경변수 설정

`.env.example`을 복사해 `.env`를 만들고 값을 입력합니다. (`.env`는 GitHub에 올라가지 않습니다)

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

### 5. Streamlit 실행

```bash
python -m streamlit run app.py
```

브라우저에서 http://localhost:8501 이 열립니다.

## 협업 규칙

- 작업 시작 전 `git pull`, 작업 후 담당 파일만 `git add` → `commit` → `push`
- `.env`, `.venv/`, API 키, DB 비밀번호는 절대 커밋하지 않기
- 새 패키지를 추가하면 `requirements.txt`에 반영하고 팀원에게 공유
- 페이지에는 화면 코드만, 계산·조회 로직은 `services/`에 작성
