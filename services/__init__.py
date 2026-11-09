"""페이지에서 공통으로 사용하는 비즈니스 로직 모음.

모듈 구성
- db.py                : MySQL 연결 (.env)
- transport_request.py : 운송 요청 입력값 정의·검증, session_state 키
- truck_stats.py       : 지역별 영업용 화물차 등록대수 조회 (sql/registration_queries.sql 재사용)
- booking_lookup.py    : 예약 조회 (예약번호 + 연락처 확인), 운송 완료 후 평점 저장
- fare_rules_db.py     : 요금표 조회 (MySQL fare_rules)
- kakao_local.py       : 카카오 주소 검색·위치 지도 (운송 신청)
- fare_table.py        : 운임 계산 기준표 (예준님)
- fare.py       : 거리·물품 기반 참고 운임 계산, 차량 추천 (구현 예정)
- matching.py   : 출발지 기준 기사 검색·추천 (구현 예정)
- agreement.py  : 사전 확정 운임 합의·변경 재동의 (구현 예정)
- settlement.py : 플랫폼 수수료 및 기사 정산액 계산 (구현 예정)

페이지(pages/)에는 화면 코드만 두고, 계산·조회 로직은 이 폴더에 작성합니다.
"""
