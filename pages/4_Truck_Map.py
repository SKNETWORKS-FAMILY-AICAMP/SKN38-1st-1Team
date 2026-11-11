"""지역별 현황 (상단 메뉴) — 같은 시도별 버블 지도로 두 현황을 전환해서 본다

1) 배차 가능 기사 현황 (기본)
   services/driver_sim.load_driver_status: MySQL drivers에 저장된 배정 가능 기사 10,000명을 시도·시군구·차종별 집계
   (scripts/seed_drivers_excel.py가 통계누리 엑셀 '계' 열 비율로 배분해 생성 — 예약 매칭이 쓰는 바로 그 기사들)
2) 화물차 등록 현황 (국토교통부 공식 통계)
   services/truck_stats.py: MySQL registration_stats 최신 기준월 조회

지도: services/truck_map.build_deck (시도 대표 좌표 data/processed/sido_bubble_points.csv, 면적 ∝ 수치).
      두 화면은 데이터와 문구(단위·제목·툴팁)·색 구간 경계만 다르고 지도 디자인·3단계 색·크기 비례는 같다.
      좌표 파일이 없거나 지역명 매칭이 어긋나면 지도 대신 막대그래프로 표시한다.
"""

from html import escape

import streamlit as st

from services import driver_map as dm
from services.db import DBConnectionError
from services.driver_sim import VEHICLES, load_driver_status
from services.truck_map import (
    POINTS_SOURCE, build_deck, is_consistent, legend_html, load_points, match_points, picked_sido,
)
from services.truck_stats import format_month, load_truck_stats
from services.ui import stat_cards

VIEW_KEY = "region_view"             # 선택한 현황 (홈 버튼은 기본 화면으로 맞춰서 이동)
SIM, REG = "배차 가능 기사 현황", "화물차 등록 현황"
SELECT_KEY = "truck_map_sido"        # 선택한 시도 — 두 화면이 공유 (전환해도 유지)
DEFAULT_SIDO = "서울"                 # 처음 기준 지역
# 배차 가능 기사 현황의 지도 보기 모드 (전국 집계 ↔ 반경 내 기사 위치)
NATIONAL, DETAIL = "전국 보기", "기사 위치 자세히 보기"
MODE_KEY, SIGUNGU_KEY, RADIUS_KEY = "driver_map_mode", "driver_map_sigungu", "driver_map_radius"
CENTER_KEY, FOCUS_KEY, PICK_KEY = "driver_map_center", "driver_map_focus", "driver_map_pick"   # PICK은 초기화용


def _reset_detail() -> None:
    """기준 지역·반경이 바뀌면 직접 고른 기준점·펼친 묶음·선택 기사를 초기화."""
    for key in (CENTER_KEY, FOCUS_KEY, PICK_KEY):
        st.session_state.pop(key, None)


def _open_detail() -> None:
    st.session_state[MODE_KEY] = DETAIL
    _reset_detail()


def _pick_sigungu() -> None:
    """시군구를 고르면 그 지역으로 지도를 이동."""
    st.session_state.pop(CENTER_KEY, None)
    st.session_state.pop(PICK_KEY, None)
    st.session_state[FOCUS_KEY] = True


def render_driver_detail(sido, points) -> None:
    """전국 지도에서 시작 → 확대하면 기사 마커가 보임. 기준 시군구 주변 5km 안 기사 수·차종·목록."""
    radius = dm.DEFAULT_RADIUS
    centers = dm.sigungu_centers()
    drivers = dm.all_drivers()
    map_col, side = st.columns([3, 2], gap="large")
    with side:
        st.subheader("기준 지역")
        choice = st.selectbox("시도", sido["sido_name"].tolist(), key=SELECT_KEY, on_change=_pick_sigungu)
        options = centers[centers["sido_name"] == choice].sort_values("n", ascending=False)
        names = options["sigungu_name"].tolist()
        if st.session_state.get(SIGUNGU_KEY) not in names:
            st.session_state[SIGUNGU_KEY] = names[0]           # 기사가 가장 많은 시군구부터
        sg = st.selectbox("시군구", names, key=SIGUNGU_KEY, on_change=_pick_sigungu)

    base = options[options["sigungu_name"] == sg].iloc[0]
    custom = st.session_state.get(CENTER_KEY)
    lat, lng = (custom["lat"], custom["lng"]) if custom else (float(base["lat"]), float(base["lng"]))
    label = custom["label"] if custom else f"{choice} {sg}"
    inside = dm.within(drivers, lat, lng, radius)
    types = inside["vehicle_type"].value_counts()
    focus = (lat, lng) if st.session_state.get(FOCUS_KEY) else None   # 시도·시군구를 고르면 그 지역으로 확대

    with map_col:
        st.subheader("기사 위치")
        national = build_deck(points, sido, "", selected=choice, unit="명", tooltip_label="배차 가능 기사",
                              basis=" ", bounds=VIEW[SIM]["bounds"], variant="drivers")
        markers = dm.driver_markers()
        deck = dm.build_zoom_deck(national, (lat, lng), radius, focus, markers)
        with st.container(key="map_wrap_driver"):   # 키에 map_wrap을 포함해 지도 카드·범례 겹침 스타일 공유
            st.html(
                '<div class="jm-map-summary"><b>' + escape(label) + f"</b> · 반경 {radius}km<br>"
                f"기사 <em>{len(inside):,}명</em> · "
                + " · ".join(f"{v} {int(types.get(v, 0)):,}" for v in VEHICLES) + "</div>"
            )
            st.html('<div class="jm-map-legend"><b>기사 (차종)</b><ul>' + "".join(
                f'<li><i style="background:rgba({c[0]},{c[1]},{c[2]},.92)"></i>{v}</li>'
                for v, c in dm.VEHICLE_COLORS.items()) + "</ul></div>")
            # 줌에 따라 시도 버블 ↔ 기사 마커를 바꾸려면 지도 안에서 줌을 알아야 해서 HTML 지도로 표시
            st.iframe(dm.zoom_map_html(deck, markers), height=680)
        st.caption("처음엔 시도별 기사 수가 보이고, 지도를 확대할수록 버블이 흐려지면서 기사 위치가 나타나요. "
                   "시도 버블을 누르면 그 지역으로 확대돼요. 기사 마커에 마우스를 올리면 기사 정보를 볼 수 있어요.")

    with side:
        st.html('<div class="jm-type-row">' + "".join(
            f'<div><span>{v}</span><b>{int(types.get(v, 0)):,}명</b></div>' for v in VEHICLES) + "</div>")
        st.caption(f"기준점 반경 {radius}km 안 기사 {len(inside):,}명 · 거리는 등록 주소지와 기준점 사이의 직선거리예요.")
        table = inside[["nickname", "vehicle_type", "sigungu_name", "distance_km", "rating"]].head(200).rename(
            columns={"nickname": "기사", "vehicle_type": "차량", "sigungu_name": "시군구", "distance_km": "거리(km)",
                     "rating": "별점"})
        st.dataframe(table, hide_index=True, height=300,
                     column_config={"별점": st.column_config.NumberColumn(format="★ %.1f", help="평균 별점 (빈칸은 신규 기사)")})
        st.caption("가까운 순 최대 200명. 예약할 때는 차량 조건과 예약 일정까지 확인해 기사님을 추천해요.")


# 화면별로 바뀌는 데이터·문구만 모아 둠 (지도·표 구성은 공통)
VIEW = {
    SIM: {
        "title": "배차 가능 기사 현황", "badge": None,
        "desc": "지역별 영업용 화물차 등록대수 비율로 전국 10,000명의 기사를 배치한 현황입니다. "
                "운송 예약 시 이 기사들 중에서 추천·배정됩니다.",
        "warn": None,
        "unit": "명", "tooltip": "배차 가능 기사", "legend": "배차 가능 기사",
        "total_card": "배차 가능 기사", "top_card": "기사가 가장 많은 지역",
        "metric": "배차 가능 기사", "column": "전체(명)", "axis": "기사 수(명)",
        "map_help": "버블에 마우스를 올리면 기사 수를, 누르면 오른쪽에서 시군구·차종별 기사 수를 볼 수 있어요.",
        "bounds": (200, 600),       # 등록대수 구간(1만·3만 대)과 같은 비율 (10,000명 / 472,852대 ≈ 1/47)
    },
    REG: {
        "title": "전국 영업용 화물차 등록 현황", "badge": None,
        "desc": "국토교통부 공공데이터를 통해 전국의 영업용 화물차 등록 현황을 확인할 수 있습니다.",
        "warn": None,
        "unit": "대", "tooltip": "영업용 화물차", "legend": "영업용 화물차 등록대수",
        "total_card": "전국 영업용 화물차 등록대수", "top_card": "등록대수가 가장 많은 지역",
        "metric": "영업용 화물차 등록대수", "column": "등록대수(대)", "axis": "등록대수(대)",
        "map_help": "버블에 마우스를 올리면 등록대수를, 누르면 오른쪽에서 시군구별 상세를 볼 수 있어요.",
        "bounds": (10_000, 30_000),
    },
}

st.title("지역별 현황")
with st.container(key="jm_view_tabs"):
    view = st.segmented_control("현황 선택", [SIM, REG], default=SIM, key=VIEW_KEY, required=True,
                                label_visibility="collapsed", width="stretch") or SIM
cfg = VIEW[view]

# ── 데이터 (둘 다 MySQL: 기사 = drivers, 등록 현황 = registration_stats) ─────────
try:
    stats = load_driver_status() if view == SIM else load_truck_stats()
except DBConnectionError as e:
    st.error(str(e))
    st.stop()

sido, sigungu = stats["sido"], stats["sigungu"]
if sido.empty:
    st.warning("저장된 기사가 없습니다. python -m scripts.seed_drivers_excel 로 먼저 생성해 주세요." if view == SIM
               else "저장된 화물차 등록 통계가 없습니다. scripts/update_registration_db.py로 데이터를 먼저 적재해 주세요.")
    st.stop()
month = format_month(stats["base_month"])
unit = cfg["unit"]

st.html(
    '<div class="jm-view-head">'
    + (f'<span class="jm-sim-badge">{cfg["badge"]}</span>' if cfg["badge"] else "")
    + f'<h2>{cfg["title"]}</h2><p>{cfg["desc"]}</p>'
    + (f'<p class="warn">{cfg["warn"]}</p>' if cfg["warn"] else "")
    + "</div>"
)

top = sido.sort_values("truck_count", ascending=False).iloc[0]   # 원본 값 중 최다 지역 (새 통계를 만들지 않음)
if view == SIM:   # 기사: DB 저장 건수 + 차종별 합계
    types = stats["by_type"]
    stat_cards([
        (cfg["total_card"], f"{int(sido['truck_count'].sum()):,}{unit}", "예약 시 추천·배정되는 기사"),
        ("차종별 (다마스 · 라보 · 1톤)", " · ".join(f"{types[v]:,}" for v in VEHICLES), "40% · 30% · 30%로 배분"),
        (cfg["top_card"], f"{top['sido_name']}", f"{int(top['truck_count']):,}{unit} · 시군구 {len(sigungu)}곳에 배치"),
    ])
else:
    stat_cards([
        (cfg["total_card"], f"{int(sido['truck_count'].sum()):,}{unit}", f"{month} 등록 통계 기준"),
        (cfg["top_card"], f"{top['sido_name']}", f"{int(top['truck_count']):,}{unit}"),
        ("집계 지역", f"시도 {len(sido)}곳", f"시군구 {len(sigungu)}곳"),
    ])
st.space("medium")

points = load_points()
check = match_points(points, sido) if points is not None else None
map_ok = is_consistent(check)
if st.session_state.get(SELECT_KEY) not in sido["sido_name"].tolist():   # 처음이거나 유효하지 않으면 서울을 기준 지역으로
    st.session_state[SELECT_KEY] = DEFAULT_SIDO if DEFAULT_SIDO in sido["sido_name"].tolist() else sido["sido_name"].iloc[0]

detail_mode = False
if view == SIM:   # 기사: 전국 집계 버블 ↔ 기사 위치 (확대하면 기사 마커가 보이는 지도)
    with st.container(key="jm_mode_tabs"):
        mode = st.segmented_control("지도 보기", [NATIONAL, DETAIL], default=NATIONAL, key=MODE_KEY, required=True,
                                    label_visibility="collapsed", width="stretch") or NATIONAL
    detail_mode = mode == DETAIL

if detail_mode:
    render_driver_detail(sido, points)
else:
    map_col, detail_col = st.columns([3, 2], gap="large")
    with map_col:  # 지도를 먼저 실행해야 클릭한 시도가 오른쪽 선택 상자에 반영된다
        st.subheader("전국 · 시도별")
        if map_ok:
            with st.container(key="map_wrap"):  # 범례를 지도 오른쪽 아래에 겹쳐 표시
                st.html(legend_html(cfg["legend"], unit, cfg["bounds"], "drivers" if view == SIM else "default"))
                basis = f"{month} 등록대수 비율 기준" if view == SIM else f"{month} 기준"
                event = st.pydeck_chart(
                    build_deck(points, sido, month, selected=st.session_state.get(SELECT_KEY), unit=unit,
                               tooltip_label=cfg["tooltip"], basis=basis, bounds=cfg["bounds"],
                               variant="drivers" if view == SIM else "default"),
                    on_select="rerun", selection_mode="single-object", key=f"truck_map_deck_{unit}", height=680,
                )
            pick = picked_sido(event)
            last_key = f"truck_map_last_pick_{unit}"
            if pick and pick != st.session_state.get(last_key):  # 새로 클릭한 경우에만 선택 반영
                st.session_state[last_key] = pick
                st.session_state[SELECT_KEY] = pick
                st.rerun()  # 지도 강조 표시도 새 선택으로 다시 그림
            st.caption(cfg["map_help"] + " 지도는 확대·축소·이동할 수 있어요.")
            with st.expander("그래프로 보기"):
                st.bar_chart(sido.set_index("sido_name")["truck_count"], horizontal=True, x_label=cfg["axis"], y_label="")
        else:
            if points is None:
                st.info("시도 대표 좌표 파일이 없어 지도 대신 그래프로 표시합니다.")
            else:
                st.warning(
                    "대표 좌표와 시도명이 일치하지 않아 지도 대신 그래프로 표시합니다. "
                    f"좌표에만 있음: {check['unmatched_points']} · 통계에만 있음: {check['unmatched_db']}"
                )
            st.bar_chart(sido.set_index("sido_name")["truck_count"], horizontal=True, x_label=cfg["axis"], y_label="")

    with detail_col:
        st.subheader("지역 선택 · 시군구별 상세")
        choice = st.selectbox("시도", sido["sido_name"].tolist(), key=SELECT_KEY)
        columns = ["sigungu_name", "truck_count", *(VEHICLES if view == SIM else ())]
        detail = (
            sigungu[sigungu["sido_name"] == choice][columns]
            .sort_values("truck_count", ascending=False)
            .reset_index(drop=True)
        )
        row = sido.loc[sido["sido_name"] == choice].iloc[0]
        total = int(row["truck_count"])
        d1, d2 = st.columns(2)
        d1.metric(f"{choice} {cfg['metric']}", f"{total:,}{unit}")
        d2.metric("전국 대비", f"{total / sido['truck_count'].sum():.1%}")
        if view == SIM:   # 선택한 시도의 차종별 기사 수
            st.html('<div class="jm-type-row">' + "".join(
                f'<div><span>{v}</span><b>{int(row[v]):,}명</b></div>' for v in VEHICLES) + "</div>")
        st.dataframe(
            detail.rename(columns={"sigungu_name": "시군구", "truck_count": cfg["column"],
                                   **{v: f"{v}(명)" for v in VEHICLES}}),
            hide_index=True, height=360,
        )
        if view == SIM:
            st.button(f"{choice} 기사 위치 자세히 보기", key="open_driver_detail", on_click=_open_detail,
                      icon=":material/zoom_in:", width="stretch")
        st.caption("일부 시군구는 공식 통계 표기 그대로입니다. (예: 경북 군위군, 경기 부천시·화성시 잔여분)")

# ── 데이터 안내 · 출처 ────────────────────────────────────────────────
st.space("large")
note_col, source_col = st.columns([3, 2], gap="medium")
points_note = f'<p class="foot">{escape(POINTS_SOURCE)}</p>' if map_ok else ""
if view == SIM:
    with note_col:
        st.html(
            '<div class="jm-note"><h4>이 데이터는 이렇게 봐 주세요</h4>'
            "<p>시군구별 영업용 화물차 등록대수 비율로 전국 10,000명의 기사를 배치하고, "
            "차종을 다마스 40% · 라보 30% · 1톤 30%로 나눈 현황입니다.<br>"
            "운송 예약을 확정하면 이 기사들 중 조건에 맞는 기사님이 배정돼요.</p>"
            "<ul><li>지역별 기사 수는 시군구별 영업용 화물차 등록대수에 비례해요. (전국 472,852대 → 10,000명)</li>"
            "<li>버블이 클수록 기사가 많아요. (버블 면적 ∝ 기사 수)</li></ul></div>"
        )
    with source_col:
        st.html(
            '<div class="jm-source"><h4>데이터 출처</h4><dl>'
            "<dt>출처</dt><dd>국토교통부 통계누리 · 시군구별 영업용 화물차 등록현황</dd>"
            "<dt>배분 기준</dt><dd>시군구별 영업용 화물차 등록대수 비율</dd>"
            f"<dt>기준월</dt><dd>{month}</dd>"
            "<dt>차종</dt><dd>다마스 40% · 라보 30% · 1톤 30%</dd></dl>"
            + points_note + "</div>"
        )
else:
    source = stats["source"]
    with note_col:
        st.html(
            '<div class="jm-note"><h4>이 데이터는 이렇게 봐 주세요</h4>'
            "<p>국토교통부 자동차 등록 통계를 바탕으로 시도별 영업용 화물차 등록대수를 보여드립니다.<br>"
            "실제 운행 중인 차량 수나 지금 바로 이용 가능한 기사 수와는 다를 수 있어요.</p>"
            "<ul><li>버블이 클수록 등록대수가 많아요. (버블 면적 ∝ 등록대수)</li>"
            "<li>버블은 각 시도의 대표 위치에 표시한 것으로, 차량의 실제 위치는 아니에요.</li></ul></div>"
        )
    with source_col:
        if source:
            d = source["retrieved_at"]
            st.html(
                '<div class="jm-source"><h4>데이터 출처</h4><dl>'
                f"<dt>출처</dt><dd>{escape(source['provider'])} · {escape(source['dataset_name'])}</dd>"
                f"<dt>기준월</dt><dd>{format_month(source['base_month'])}</dd>"
                f"<dt>수집일</dt><dd>{d.year}년 {d.month}월 {d.day}일</dd>"
                f"<dt>원문</dt><dd><a href=\"{escape(source['portal_url'])}\" target=\"_blank\" rel=\"noopener\">"
                "원문 보기 ↗</a></dd></dl>"
                + points_note + "</div>"
            )
        else:
            st.html('<div class="jm-source"><h4>데이터 출처</h4><p>출처 정보가 없습니다.</p></div>')

st.space("medium")
if st.button("홈으로"):
    st.switch_page("pages/0_Home.py")
