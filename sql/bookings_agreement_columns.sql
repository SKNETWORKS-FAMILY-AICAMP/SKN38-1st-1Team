-- ============================================================
-- 사전 확정 운임 동의 증거 컬럼 (이미 만들어 둔 DB에 한 번만 실행)
-- 새로 만드는 DB는 sql/schema.sql에 이미 포함되어 있어 실행하지 않아도 됩니다.
--
-- 실행 전 확인: 이미 추가되어 있는지 (결과가 0행이어야 실행)
--   SHOW COLUMNS FROM bookings LIKE 'agree%';
--
-- 모두 NULL 허용이라 기존 예약 데이터는 그대로이며 값은 NULL로 남습니다.
-- 이 컬럼이 없는 DB에서도 예약 저장(services/booking.py)은 동의 기록만 빼고 정상 동작합니다.
-- ============================================================

ALTER TABLE bookings
    ADD COLUMN agreed_at DATETIME NULL COMMENT '사전 운임 동의 시각',
    ADD COLUMN agreement_hash CHAR(64) NULL COMMENT '동의한 조건+운임 해시',
    ADD COLUMN agreed_terms JSON NULL COMMENT '동의 당시 조건·운임 스냅샷';
