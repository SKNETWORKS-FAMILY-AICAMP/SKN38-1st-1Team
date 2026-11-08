"""지역별 화물차 현황 — MySQL registration_stats 기반 시도·시군구 영업용 화물차 등록대수

지도: 시도별 등록대수를 대표 위치(data/processed/sido_bubble_points.csv)에 버블로 표시 (면적 ∝ 등록대수).
      좌표 파일이 없거나 지역명 매칭이 어긋나면 지도 대신 막대그래프로 표시한다.
"""

import streamlit as st

from services.db import DBConnectionError
from services.truck_map import POINTS_SOURCE, build_deck, is_consistent, load_points, match_points, picked_sido
from services.truck_stats import DATA_NOTE, format_month, load_truck_stats

SELECT_KEY = "truck_map_sido"
LAST_PICK_KEY = "truck_map_last_pick"

st.title("지역별 화물차 현황")

try:
    stats = load_truck_stats()
except DBConnectionError as e:
    st.error(str(e))
    st.stop()

sido, sigungu, source = stats["sido"], stats["sigungu"], stats["source"]
if sido.empty:
    st.warning("저장된 화물차 등록 통계가 없습니다. scripts/update_registration_db.py로 데이터를 먼저 적재해 주세요.")
    st.stop()

month = format_month(stats["base_month"])
st.caption(f"{month} 기준 · {DATA_NOTE}")

c1, c2, c3 = st.columns(3)
c1.metric("전국 영업용 화물차 등록대수", f"{int(sido['truck_count'].sum()):,}대")
c2.metric("시도", f"{len(sido)}곳")
c3.metric("시군구", f"{len(sigungu)}곳")

st.subheader("전국 · 시도별")
points = load_points()
check = match_points(points, sido) if points is not None else None
map_ok = is_consistent(check)

if map_ok:
    event = st.pydeck_chart(
        build_deck(points, sido, month, selected=st.session_state.get(SELECT_KEY)),
        on_select="rerun", selection_mode="single-object", key="truck_map_deck", height=640,
    )
    pick = picked_sido(event)
    if pick and pick != st.session_state.get(LAST_PICK_KEY):  # 새로 클릭한 경우에만 선택 반영
        st.session_state[LAST_PICK_KEY] = pick
        st.session_state[SELECT_KEY] = pick
        st.rerun()  # 지도 강조 표시도 새 선택으로 다시 그림
    st.caption("버블 면적이 클수록 등록대수가 많습니다. 버블을 클릭하면 아래 시군구 상세가 바뀝니다. "
               "지도는 확대·축소·이동할 수 있습니다.")
    st.caption(POINTS_SOURCE)
    with st.expander("그래프로 보기"):
        st.bar_chart(sido.set_index("sido_name")["truck_count"], horizontal=True, x_label="등록대수(대)", y_label="")
else:
    if points is None:
        st.info("시도 대표 좌표 파일이 없어 지도 대신 그래프로 표시합니다.")
    else:
        st.warning(
            "대표 좌표와 DB 시도명이 일치하지 않아 지도 대신 그래프로 표시합니다. "
            f"좌표에만 있음: {check['unmatched_points']} · 통계에만 있음: {check['unmatched_db']}"
        )
    st.bar_chart(sido.set_index("sido_name")["truck_count"], horizontal=True, x_label="등록대수(대)", y_label="")

st.subheader("지역 선택 · 시군구별 상세")
choice = st.selectbox("시도", sido["sido_name"].tolist(), key=SELECT_KEY)
detail = (
    sigungu[sigungu["sido_name"] == choice][["sigungu_name", "truck_count"]]
    .sort_values("truck_count", ascending=False)
    .reset_index(drop=True)
)
total = int(sido.loc[sido["sido_name"] == choice, "truck_count"].iloc[0])
d1, d2 = st.columns(2)
d1.metric(f"{choice} 영업용 화물차 등록대수", f"{total:,}대")
d2.metric("전국 대비", f"{total / sido['truck_count'].sum():.1%}")
st.dataframe(
    detail.rename(columns={"sigungu_name": "시군구", "truck_count": "등록대수(대)"}),
    hide_index=True,
)
st.caption("일부 시군구는 공식 통계 표기 그대로입니다. (예: 경북 군위군, 경기 부천시·화성시 잔여분)")

st.subheader("출처")
if source:
    st.write(f"{source['provider']} · {source['dataset_name']}")
    st.write(f"기준월 {format_month(source['base_month'])} · 수집일 {source['retrieved_at']}")
    st.markdown(f"[원문 보기]({source['portal_url']})")
else:
    st.write("출처 정보가 없습니다.")
if map_ok:
    st.write(POINTS_SOURCE)

if st.button("홈 · 요청하기로 이동"):
    st.switch_page("pages/1_Delivery_Request.py")
