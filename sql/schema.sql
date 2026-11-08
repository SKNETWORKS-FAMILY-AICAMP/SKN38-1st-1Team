CREATE TABLE `bookings` (
	`booking_id`	BIGINT	NOT NULL,
	`customer_name`	VARCHAR(50)	NOT NULL	COMMENT '예약자명',
	`customer_phone`	VARCHAR(20)	NOT NULL	COMMENT '연락처',
	`origin_address`	VARCHAR(255)	NOT NULL	COMMENT '출발주소',
	`origin_lat`	DECIMAL(9, 6)	NULL	COMMENT '출발위도',
	`origin_lng`	DECIMAL(9, 6)	NULL	COMMENT '출발경도',
	`origin_floor`	INT	NOT NULL	DEFAULT 1	COMMENT '출발층수',
	`origin_has_elevator`	BOOLEAN	NOT NULL	DEFAULT TRUE	COMMENT '출발엘리베이터',
	`dest_address`	VARCHAR(255)	NOT NULL	COMMENT '도착주소',
	`dest_lat`	DECIMAL(9, 6)	NULL	COMMENT '도착위도',
	`dest_lng`	DECIMAL(9, 6)	NULL	COMMENT '도착경도',
	`dest_floor`	INT	NOT NULL	DEFAULT 1	COMMENT '도착층수',
	`dest_has_elevator`	BOOLEAN	NOT NULL	DEFAULT TRUE	COMMENT '도착엘리베이터',
	`item_s_count`	INT	NOT NULL	DEFAULT 0	COMMENT '소형물품수',
	`item_m_count`	INT	NOT NULL	DEFAULT 0	COMMENT '중형물품수',
	`item_l_count`	INT	NOT NULL	DEFAULT 0	COMMENT '대형물품수',
	`item_xl_count`	INT	NOT NULL	DEFAULT 0	COMMENT '특대형물품수',
	`helper_option`	VARCHAR(20)	NOT NULL	DEFAULT 'NONE'	COMMENT '인력옵션',
	`distance_km`	DECIMAL(10, 2)	NULL	COMMENT '거리',
	`estimated_minutes`	INT	NULL	COMMENT '소요시간',
	`scheduled_at`	DATETIME	NOT NULL	COMMENT '운송일시',
	`estimated_fare`	INT	NOT NULL	COMMENT '예상요금',
	`commission_rate`	DECIMAL(5, 2)	NULL	COMMENT '플랫폼 수수료율(%)',
	`origin_region_id`	INT	NOT NULL,
	`dest_region_id`	INT	NOT NULL,
	`fare_rule_id`	INT	NOT NULL,
	`driver_id`	INT	NOT NULL,
	`commission_amount`	INT	NULL,
	`driver_payout`	INT	NULL,
	`status`	VARCHAR(20)	NOT NULL	DEFAULT 'BOOKED',
	`status_updated_at`	DATETIME	NULL,
	`rating`	INT	NULL,
	`created_at`	DATETIME	NOT NULL	DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE `drivers` (
	`driver_id`	INT	NOT NULL,
	`nickname`	VARCHAR(30)	NOT NULL	COMMENT '기사명',
	`base_lat`	DECIMAL(9, 6)	NOT NULL	COMMENT '차고지위도',
	`base_lng`	DECIMAL(9, 6)	NOT NULL	COMMENT '차고지경도',
	`verification_status`	VARCHAR(15)	NOT NULL	DEFAULT 'NOT_VERIFIED'	COMMENT '사업자확인',
	`is_active`	BOOLEAN	NOT NULL	DEFAULT TRUE	COMMENT '배정가능',
	`created_at`	DATETIME	NOT NULL	DEFAULT CURRENT_TIMESTAMP	COMMENT '등록일시',
	`source_id`	INT	NOT NULL	COMMENT '출처번호',
	`region_id`	INT	NOT NULL,
	`fare_rule_id`	INT	NOT NULL
);

CREATE TABLE `fare_rules` (
	`fare_rule_id`	INT	NOT NULL,
	`vehicle_type`	VARCHAR(50)	NOT NULL	COMMENT '차종',
	`max_load_kg`	INT	NOT NULL	COMMENT '최대적재량',
	`base_fare`	INT	NOT NULL	COMMENT '기본요금',
	`base_distance_km`	DECIMAL(10, 2)	NOT NULL	COMMENT '기본거리',
	`per_km_fare`	INT	NOT NULL	COMMENT 'km당요금',
	`is_active`	BOOLEAN	NOT NULL	DEFAULT TRUE	COMMENT '사용여부',
	`effective_from`	DATE	NOT NULL	COMMENT '적용일'
);

CREATE TABLE `regions` (
	`region_id`	INT	NOT NULL,
	`region_level`	VARCHAR(10)	NOT NULL	COMMENT '지역단계',
	`sido_name`	VARCHAR(20)	NOT NULL	COMMENT '시도',
	`sigungu_name`	VARCHAR(50)	NULL	COMMENT '시군구',
	`adm_code`	VARCHAR(10)	NULL	COMMENT '행정코드',
	`created_at`	DATETIME	NOT NULL	DEFAULT CURRENT_TIMESTAMP	COMMENT '등록일시',
	`parent_region_id`	INT	NULL
);

CREATE TABLE `faqs` (
	`faq_id`	INT	NOT NULL,
	`category`	VARCHAR(50)	NOT NULL	COMMENT '분류',
	`question`	VARCHAR(255)	NOT NULL	COMMENT '질문',
	`answer`	TEXT	NOT NULL	COMMENT '답변',
	`source_name`	VARCHAR(50)	NOT NULL	COMMENT '출처',
	`source_url`	VARCHAR(500)	NULL	COMMENT '원문URL',
	`crawled_at`	DATETIME	NULL	COMMENT '수집일시'
);

CREATE TABLE `data_sources` (
	`source_id`	INT	NOT NULL,
	`source_code`	VARCHAR(40)	NOT NULL	COMMENT '출처코드',
	`dataset_name`	VARCHAR(200)	NOT NULL	COMMENT '데이터명',
	`provider`	VARCHAR(100)	NOT NULL	COMMENT '제공기관',
	`portal_url`	VARCHAR(300)	NOT NULL	COMMENT '출처URL',
	`file_name`	VARCHAR(200)	NULL	COMMENT '파일명',
	`base_month`	DATE	NULL	COMMENT '기준월',
	`retrieved_at`	DATE	NOT NULL	COMMENT '수집일',
	`collection_method`	VARCHAR(10)	NOT NULL	COMMENT '수집방식',
	`coverage_note`	VARCHAR(500)	NULL	COMMENT '비고',
	`region_id`	INT	NOT NULL	COMMENT '지역번호'
);

CREATE TABLE `registration_stats` (
	`stat_id`	BIGINT	NOT NULL	COMMENT '통계번호',
	`base_month`	DATE	NOT NULL	COMMENT '기준월',
	`vehicle_kind`	VARCHAR(20)	NOT NULL	COMMENT '차종',
	`usage_type`	VARCHAR(20)	NOT NULL	COMMENT '용도',
	`vehicle_count`	INT	NOT NULL	COMMENT '등록대수',
	`source_id`	INT	NOT NULL,
	`region_id`	INT	NOT NULL
);

ALTER TABLE `bookings` ADD CONSTRAINT `PK_BOOKINGS` PRIMARY KEY (
	`booking_id`
);

ALTER TABLE `drivers` ADD CONSTRAINT `PK_DRIVERS` PRIMARY KEY (
	`driver_id`
);

ALTER TABLE `fare_rules` ADD CONSTRAINT `PK_FARE_RULES` PRIMARY KEY (
	`fare_rule_id`
);

ALTER TABLE `regions` ADD CONSTRAINT `PK_REGIONS` PRIMARY KEY (
	`region_id`
);

ALTER TABLE `faqs` ADD CONSTRAINT `PK_FAQS` PRIMARY KEY (
	`faq_id`
);

ALTER TABLE `data_sources` ADD CONSTRAINT `PK_DATA_SOURCES` PRIMARY KEY (
	`source_id`
);

ALTER TABLE `registration_stats` ADD CONSTRAINT `PK_REGISTRATION_STATS` PRIMARY KEY (
	`stat_id`
);



-- FK 9개 추가: 이미 존재하는 DB에 적용 시 기존 데이터의 참조 무결성을 먼저 확인하세요.
ALTER TABLE `regions` ADD CONSTRAINT `fk_regions_parent` FOREIGN KEY (`parent_region_id`) REFERENCES `regions` (`region_id`);
ALTER TABLE `registration_stats` ADD CONSTRAINT `fk_stats_source` FOREIGN KEY (`source_id`) REFERENCES `data_sources` (`source_id`);
ALTER TABLE `registration_stats` ADD CONSTRAINT `fk_stats_region` FOREIGN KEY (`region_id`) REFERENCES `regions` (`region_id`);
ALTER TABLE `drivers` ADD CONSTRAINT `fk_drivers_region` FOREIGN KEY (`region_id`) REFERENCES `regions` (`region_id`);
ALTER TABLE `drivers` ADD CONSTRAINT `fk_drivers_fare` FOREIGN KEY (`fare_rule_id`) REFERENCES `fare_rules` (`fare_rule_id`);
ALTER TABLE `bookings` ADD CONSTRAINT `fk_bookings_origin` FOREIGN KEY (`origin_region_id`) REFERENCES `regions` (`region_id`);
ALTER TABLE `bookings` ADD CONSTRAINT `fk_bookings_dest` FOREIGN KEY (`dest_region_id`) REFERENCES `regions` (`region_id`);
ALTER TABLE `bookings` ADD CONSTRAINT `fk_bookings_fare` FOREIGN KEY (`fare_rule_id`) REFERENCES `fare_rules` (`fare_rule_id`);
ALTER TABLE `bookings` ADD CONSTRAINT `fk_bookings_driver` FOREIGN KEY (`driver_id`) REFERENCES `drivers` (`driver_id`);
