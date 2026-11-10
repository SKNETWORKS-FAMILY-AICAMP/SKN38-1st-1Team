"""기사 위치 지도 — MySQL drivers의 주소지 좌표(base_lat, base_lng)로 반경 내 기사 조회·표시

화면 (pages/4_Truck_Map.py '기사 위치 자세히 보기')
    - 처음엔 전국 지도(시도 버블). 기사 마커는 미터 단위 크기라 전국 축척에서는 보이지 않고,
      지도를 확대하면 자연스럽게 나타난다 (pydeck은 줌 이벤트를 Python에 주지 않아 지도 자체의 축척으로 전환)
    - 반경은 5km 고정: 고른 시군구 기준점 주변 5km 원과 그 안의 기사 수·차종을 표시

데이터 (기사 매칭 services/matching.py와 같은 기준)
    - drivers.base_lat · base_lng (DECIMAL(9,6)) = 기사 등록 주소지 좌표
    - 배정 가능(is_active = TRUE) 기사만, 차종은 fare_rules.vehicle_type, 별점은 drivers.avg_rating (matching·별점 입력과 같은 값)
    - 거리: matching.haversine_km (두 좌표 사이 직선거리, km). 도로 이동 거리 아님
    - 예약 일정·차량 조건까지 보는 실제 매칭 결과와는 다를 수 있다 (화면에 안내)

성능
    - 배정 가능 기사(약 47,000명)의 필요한 열만 한 번 조회해 60초 캐시, 같은 좌표는 한 마커로 묶어 지도 용량 절약
    - 반경 판정은 기준점 주변 사각 범위로 먼저 거른 뒤 Haversine
    - 마커(사람 모양)는 확대했을 때만 서서히 나타나고, 그 전에는 그려지지 않음 (visible=false)
    - 같은 좌표의 기사는 위치를 옮기지 않고 한 마커로 묶어 툴팁에 함께 표시
"""

from __future__ import annotations

import base64
import io
import math
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from services.db import get_connection
from services.matching import haversine_km           # 기사 매칭과 같은 거리 계산
from services.truck_map import MAP_STYLE, TOOLTIP_STYLE

DEFAULT_RADIUS = 5                    # km (고정)
VEHICLE_COLORS = {                    # 차종별 마커 색 (블루 계열 명도 차이)
    "다마스": [96, 165, 250, 235],
    "라보": [37, 99, 235, 235],
    "1톤": [30, 58, 138, 235],
}
DRIVER_LAYER, OUTSIDE_LAYER, CLUSTER_LAYER = "drivers_in", "drivers_out", "driver_clusters"

_DRIVERS_SQL = """
    SELECT d.driver_id, d.nickname, d.base_lat, d.base_lng, f.vehicle_type, r.sido_name, r.sigungu_name,
           d.avg_rating AS rating, d.rating_count                   -- 기사 평균 별점 (예약 조회에서 별점 입력 시 갱신)
    FROM drivers d
    JOIN fare_rules f ON f.fare_rule_id = d.fare_rule_id
    JOIN regions r ON r.region_id = d.region_id
    WHERE d.is_active = TRUE AND d.base_lat BETWEEN %s AND %s AND d.base_lng BETWEEN %s AND %s
"""


def _box(lat: float, lng: float, km: float) -> tuple[float, float, float, float]:
    dlat = km / 110.574
    dlng = km / (111.320 * math.cos(math.radians(lat)))
    return lat - dlat, lat + dlat, lng - dlng, lng + dlng


@st.cache_data(ttl=600, show_spinner=False)
def sigungu_centers() -> pd.DataFrame:
    """시군구 기준점: 그 시군구 기사들이 가장 많이 모인 곳 (기사 좌표 중앙값에 가장 가까운 기사 위치).

    기사 좌표는 시군구 안 실제 장소이므로 기준점도 항상 육지·시군구 안이 된다 (행정 중심이 물 위에 잡히는 문제 방지).
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("""SELECT r.region_id, r.sido_name, r.sigungu_name, d.base_lat AS lat, d.base_lng AS lng
                       FROM regions r JOIN drivers d ON d.region_id = r.region_id AND d.is_active = TRUE
                       WHERE r.sigungu_name IS NOT NULL""")
        raw = pd.DataFrame(cur.fetchall(), columns=["region_id", "sido_name", "sigungu_name", "lat", "lng"])
    raw[["lat", "lng"]] = raw[["lat", "lng"]].astype(float)
    rows = []
    for (rid, sido, sg), grp in raw.groupby(["region_id", "sido_name", "sigungu_name"]):
        mlat, mlng = grp["lat"].median(), grp["lng"].median()
        k = ((grp["lat"] - mlat) ** 2 + (grp["lng"] - mlng) ** 2).idxmin()
        rows.append((rid, sido, sg, grp.at[k, "lat"], grp.at[k, "lng"], len(grp)))
    return pd.DataFrame(rows, columns=["region_id", "sido_name", "sigungu_name", "lat", "lng", "n"])


def zoom_for(radius_km: float, lat: float, map_height_px: int = 680) -> float:
    """반경 원 지름이 지도 높이의 약 75%가 되는 줌 (지도 타일 512px 기준)."""
    meters_per_px = radius_km * 2000 / (map_height_px * 0.75)
    return round(math.log2(78_271.52 * math.cos(math.radians(lat)) / meters_per_px), 2)


def picked(event) -> tuple[str, dict] | None:
    """지도에서 누른 대상: ("driver" | "outside" | "cluster", 그 레코드)."""
    try:
        objects = event.selection["objects"]
    except (AttributeError, KeyError, TypeError):
        return None
    for layer, kind in ((DRIVER_LAYER, "driver"), (CLUSTER_LAYER, "cluster"), (OUTSIDE_LAYER, "outside")):
        items = objects.get(layer) or []
        if items:
            obj = items[0]
            return kind, (obj.get("properties", obj) if isinstance(obj, dict) else {})
    return None


# ── 전국 지도 + 확대 시 기사 마커 ───────────────────────────────────────
MARKER_RADIUS_M = 90         # 기사 마커 반지름(m): 전국 축척에선 1px 미만이라 안 보이고, 확대하면 나타남
MARKER_MAX_PX = 7
BUBBLE_MAX_PX = 70           # 확대해도 시도 버블이 화면을 덮지 않게


@st.cache_data(ttl=60, show_spinner="기사 위치를 불러오는 중...")
def all_drivers() -> pd.DataFrame:
    """배정 가능 기사 전체 (지도 마커·반경 집계용, 필요한 열만)."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(_DRIVERS_SQL, (-90, 90, -180, 180))
        df = pd.DataFrame(cur.fetchall(), columns=["driver_id", "nickname", "base_lat", "base_lng", "vehicle_type",
                                                   "sido_name", "sigungu_name", "rating", "rating_count"])
    df["base_lat"] = df["base_lat"].astype(float)
    df["base_lng"] = df["base_lng"].astype(float)
    df["rating"] = pd.to_numeric(df["rating"]).round(1)       # 화면 표시는 소수 한 자리 (예: 4.6)
    return df


def within(df: pd.DataFrame, lat: float, lng: float, radius_km: float) -> pd.DataFrame:
    """기준점 반경 안 기사 (직선거리 = matching.haversine_km), 가까운 순."""
    lat_min, lat_max, lng_min, lng_max = _box(lat, lng, radius_km)
    near = df[df["base_lat"].between(lat_min, lat_max) & df["base_lng"].between(lng_min, lng_max)].copy()
    near["distance_km"] = [round(haversine_km(lat, lng, a, b), 2) for a, b in zip(near["base_lat"], near["base_lng"])]
    return near[near["distance_km"] <= radius_km].sort_values("distance_km").reset_index(drop=True)


MARKER_ICON = Path(__file__).resolve().parents[1] / "assets" / "driver_marker.png"
ICON_PX = 64                                                     # 아틀라스 안 아이콘 한 칸 크기


@st.cache_resource(show_spinner=False)
def person_icon_uri() -> str:
    """기사 마커 아이콘 아틀라스 (assets/driver_marker.png 모양, 차종마다 한 칸).

    원본은 그라데이션 원에 사람 모양이 뚫려 있어서, 흰 원 위에 원 부분만 차종 색 그라데이션
    (왼쪽 밝게 → 오른쪽 차종 색)으로 칠해 사람은 흰색, 원은 차종 색이 되게 만든다.
    """
    from PIL import Image, ImageDraw

    src = Image.open(MARKER_ICON).convert("RGBA")
    alpha = src.getchannel("A")
    w, h = src.size
    atlas = Image.new("RGBA", (ICON_PX * len(VEHICLE_COLORS), ICON_PX), (0, 0, 0, 0))
    for k, color in enumerate(VEHICLE_COLORS.values()):
        light = [round(c + (255 - c) * 0.3) for c in color[:3]]
        grad = Image.new("RGBA", (w, 1))
        grad.putdata([tuple(round(a + (b - a) * x / (w - 1)) for a, b in zip(light, color[:3])) + (255,)
                      for x in range(w)])
        grad = grad.resize((w, h))
        icon = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        disc = Image.new("L", (w, h), 0)
        ImageDraw.Draw(disc).ellipse([1, 1, w - 2, h - 2], fill=255)
        icon.paste((255, 255, 255, 255), (0, 0), disc)            # 사람 자리(뚫린 부분)를 흰색으로
        icon.paste(grad, (0, 0), alpha)                            # 원 부분만 차종 색 그라데이션
        atlas.paste(icon.resize((ICON_PX, ICON_PX), Image.LANCZOS), (ICON_PX * k, 0))
    buf = io.BytesIO()
    atlas.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


VEHICLE_ORDER = list(VEHICLE_COLORS)        # 마커 차종 번호 (0 다마스 · 1 라보 · 2 1톤)


@st.cache_data(ttl=60, show_spinner=False)
def driver_markers() -> dict:
    """기사 마커 (같은 좌표는 한 마커로 묶음, 위치 이동 없음).

    약 47,000명이라 지도 용량을 줄이려고 숫자만 담는다: p=[경도, 위도](소수 5자리 ≈ 1m), v=차종 번호,
    r=지역 번호, s=성 번호, n=같은 좌표 인원, a=별점×10 · c=별점 개수(한 명이고 별점이 있을 때만). 툴팁 글자는 지도 안 스크립트가 번호 → 글자로 바꿔 만든다.
    """
    df = all_drivers()
    g = df.groupby(["base_lat", "base_lng"], sort=False).agg(
        n=("driver_id", "size"), nickname=("nickname", "first"), vehicle=("vehicle_type", "first"),
        sido=("sido_name", "first"), sigungu=("sigungu_name", "first"),
        rating=("rating", "first"), count=("rating_count", "first")).reset_index()
    regions = sorted(set(g["sido"] + " " + g["sigungu"]))
    surnames = sorted({nick[0] for nick in g["nickname"]})
    r_idx, s_idx = {name: k for k, name in enumerate(regions)}, {ch: k for k, ch in enumerate(surnames)}
    records = []
    for a, b, v, sd, sg, nick, n, rt, cnt in zip(g["base_lat"], g["base_lng"], g["vehicle"], g["sido"], g["sigungu"],
                                                 g["nickname"], g["n"], g["rating"], g["count"]):
        rec = {"p": [round(b, 5), round(a, 5)], "v": VEHICLE_ORDER.index(v) if v in VEHICLE_ORDER else 1,
               "r": r_idx[f"{sd} {sg}"], "s": s_idx[nick[0]], "n": int(n)}
        if n == 1 and pd.notna(rt):
            rec["a"], rec["c"] = int(round(float(rt) * 10)), int(cnt)
        records.append(rec)
    return {"records": records, "regions": regions, "surnames": surnames}


def build_zoom_deck(national: pdk.Deck, center: tuple[float, float], radius_km: float,
                    focus: tuple[float, float] | None, markers: dict) -> pdk.Deck:
    """시도 버블(national 지도의 레이어) + 반경 원 + 사람 모양 기사 마커. 줌에 따른 투명도 전환은 zoom_map_html."""
    lat, lng = center
    layers = list(national.layers)
    layers += [
        pdk.Layer("ScatterplotLayer", [{"lat": lat, "lng": lng}], id="radius_circle", pickable=False, visible=False,
                  get_position=["lng", "lat"], get_radius=radius_km * 1000, stroked=True, filled=True,
                  get_fill_color=[37, 99, 235, 26], get_line_color=[37, 99, 235, 170], line_width_min_pixels=2),
    ]
    # 차종마다 레이어를 나눠 색을 고정 (deck.gl 문자열 식은 조건식(?:)을 지원하지 않음)
    for k in range(len(VEHICLE_COLORS)):
        layers.append(pdk.Layer(
            "IconLayer", [r for r in markers["records"] if r["v"] == k], id=f"{DRIVER_LAYER}_{k}",
            pickable=True, visible=False, get_position="p", icon_atlas=f"'{person_icon_uri()}'",  # 따옴표: 문자열 그대로
            icon_mapping={"person": {"x": ICON_PX * k, "y": 0, "width": ICON_PX, "height": ICON_PX, "mask": False}},
            get_icon="'person'", get_size=MARKER_SIZE_M, size_units="'meters'",
            size_min_pixels=MARKER_MIN_PX, size_max_pixels=MARKER_MAX_PX,   # 줌 아웃에선 작게, 확대할수록 커짐
            auto_highlight=True, highlight_color=[251, 183, 29, 255]))
    layers += [
        pdk.Layer("ScatterplotLayer", [{"lat": lat, "lng": lng}], id="center_point", pickable=False, visible=False,
                  get_position=["lng", "lat"], get_radius=1, radius_min_pixels=4,
                  get_fill_color=[17, 31, 63, 255], stroked=True, get_line_color=[255, 255, 255, 255],
                  line_width_min_pixels=2),
    ]
    if focus:
        view = pdk.ViewState(latitude=focus[0], longitude=focus[1], zoom=zoom_for(radius_km, focus[0]),
                             min_zoom=5.3, max_zoom=16)
    else:
        view = national.initial_view_state
        view.max_zoom = 16                    # 전국 지도(최대 10)보다 더 확대해 기사 한 명씩 볼 수 있게
    return pdk.Deck(layers=layers, initial_view_state=view, map_style=MAP_STYLE, tooltip=False)


# 줌에 따른 전환: 버블은 FADE_START→FADE_END 동안 서서히 투명해지고,
# 기사 마커는 SHOW_START→SHOW_END 동안 서서히 나타난다 (구간이 겹쳐 버블 → 흐려짐 → 마커로 자연스럽게 이어짐)
FADE_START, FADE_END = 7.4, 9.2
SHOW_START, SHOW_END = 8.3, 9.6
MARKER_SIZE_M, MARKER_MIN_PX, MARKER_MAX_PX = 250, 9, 28   # 원형 사람 아이콘 지름 (m 기준, 화면에서 9~28px)
BUBBLE_IDS = ("sido_bubble", "selected", "labels_light", "labels_dark")
MARKER_IDS = tuple(f"{DRIVER_LAYER}_{k}" for k in range(len(VEHICLE_COLORS))) + ("radius_circle", "center_point")

_ZOOM_SCRIPT = """
<style>.mapboxgl-canvas, .maplibregl-canvas { filter: grayscale(1) sepia(.35) hue-rotate(192deg) saturate(3) brightness(1.02); }
body { margin: 0; } #deck-container { border-radius: 20px; overflow: hidden; }</style>
<script>
(function () {
  const F0 = __F0__, F1 = __F1__, S0 = __S0__, S1 = __S1__;
  const BUBBLES = new Set(__BUBBLES__), MARKERS = new Set(__MARKERS__);
  const REGIONS = __REGIONS__, SURNAMES = __SURNAMES__, VEHICLES = __VEHICLES__, TIP = __TIP_STYLE__;
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]; }); }
  function tooltip(info) {                     // 툴팁 글자 (기사 마커: 번호 → 글자)
    const o = info && info.object;
    if (!o) return null;
    let title, sub;
    if (o.r !== undefined) {
      title = o.n > 1 ? "기사 " + o.n + "명" : SURNAMES[o.s] + "** 기사님 (" + VEHICLES[o.v] + ")";
      sub = REGIONS[o.r];
      if (o.n === 1) sub = (o.a !== undefined ? "★ " + (o.a / 10).toFixed(1) + " (" + o.c + "건)" : "신규 기사")
                           + " · " + sub;   // 별점 (매칭 화면과 같은 평균 별점)
    } else if (o.sido_name) {
      title = o.sido_name; sub = "배차 가능 기사 " + o.count_label;
    } else return null;
    return { html: "<b style='font-size:14px'>" + esc(title) + "</b><br/>" + esc(sub), style: TIP };
  }
  const clamp = function (x) { return Math.max(0, Math.min(1, x)); };
  let last = null, pending = null, zoom = __START_ZOOM__;
  function apply() {                           // 줌 → 버블 투명도 · 마커 투명도
    pending = null;
    if (!deckInstance || !deckInstance.props.layers || !deckInstance.props.layers.length) return;
    const b = clamp((F1 - zoom) / (F1 - F0)), m = clamp((zoom - S0) / (S1 - S0));
    const key = b.toFixed(2) + "|" + m.toFixed(2);
    if (key === last) return;
    last = key;
    deckInstance.setProps({ layers: deckInstance.props.layers.map(function (l) {
      if (BUBBLES.has(l.id)) return l.clone({ opacity: b, visible: b > 0.02, pickable: b > 0.5 && l.id === "sido_bubble" });
      if (MARKERS.has(l.id)) return l.clone({ opacity: m, visible: m > 0.02 });
      return l;
    }) });
  }
  function schedule() { if (!pending) pending = requestAnimationFrame(apply); }
  const wait = setInterval(function () {      // JSON → 레이어 변환이 끝나면 처음 상태 적용
    if (deckInstance && deckInstance.props.layers && deckInstance.props.layers.length) {
      clearInterval(wait);
      deckInstance.setProps({
        getTooltip: tooltip,
        onViewStateChange: function (p) { zoom = p.viewState.zoom; schedule(); return p.viewState; },
        onClick: function (info) {               // 시도 버블을 누르면 그 지역으로 부드럽게 확대
          if (info && info.layer && info.layer.id === "sido_bubble" && info.object) {
            const o = info.object;
            deckInstance.setProps({ initialViewState: { longitude: o.lon, latitude: o.lat, zoom: S1 + 0.3,
              transitionDuration: 900 } });
          }
        }
      });
      apply();
    }
  }, 100);
})();
</script>
"""


def zoom_map_html(deck: pdk.Deck, markers: dict) -> str:
    """pydeck 지도를 HTML로 만들고 줌에 따른 버블·마커 투명도 전환·툴팁 스크립트를 덧붙인다 (st.iframe으로 표시)."""
    import json

    html = deck.to_html(as_string=True, notebook_display=False)
    # pydeck은 지도 설정(JSON)을 들여쓰기해 넣어 마커 수만큼 크기가 커진다 → 공백 없는 JSON으로 바꿔 넣음
    start = html.index("const jsonInput = ") + len("const jsonInput = ")
    end = html.index("const tooltip", start)
    end = html.rindex(";", start, end)
    compact = json.dumps(json.loads(html[start:end]), ensure_ascii=False, separators=(",", ":"))
    html = html[:start] + compact + html[end:]
    script = (_ZOOM_SCRIPT.replace("__F0__", str(FADE_START)).replace("__F1__", str(FADE_END))
              .replace("__S0__", str(SHOW_START)).replace("__S1__", str(SHOW_END))
              .replace("__BUBBLES__", str(list(BUBBLE_IDS)).replace("'", '"'))
              .replace("__MARKERS__", str(list(MARKER_IDS)).replace("'", '"'))
              .replace("__START_ZOOM__", str(deck.initial_view_state.zoom))
              .replace("__REGIONS__", json.dumps(markers["regions"], ensure_ascii=False))
              .replace("__SURNAMES__", json.dumps(markers["surnames"], ensure_ascii=False))
              .replace("__VEHICLES__", json.dumps(VEHICLE_ORDER, ensure_ascii=False))
              .replace("__TIP_STYLE__", json.dumps(TOOLTIP_STYLE)))
    return html.replace("</html>", script + "</html>")
