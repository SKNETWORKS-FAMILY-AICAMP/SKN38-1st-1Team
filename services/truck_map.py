"""시도별 영업용 화물차 등록대수 버블 지도 (pydeck ScatterplotLayer)

- 버블 위치: data/processed/sido_bubble_points.csv (시도 16개 대표 좌표)
    출처: 국가데이터처 SGIS 센서스용 행정구역경계(시도, 2025-06-30 기준)에서 계산한 각 시도 본토의
          '경계에서 가장 먼 내부 점'(pole of inaccessibility). 광주광역시+전라남도는 합쳐서 '전남광주' 1개.
          16개 모두 원본 경계 기준으로 자기 시도 안에 있고 다른 시도와 겹치지 않음을 확인함.
    버블은 시도 통계를 대표 위치에 표시한 것이며 지역 전체 범위나 차량의 실제 위치가 아니다.
- 버블 크기: 면적이 등록대수에 비례 (반지름 ∝ √등록대수)
- 수치: services.truck_stats.load_truck_stats()의 시도별 등록대수 (DB 값만 사용)
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

POINTS_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "sido_bubble_points.csv"
POINTS_SOURCE = "버블 위치: 각 시도의 대표 지점(국가데이터처 SGIS 행정구역경계 기준 시도 내부 중심부). 지역 전체 범위나 차량 위치가 아닙니다."
LAYER_ID = "sido_bubble"
MAX_RADIUS_M = 52_000      # 등록대수 최대 지역의 버블 반지름(m)
MAP_STYLE = "https://basemaps.cartocdn.com/gl/voyager-nolabels-gl-style/style.json"  # 연한 하늘색 바다·밝은 육지, 지명 글자 없음

# 수치 구간별 버블 색 (브랜드 블루 #2563EB 계열, 많을수록 진하게) — 범례와 같은 기준
# 두 화면(가상 기사 현황 · 화물차 등록 현황)이 같은 3단계 색을 쓰고, 구간 경계(bounds)와 단위만 바뀐다
TIERS = [  # (채우기 RGBA, 글자색) — 연한 → 진한
    ([37, 99, 235, 45], [17, 31, 63]),
    ([37, 99, 235, 95], [17, 31, 63]),
    ([37, 99, 235, 185], [255, 255, 255]),
]
DEFAULT_BOUNDS = (10_000, 30_000)    # 화물차 등록대수 기준 (대)
# 가상 기사 현황용 변형: 하늘빛 블루 + 얇은 블루 테두리로 화물차 등록 현황 지도와 구분 (검정 테두리 없음)
DRIVER_TIERS = [
    ([56, 189, 248, 50], [12, 74, 110]),
    ([14, 165, 233, 100], [12, 74, 110]),
    ([2, 132, 199, 190], [255, 255, 255]),
]
DRIVER_LINE = [2, 132, 199, 170]
HOVER = [29, 78, 216, 150]          # 마우스를 올린 버블 (버블은 테두리 없이 색으로만 구분)
SELECTED_FILL = [29, 78, 216, 235]  # 선택한 버블: 진한 블루 #1D4ED8

# 글자는 지도 단위(m)로 그려 확대·축소에 따라 버블과 함께 커지고 작아지게 한다.
# 기준 줌(처음 화면)에서 1픽셀이 몇 m인지로 픽셀 크기·위치 보정값을 m로 바꾼다. (지도 타일 512px 기준)
BASE_ZOOM = 6.2
BASE_LAT = 35.85
M_PER_PX = 78_271.52 * math.cos(math.radians(BASE_LAT)) / 2 ** BASE_ZOOM
LABEL_MAX_PX = 30                   # 많이 확대해도 글자가 이 크기 이상 커지지 않게
# 버블이 서로 붙은 지역은 글자 위치를 조금 옮겨 겹치지 않게 (기준 줌에서의 픽셀, [오른쪽, 아래])
LABEL_OFFSETS = {"인천": [-12, 12], "서울": [4, -16], "경기": [10, 8], "세종": [-14, -14], "대전": [6, 8],
                 "울산": [12, -8], "부산": [0, 6]}
TOOLTIP_STYLE = {
    "backgroundColor": "#FFFFFF", "color": "#111F3F", "border": "1px solid #E6EBF3", "borderRadius": "12px",
    "padding": "10px 14px", "fontFamily": "Pretendard, sans-serif", "fontSize": "13px", "lineHeight": "1.5",
    "boxShadow": "0 8px 24px rgba(17, 31, 63, .12)",
}


@st.cache_data(show_spinner=False)
def _load_points(mtime: float) -> pd.DataFrame:  # mtime: 파일이 바뀌면 다시 읽음
    return pd.read_csv(POINTS_PATH, encoding="utf-8")


def load_points() -> pd.DataFrame | None:
    """대표 좌표 파일이 없으면 None (화면은 그래프로 대체)."""
    if not POINTS_PATH.exists():
        return None
    return _load_points(POINTS_PATH.stat().st_mtime)


def match_points(points: pd.DataFrame, sido: pd.DataFrame) -> dict:
    """대표 좌표의 지역명과 DB 시도명 매칭 결과 및 합계 검증."""
    names = points["sido_name"].tolist()
    db_counts = dict(zip(sido["sido_name"], sido["truck_count"]))
    matched = set(names) & set(db_counts)
    return {
        "unmatched_points": sorted(set(names) - set(db_counts)),  # 좌표는 있는데 통계가 없음
        "unmatched_db": sorted(set(db_counts) - set(names)),      # 통계는 있는데 좌표가 없음
        "duplicated_points": sorted({n for n in names if names.count(n) > 1}),
        "matched_count": len(matched),
        "matched_total": int(sum(db_counts[n] for n in matched)),
        "db_total": int(sum(db_counts.values())),
    }


def is_consistent(check: dict | None) -> bool:
    """좌표와 DB 시도명이 1:1로 맞을 때만 지도를 그린다."""
    return bool(check) and not (check["unmatched_points"] or check["unmatched_db"] or check["duplicated_points"])


def tier_of(count: int, bounds: tuple = DEFAULT_BOUNDS, variant: str = "default") -> tuple:
    """수치가 속한 색 구간 (채우기, 글자색)."""
    return (DRIVER_TIERS if variant == "drivers" else TIERS)[sum(count >= b for b in bounds)]


def tier_labels(unit: str, bounds: tuple = DEFAULT_BOUNDS) -> list[str]:
    low, high = bounds
    return [f"{low:,}{unit} 미만", f"{low:,} ~ {high:,}{unit}", f"{high:,}{unit} 이상"]


def legend_html(title: str = "영업용 화물차 등록대수", unit: str = "대", bounds: tuple = DEFAULT_BOUNDS,
                variant: str = "default") -> str:
    """지도 오른쪽 아래에 겹쳐 표시하는 범례 (TIERS와 같은 기준)."""
    rows = "".join(
        f'<li><i style="background:rgba({c[0]},{c[1]},{c[2]},{c[3] / 255:.2f})"></i>{label}</li>'
        for (c, _), label in zip(DRIVER_TIERS if variant == "drivers" else TIERS, tier_labels(unit, bounds))
    )
    return f'<div class="jm-map-legend"><b>{title}</b><ul>{rows}</ul></div>'


def _label_position(name: str, lon: float, lat: float) -> list[float]:
    """글자 위치. 옮길 지역은 픽셀 보정값을 경위도로 바꿔 줌을 바꿔도 버블과 같은 비율로 움직이게 한다."""
    dx, dy = LABEL_OFFSETS.get(name, (0, 0))
    meters_per_deg_lon = 111_320 * math.cos(math.radians(lat))
    return [lon + dx * M_PER_PX / meters_per_deg_lon, lat - dy * M_PER_PX / 110_540]


def bubble_data(points: pd.DataFrame, sido: pd.DataFrame, unit: str = "대", bounds: tuple = DEFAULT_BOUNDS,
                variant: str = "default") -> list[dict]:
    """버블 레코드 (큰 버블부터 → 작은 버블이 위에 그려져 마우스로 고를 수 있음)."""
    df = points[["sido_name", "lon", "lat"]].merge(sido[["sido_name", "truck_count"]], on="sido_name")
    vmax = int(df["truck_count"].max())
    df = df.sort_values("truck_count", ascending=False)
    records = []
    for r in df.to_dict("records"):
        count = int(r["truck_count"])
        fill, text_color = tier_of(count, bounds, variant)
        share = math.sqrt(count / vmax)
        name = "전남·광주" if r["sido_name"] == "전남광주" else r["sido_name"]
        records.append({
            **r, "truck_count": count, "radius": round(MAX_RADIUS_M * share), "count_label": f"{count:,}{unit}",
            "label": f"{name}\n{count:,}{unit}", "fill": fill, "text_color": text_color,
            "dark": text_color[0] == 255,
            "text_size_m": round((11 + 6 * share) * M_PER_PX),  # 큰 버블일수록 글자도 크게 (기준 줌에서 11~17px)
            "label_position": _label_position(r["sido_name"], r["lon"], r["lat"]),
        })
    return records


def build_deck(
    points: pd.DataFrame,
    sido: pd.DataFrame,
    month_label: str,
    selected: str | None = None,
    labels: bool = True,
    zoom: float = BASE_ZOOM,
    unit: str = "대",
    tooltip_label: str = "영업용 화물차",
    basis: str | None = None,
    bounds: tuple = DEFAULT_BOUNDS,
    variant: str = "default",
    bubble_max_px: int | None = None,
) -> pdk.Deck:
    """시도별 버블 지도. 표시 데이터와 문구(unit·tooltip_label·basis)만 바꿔 두 현황 화면이 같은 디자인을 쓴다."""
    data = bubble_data(points, sido, unit, bounds, variant)
    outline = variant == "drivers"   # 가상 기사 현황: 얇은 하늘빛 테두리
    # 주의: pydeck은 문자열 인자를 JS 식으로 바꾼다 (예: "fill" → 각 레코드의 fill 값).
    #       단위·크기는 숫자로, 글자 그대로의 값은 "'auto'"처럼 따옴표로 감싸서 넘긴다.
    layers = [
        pdk.Layer(
            "ScatterplotLayer", data, id=LAYER_ID, pickable=True, stroked=outline, filled=True,
            get_position=["lon", "lat"], get_radius="radius", radius_min_pixels=3,
            **({"radius_max_pixels": bubble_max_px} if bubble_max_px else {}),
            get_line_color=DRIVER_LINE, line_width_min_pixels=1.5,
            get_fill_color="fill", auto_highlight=True, highlight_color=HOVER,  # hover 시 조금 더 진한 블루
        )
    ]
    if selected:  # 선택한 버블만 진한 블루 (기본 버블 아래에 그려 겹친 작은 버블도 보이게)
        layers.insert(0, pdk.Layer(
            "ScatterplotLayer", [d for d in data if d["sido_name"] == selected], id="selected",
            pickable=False, stroked=False, filled=True, get_position=["lon", "lat"], get_radius="radius",
            radius_min_pixels=3, get_fill_color=SELECTED_FILL,
            **({"radius_max_pixels": bubble_max_px} if bubble_max_px else {}),
        ))
    if labels:  # 버블 안에 지역명 + 등록대수. 진한 버블은 흰 글자, 연한 버블은 네이비 글자
        for dark in (False, True):
            if dark:
                rows = [d for d in data if d["dark"] or d["sido_name"] == selected]
            else:
                rows = [d for d in data if not d["dark"] and d["sido_name"] != selected]
            if not rows:
                continue
            layers.append(pdk.Layer(
                "TextLayer", rows, id=f"labels_{'dark' if dark else 'light'}", pickable=False,
                get_position="label_position", get_text="label", get_size="text_size_m",
                size_units="'meters'", size_min_pixels=0, size_max_pixels=LABEL_MAX_PX,  # 줌에 따라 글자 크기 변화
                get_color=[255, 255, 255] if dark else [17, 31, 63], character_set="'auto'", font_weight=700,
                font_family="'Pretendard, sans-serif'", font_settings={"sdf": True}, line_height=1.25,
                outline_width=3 if dark else 4,
                outline_color=[29, 78, 216, 230] if dark else [255, 255, 255, 230],
            ))
    tooltip = {
        "html": f"<b style='font-size:14px'>{{sido_name}}</b><br/>{tooltip_label} <b style='color:#2563EB'>{{count_label}}</b>"
                f"<br/><span style='color:#5B6475'>{basis or month_label + ' 기준'}</span>",
        "style": TOOLTIP_STYLE,
    }
    view = pdk.ViewState(latitude=BASE_LAT, longitude=127.75, zoom=zoom, min_zoom=5.3, max_zoom=10)  # 한국 중심
    return pdk.Deck(layers=layers, initial_view_state=view, tooltip=tooltip, map_style=MAP_STYLE)


def picked_sido(event) -> str | None:
    """st.pydeck_chart(on_select="rerun") 결과에서 클릭한 시도명."""
    try:
        objects = event.selection["objects"].get(LAYER_ID) or []
    except (AttributeError, KeyError, TypeError):
        return None
    if not objects:
        return None
    obj = objects[0]
    props = obj.get("properties", obj) if isinstance(obj, dict) else {}
    return props.get("sido_name")
