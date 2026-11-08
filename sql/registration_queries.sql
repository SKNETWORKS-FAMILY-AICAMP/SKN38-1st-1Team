-- ============================================================
-- 영업용 화물차 등록대수 조회 SQL (pages/4_Truck_Map.py용)
-- 데이터: scripts/update_registration_db.py 가 적재
-- registration_stats 에는 시군구 행만 저장 (시도 '계' 소계 행은 저장하지 않음)
--   → 시도 합계는 아래 2번처럼 GROUP BY 로 계산
-- ============================================================

-- 1. 최신 기준월
SELECT MAX(base_month) AS latest_month
FROM registration_stats
WHERE vehicle_kind = '화물' AND usage_type = '영업용';


-- 2. 최신 기준월 · 시도별 영업용 화물차 등록대수 (지도 시도 단위)
SELECT r.sido_name,
       SUM(s.vehicle_count) AS truck_count,
       s.base_month
FROM registration_stats s
JOIN regions r ON r.region_id = s.region_id
WHERE s.vehicle_kind = '화물'
  AND s.usage_type = '영업용'
  AND s.base_month = (SELECT MAX(base_month) FROM registration_stats
                      WHERE vehicle_kind = '화물' AND usage_type = '영업용')
GROUP BY r.sido_name, s.base_month
ORDER BY truck_count DESC;


-- 3. 최신 기준월 · 시군구별 영업용 화물차 등록대수 (지도 시군구 단위)
SELECT r.region_id,
       r.sido_name,
       r.sigungu_name,
       r.adm_code,
       s.vehicle_count AS truck_count,
       s.base_month
FROM registration_stats s
JOIN regions r ON r.region_id = s.region_id
WHERE s.vehicle_kind = '화물'
  AND s.usage_type = '영업용'
  AND s.base_month = (SELECT MAX(base_month) FROM registration_stats
                      WHERE vehicle_kind = '화물' AND usage_type = '영업용')
ORDER BY r.sido_name, r.sigungu_name;


-- 4. 화면 하단 출처 표시용 (최신 기준월의 수집 출처)
SELECT d.dataset_name, d.provider, d.portal_url, d.base_month, d.retrieved_at
FROM data_sources d
WHERE d.source_id = (
    SELECT s.source_id FROM registration_stats s
    WHERE s.vehicle_kind = '화물' AND s.usage_type = '영업용'
    ORDER BY s.base_month DESC LIMIT 1
);
