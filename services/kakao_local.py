"""카카오 주소 검색 · 위치 지도 (운송 신청 화면용)

담당 범위: 주소 검색 → 사용자가 결과 선택 → 위도·경도 확보 → 지도에 마커 표시
          거리·경로·소요시간·운임 계산은 services/fare.py에서 하며 여기서 하지 않는다.

API (카카오 개발자 문서 기준)
    - 주소 검색   GET https://dapi.kakao.com/v2/local/search/address.json  (REST API 키)
    - 키워드 검색 GET https://dapi.kakao.com/v2/local/search/keyword.json  (REST API 키, 건물명·장소명)
      응답 좌표: x = 경도(longitude), y = 위도(latitude)
    - 지도 표시   Kakao Maps JavaScript SDK (JavaScript 키 + 웹 플랫폼 도메인 등록 필요)

키 설정 (.env 또는 .streamlit/secrets.toml)
    KAKAO_REST_API_KEY    서버(파이썬)에서만 사용 — 화면에 노출하지 않음
    KAKAO_JAVASCRIPT_KEY  브라우저 지도용 (카카오가 도메인으로 사용처를 제한하는 공개용 키)
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API_BASE = "https://dapi.kakao.com/v2/local/search"
TIMEOUT = 10
RESULT_SIZE = 10
KOREA_BOUNDS = (33.0, 39.6, 124.0, 132.0)  # 위도 최소·최대, 경도 최소·최대


class KakaoApiError(RuntimeError):
    """사용자에게 그대로 보여줄 수 있는 안내 문구를 담는다 (키 값은 포함하지 않음)."""


def _secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:  # secrets.toml이 없으면 예외
        return ""


def rest_api_key() -> str:
    return _secret("KAKAO_REST_API_KEY")


def javascript_key() -> str:
    return _secret("KAKAO_JAVASCRIPT_KEY")


def _get(kind: str, params: dict) -> dict:
    key = rest_api_key()
    if not key:
        raise KakaoApiError("카카오 REST API 키가 설정되지 않아 주소를 검색할 수 없습니다. (.env의 KAKAO_REST_API_KEY)")
    try:
        resp = requests.get(f"{API_BASE}/{kind}.json", headers={"Authorization": f"KakaoAK {key}"},
                            params=params, timeout=TIMEOUT)
    except requests.RequestException:
        raise KakaoApiError("카카오 주소 검색 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.") from None
    if resp.status_code == 401:
        raise KakaoApiError("카카오 REST API 키가 올바르지 않습니다. 키 값을 확인해 주세요.")
    if resp.status_code == 403:
        raise KakaoApiError("카카오 주소 검색 권한이 없습니다. 카카오 개발자 콘솔에서 카카오맵(로컬) 사용 설정을 확인해 주세요.")
    if resp.status_code == 429:
        raise KakaoApiError("주소 검색 요청이 많습니다. 잠시 후 다시 시도해 주세요.")
    if not resp.ok:
        raise KakaoApiError(f"주소 검색 중 오류가 발생했습니다. (HTTP {resp.status_code})")
    return resp.json()


def _location(address: str, road: str | None, jibun: str | None, place: str | None, x, y, source: str) -> dict | None:
    try:
        lng, lat = float(x), float(y)  # 카카오 좌표: x = 경도, y = 위도
    except (TypeError, ValueError):
        return None
    loc = {"address": address, "road_address": road or "", "jibun_address": jibun or "",
           "place_name": place or "", "lat": lat, "lng": lng, "source": source}
    return loc if is_valid_location(loc) else None


@st.cache_data(ttl=3600, show_spinner=False)
def search_address(query: str) -> list[dict]:
    """도로명·지번 주소 + 건물명·장소명 검색 결과 (중복 제거). 같은 검색어는 1시간 캐시."""
    q = " ".join(str(query or "").split())
    if len(q) < 2:
        return []
    results, seen = [], set()

    def add(loc):
        if loc and (loc["address"], loc["place_name"]) not in seen:
            seen.add((loc["address"], loc["place_name"]))
            results.append(loc)

    for d in _get("address", {"query": q, "size": RESULT_SIZE}).get("documents", []):
        if d.get("address_type") == "REGION":  # '서울 중구'처럼 행정구역만 있는 결과는 위치가 특정되지 않아 제외
            continue
        road = (d.get("road_address") or {}).get("address_name")
        jibun = (d.get("address") or {}).get("address_name")
        building = (d.get("road_address") or {}).get("building_name")
        add(_location(road or jibun or d.get("address_name"), road, jibun, building, d.get("x"), d.get("y"), "address"))

    for d in _get("keyword", {"query": q, "size": RESULT_SIZE}).get("documents", []):
        road, jibun = d.get("road_address_name"), d.get("address_name")
        add(_location(road or jibun, road, jibun, d.get("place_name"), d.get("x"), d.get("y"), "keyword"))
    return results


def is_valid_location(loc) -> bool:
    """카카오 검색에서 선택한 위치인지 (주소 문자열 + 국내 범위의 숫자 좌표)."""
    if not isinstance(loc, dict) or not str(loc.get("address") or "").strip():
        return False
    lat, lng = loc.get("lat"), loc.get("lng")
    if isinstance(lat, bool) or isinstance(lng, bool) or not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        return False
    lat_min, lat_max, lng_min, lng_max = KOREA_BOUNDS
    return lat_min <= lat <= lat_max and lng_min <= lng <= lng_max


def result_label(loc: dict) -> str:
    """검색 결과 한 줄 표시: 장소명 · 도로명 (지번)"""
    parts = []
    if loc.get("place_name"):
        parts.append(f"{loc['place_name']} · ")
    parts.append(loc["road_address"] or loc["jibun_address"] or loc["address"])
    if loc.get("road_address") and loc.get("jibun_address"):
        parts.append(f"  (지번 {loc['jibun_address']})")
    return "".join(parts)


# ── 지도 ─────────────────────────────────────────────────────────────
def render_location_map(points: list[dict], height: int = 320) -> None:
    """선택한 위치를 지도에 마커로 표시. points: [{"label": "출발", "lat", "lng", "address"}]

    JavaScript 키가 있으면 카카오 지도, 없으면 기본 지도(pydeck)로 표시한다.
    """
    points = [p for p in points if is_valid_location(p)]
    if not points:
        return
    js_key = javascript_key()
    if js_key:
        _kakao_map(points, js_key, height)
    else:
        st.caption("카카오 JavaScript 키가 없어 기본 지도로 표시합니다. (.env의 KAKAO_JAVASCRIPT_KEY)")
        _fallback_map(points, height)


def _kakao_map(points: list[dict], js_key: str, height: int) -> None:
    data = json.dumps([{"label": p["label"], "lat": p["lat"], "lng": p["lng"], "address": p["address"]} for p in points],
                      ensure_ascii=False).replace("<", chr(92) + "u003c")  # '<'를 유니코드 이스케이프로 바꿔 주소 문자열이 <script>를 닫지 못하게
    key = html.escape(js_key, quote=True)
    st.iframe(
        f"""
<div id="map" style="width:100%;height:{height - 8}px;border-radius:12px;"></div>
<div id="msg" style="display:none;font:14px Pretendard,sans-serif;color:#282529;padding:12px;"></div>
<style>
  .pin {{ background:#2563EB;color:#fff;font:600 13px Pretendard,sans-serif;padding:4px 10px;border-radius:999px;
         box-shadow:0 2px 6px rgba(17,31,63,.25);white-space:nowrap;transform:translateY(-46px); }}
  .pin.dest {{ background:#111F3F; }}
</style>
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={key}&autoload=false"
        onerror="window.__kakaoFail=true"></script>
<script>
  const pts = {data};
  function fail() {{
    document.getElementById('map').style.display = 'none';
    const m = document.getElementById('msg'); m.style.display = 'block';
    m.textContent = '카카오 지도를 불러오지 못했습니다. JavaScript 키와 카카오 개발자 콘솔의 웹 플랫폼 도메인 등록을 확인해 주세요.';
  }}
  if (window.__kakaoFail || !window.kakao || !kakao.maps) {{ fail(); }}
  else {{
    kakao.maps.load(function () {{
      const map = new kakao.maps.Map(document.getElementById('map'),
        {{ center: new kakao.maps.LatLng(pts[0].lat, pts[0].lng), level: 4 }});
      const bounds = new kakao.maps.LatLngBounds();
      pts.forEach(function (p, i) {{
        const pos = new kakao.maps.LatLng(p.lat, p.lng);
        new kakao.maps.Marker({{ map: map, position: pos, title: p.address }});
        const el = document.createElement('div');
        el.className = 'pin' + (i > 0 ? ' dest' : '');
        el.textContent = p.label;
        new kakao.maps.CustomOverlay({{ map: map, position: pos, content: el, yAnchor: 1 }});
        bounds.extend(pos);
      }});
      if (pts.length > 1) map.setBounds(bounds, 60, 60, 60, 60);
      map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.RIGHT);
      window.__kakaoReady = true;
    }});
    setTimeout(function () {{ if (!window.__kakaoReady) fail(); }}, 5000);
  }}
</script>
""",
        height=height,
    )


def _fallback_map(points: list[dict], height: int) -> None:
    import pydeck as pdk

    data = [{"label": p["label"], "lat": p["lat"], "lng": p["lng"], "address": p["address"]} for p in points]
    lats, lngs = [p["lat"] for p in points], [p["lng"] for p in points]
    view = pdk.ViewState(latitude=sum(lats) / len(lats), longitude=sum(lngs) / len(lngs), zoom=11 if len(points) > 1 else 14)
    layers = [
        pdk.Layer("ScatterplotLayer", data, get_position=["lng", "lat"], get_radius=60, radius_min_pixels=7,
                  get_fill_color=[37, 99, 235], get_line_color=[255, 255, 255], stroked=True, line_width_min_pixels=2,
                  pickable=True),
        pdk.Layer("TextLayer", data, get_position=["lng", "lat"], get_text="label", get_size=14,
                  get_pixel_offset=[0, -22], get_color=[17, 31, 63], character_set="'auto'", font_weight=700),
    ]
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view, map_style=None,
                             tooltip={"text": "{label}: {address}"}), height=height)
