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
MAX_RADIUS_M = 42_000      # 등록대수 최대 지역의 버블 반지름(m)
FILL = [15, 110, 86, 150]  # 반투명 → 겹쳐도 아래 버블이 보임
LINE = [8, 70, 55]


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


def bubble_data(points: pd.DataFrame, sido: pd.DataFrame) -> list[dict]:
    """버블 레코드 (큰 버블부터 → 작은 버블이 위에 그려져 마우스로 고를 수 있음)."""
    df = points[["sido_name", "lon", "lat"]].merge(sido[["sido_name", "truck_count"]], on="sido_name")
    vmax = int(df["truck_count"].max())
    df["radius"] = [round(MAX_RADIUS_M * math.sqrt(v / vmax)) for v in df["truck_count"]]
    df["count_label"] = [f"{int(v):,}대" for v in df["truck_count"]]
    df = df.sort_values("truck_count", ascending=False)
    return [{**r, "truck_count": int(r["truck_count"]), "radius": int(r["radius"])} for r in df.to_dict("records")]


def build_deck(
    points: pd.DataFrame,
    sido: pd.DataFrame,
    month_label: str,
    selected: str | None = None,
    labels: bool = True,
    zoom: float = 6.0,
) -> pdk.Deck:
    data = bubble_data(points, sido)
    # 주의: pydeck은 문자열 인자를 JS 식으로 바꾼다 (예: "pixels" → "@@=pixels").
    #       단위·크기는 숫자로, 글자 그대로의 값은 "'auto'"처럼 따옴표로 감싸서 넘긴다.
    layers = [
        pdk.Layer(
            "ScatterplotLayer", data, id=LAYER_ID, pickable=True, stroked=True, filled=True,
            get_position=["lon", "lat"], get_radius="radius", radius_min_pixels=5,
            get_fill_color=FILL, get_line_color=LINE, line_width_min_pixels=1,
        )
    ]
    if selected:
        layers.append(pdk.Layer(
            "ScatterplotLayer", [d for d in data if d["sido_name"] == selected], id="selected",
            pickable=False, stroked=True, filled=False, get_position=["lon", "lat"], get_radius="radius",
            radius_min_pixels=5, get_line_color=[0, 0, 0], line_width_min_pixels=3,
        ))
    if labels:
        layers.append(pdk.Layer(
            "TextLayer", data, id="labels", pickable=False, get_position=["lon", "lat"], get_text="sido_name",
            get_size=12, get_color=[20, 20, 20], character_set="'auto'", font_weight=700,
        ))
    tooltip = {"html": f"<b>{{sido_name}}</b><br/>영업용 화물차 등록대수 {{count_label}}<br/>{month_label} 기준"}
    view = pdk.ViewState(latitude=35.95, longitude=127.75, zoom=zoom, min_zoom=4.5, max_zoom=10)
    return pdk.Deck(layers=layers, initial_view_state=view, tooltip=tooltip, map_style=None)


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
