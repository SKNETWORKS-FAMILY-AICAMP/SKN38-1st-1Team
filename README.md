# 🚚 생활 물류·소형 화물 운송 중개 플랫폼


생활 속에서 발생하는 **소형 이사·단건 운송 수요와 개인 운송사업자를 연결하는 양면 플랫폼**입니다.

소비자에게는 투명하고 편리한 운송 경험을, 기사에게는 효율적인 일감 확보와 업무 관리 환경을 제공합니다.

특히 여성·1인 가구가 안심하고 서비스를 이용할 수 있도록 **사전 확정 운임, 기사 정보 확인, 운송 상태 조회**를 핵심 기능으로 기획했습니다.

## 🎯 프로젝트 목표

- **합리적인 운송:** 운송 조건에 따른 차량 추천과 예상 운임 제공
- **투명한 거래:** 소비자·기사 간 최종 운임 사전 합의 및 추가요금 분쟁 예방
- **안심 서비스:** 기사 정보 및 운송 진행 상태 확인
- **효율적인 중개:** 기사 매칭과 수수료·정산 정보 제공
- **공공데이터 활용:** 지역별 영업용 화물차 등록 현황 시각화

## 🛠️ 핵심 기능

| 기능 | 주요 내용 |
|---|---|
| 📦 운송 신청 및 운임 계산 | 출발·도착지, 층수, 엘리베이터, 물품 크기·수량, 인력 옵션 등을 반영한 차량 추천 및 예상 운임 |
| 🚚 기사·차량 조회 및 매칭 | 출발지 기준 기사 추천, 차량 종류·평점·완료 건수 조회 |
| 🤝 사전 확정 운임제 | 최종 운임과 작업 조건 사전 합의, 조건 변경 시 재동의 |
| 💰 수수료 및 정산 | 플랫폼 수수료율, 운송 확정 금액, 기사 예상 정산액 공개 |
| 🛡️ 안심 운송 | 사업자 확인 정보, 운송 상태 조회, 운송 완료 후 평가 |
| 📋 예약 및 조회 | 로그인 없이 예약 신청, 예약번호 발급 및 추가 본인 확인 후 조회 |
| ❓ FAQ | 요금·예약·취소·파손·분실·안전 관련 안내 및 검색 |
| 🗺️ 화물차 현황 지도 | 국토교통부 공공데이터 기반 지역별 영업용 화물차 등록대수 시각화 |

※ 위 내용은 구현 목표이며, 개발 상황에 따라 일부 기능이 변경될 수 있습니다.

## 💻 기술 스택

| 구분 | 기술 |
|---|---|
| Language | Python |
| Data Processing | Pandas |
| Database | MySQL |
| Web Application | Streamlit |
| Visualization | Plotly |
| Public Data | 국토교통부 통계누리 OpenAPI |
| External API | 카카오 로컬 API (도입 검토) |
| Collaboration | Git, GitHub |

## 🗂️ 프로젝트 폴더 구조

```text
SKN38-1st-1Team/
│
├── app.py                    # Streamlit 메인 화면
├── pages/                    # 기능별 화면
│   ├── 1_Delivery_Request.py # 운송 신청 및 예상 운임
│   ├── 2_Driver_Matching.py  # 기사·차량 조회 및 매칭
│   ├── 3_Booking_Lookup.py   # 예약 조회 및 운송 상태
│   ├── 4_Truck_Map.py        # 지역별 화물차 현황
│   └── 5_FAQ.py              # FAQ
│
├── services/                 # 운임 계산·매칭·정산 로직
├── data/                     # 수집 및 전처리 데이터
├── scripts/                  # 데이터 수집·전처리 코드
├── sql/                      # MySQL 관련 파일
├── docs/                     # ERD 및 프로젝트 문서
│
├── requirements.txt          # Python 라이브러리 목록
├── .env.example              # 환경변수 예시
├── .gitignore                # Git 업로드 제외 설정
└── README.md
```

## 📊 데이터 및 ERD

### 데이터 활용

- **국토교통부 자동차등록현황보고:** 지역별 영업용 화물차 등록 통계
- **운송 요금 기준:** 차종·거리·적재량·인력 옵션별 참고 운임
- **서비스 운영 데이터:** 기사·차량 정보, 운송 요청, 예약 및 정산
- **FAQ:** 서비스 이용 안내 및 관련 외부 자료

공공데이터는 Python/Pandas로 수집·전처리하고 MySQL에 저장하여 Streamlit에서 활용할 계획입니다.

공공데이터의 영업용 화물차 등록대수와 플랫폼 내 실제 이용 가능 기사 수는 구분하여 표시합니다.

### ERD



![ERD](docs/erd.png)


## 🚀 실행 방법

### 1. GitHub 저장소 Clone

```bash
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN38-1st-1Team.git
cd SKN38-1st-1Team
```

또는 VS Code에서 `Clone Git Repository`를 이용합니다.

### 2. 가상환경 생성 및 활성화

Windows PowerShell 기준:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. 라이브러리 설치

```powershell
python -m pip install -r requirements.txt
```

### 4. 환경변수 설정

`.env.example`을 복사해 `.env`를 만들고 필요한 API 키와 DB 연결 정보를 입력합니다.

```powershell
Copy-Item .env.example .env
```

`.env`는 GitHub에 업로드하지 않습니다.

### 5. Streamlit 실행

```powershell
python -m streamlit run app.py
```

접속 주소: http://localhost:8501

## 🤝 GitHub 협업

팀원 4명이 `main` 브랜치를 기준으로 기능별 파일을 분담하여 개발합니다.

**작업 순서:** `Pull → 개발 → Commit → Pull → Push`

- 작업 전 최신 코드 Pull
- 담당 파일 위주로 수정
- 공통 파일 수정 시 팀원에게 공유
- API 키, DB 비밀번호, `.env`, `.venv` 업로드 금지
- 충돌 발생 시 강제 Push 금지

### 팀 GitHub

https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN38-1st-1Team

---

**SK Networks Family AI Camp · SKN38 1st Project · 1Team**
