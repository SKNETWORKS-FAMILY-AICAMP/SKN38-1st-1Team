"""팀 전처리 CSV → DB 적재 (국토부 API 키가 없을 때 대신 사용)
- 저장 로직은 update_registration_db.py 함수를 그대로 재사용 (지역 매핑·출처·중복 방지·검증 동일)
- API 수집 단계만 CSV 읽기로 바꿈. 나중에 API로 같은 기준월을 실행하면 "새 기준월 없음"으로 그냥 종료됨
실행: python -m scripts.load_registration_csv
라이브러리: pandas(CSV 읽기)
"""
import pandas as pd

from scripts import update_registration_db as u            # 팀 적재 스크립트

CSV = "data/processed/truck_business_by_sigungu_202609.csv"


def main():
    df = pd.read_csv(CSV, dtype={"base_month": str})        # 202609를 숫자가 아닌 글자로 읽기
    month = df["base_month"].iloc[0]
    report = {"sigungu_rows": len(df), "total_vehicle_count": int(df["vehicle_count"].sum())}
    u.SOURCE_INFO = {**u.SOURCE_INFO, "collection_method": "File"}  # API가 아니라 파일로 넣었다고 기록

    conn = u.connect()
    try:
        with conn.cursor() as cur:
            schema = u.load_schema(cur)                                  # 팀 스키마 점검
            stored = u.stored_latest_month(cur)
            if stored and stored >= month:
                print(f"이미 {stored} 기준월 데이터가 있어 그대로 둡니다.")
                return
            month_value = u.month_to_db(month, schema["registration_stats"]["base_month"])
            source_id = u.upsert_source(cur, month, report, CSV.split("/")[-1], schema)   # 출처
            region_ids, added = u.map_regions(cur, df, schema, write=True)               # 지역
            inserted = u.insert_stats(cur, df, region_ids, source_id, month_value, schema)  # 등록대수
            u.verify_month(cur, month_value, report["sigungu_rows"], report["total_vehicle_count"])  # 검증
            conn.commit()
    except Exception:
        conn.rollback()                                                  # 실패하면 하나도 안 들어감
        raise
    finally:
        conn.close()
    print(f"기준월 {month} | 지역 추가 {added}건 | 등록통계 {inserted}건 저장 완료")


if __name__ == "__main__":
    main()
