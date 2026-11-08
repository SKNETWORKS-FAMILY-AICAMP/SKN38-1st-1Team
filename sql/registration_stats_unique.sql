-- ============================================================
-- [권장·선택] registration_stats 중복 방지 UNIQUE 인덱스
-- 스크립트(update_registration_db.py)는 이 인덱스가 없어도 중복을 넣지 않지만,
-- DB 차원에서도 막으려면 스키마 확정 후 한 번만 실행하세요.
--
-- 실행 전 확인: 이미 같은 이름/구성의 인덱스가 있는지
--   SHOW INDEX FROM registration_stats;
-- 실행 전 확인: 기존 데이터에 중복이 없는지 (결과가 0행이어야 함)
--   SELECT base_month, region_id, vehicle_kind, usage_type, COUNT(*)
--   FROM registration_stats
--   GROUP BY base_month, region_id, vehicle_kind, usage_type
--   HAVING COUNT(*) > 1;
-- ============================================================

ALTER TABLE registration_stats
    ADD UNIQUE KEY uq_registration_stats_month_region_kind_usage
        (base_month, region_id, vehicle_kind, usage_type);
