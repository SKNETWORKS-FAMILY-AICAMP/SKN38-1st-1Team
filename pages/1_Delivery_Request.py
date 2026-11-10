"""운송 신청 (요청 1단계: 정보 입력) — 홈의 [운송 신청하기]로 진입

- 출발지·도착지는 카카오 주소 검색 결과에서 선택해야만 유효 (services/kakao_local.py)
- 입력값은 services.transport_request.REQUEST_KEY로 session_state에 저장 → 매칭 결과 화면에서 사용
  (pickup_*/dropoff_* 좌표 + 기존 origin_address/dest_address 키)
- 거리·운임·차량 추천·기사 매칭은 각 담당 기능에서 계산 (이 화면에서 계산하지 않음)
"""

from base64 import b64encode
from datetime import date, datetime, time, timedelta
from html import escape

import streamlit as st

from services.kakao_local import (
    KakaoApiError,
    is_valid_location,
    render_location_map,
    result_label,
    search_address,
)
from services.transport_request import (
    FLOOR_MAX,
    FLOOR_MIN,
    HELPER_OPTIONS,
    ITEM_MAX,
    ITEM_SIZES,
    REQUEST_KEY,
    SELECTED_DRIVER_KEY,
    VEHICLE_TYPES,
    validate_request,
)
from services.fare_table import ITEM_GRADES
from services.ui import step_header

SIDES = {"pickup": "출발지", "dropoff": "도착지"}
SEL_KEY = "address_selection"   # {"pickup": 위치 dict | None, "dropoff": ...} — 페이지를 오가도 유지
DETAIL_KEY = "address_detail"   # {"pickup": 상세주소, "dropoff": ...}

# [기능 1] 상단 단계 표시 및 타이틀 설정
step_header(1)
st.title("운송 정보 입력")

# 세션에 저장된 기존 데이터 로드 (없을 경우 기본값 세팅)
saved = st.session_state.get(REQUEST_KEY, {})
default_dt = saved.get("scheduled_at") or datetime.combine(date.today() + timedelta(days=1), time(9, 0))

# 운송 조건 수정으로 돌아온 경우 선택했던 주소·상세주소 복원
if SEL_KEY not in st.session_state:
    st.session_state[SEL_KEY] = {
        side: ({"address": saved[f"{side}_address"], "lat": saved[f"{side}_lat"], "lng": saved[f"{side}_lng"],
                "road_address": saved.get(f"{side}_road_address", ""), "jibun_address": saved.get(f"{side}_jibun_address", ""),
                "place_name": saved.get(f"{side}_place_name", "")}
               if is_valid_location({"address": saved.get(f"{side}_address"), "lat": saved.get(f"{side}_lat"),
                                     "lng": saved.get(f"{side}_lng")}) else None)
        for side in SIDES
    }
    st.session_state[DETAIL_KEY] = {side: saved.get(f"{side}_detail_address", "") for side in SIDES}


FLOOR_OPTIONS = [f for f in range(FLOOR_MIN, FLOOR_MAX + 1) if f != 0]   # 0층은 없음


def floor_label(floor: int) -> str:
    return f"지하 {-floor}층" if floor < 0 else f"{floor}층"


def _icon(path: str, size: int = 18, color: str = "#2563EB") -> str:
    """선 아이콘 (st.html이 인라인 svg를 지우므로 data URI 이미지로 넣음)."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{path}</svg>')
    return f'<img src="data:image/svg+xml;base64,{b64encode(svg.encode()).decode()}" width="{size}" height="{size}" alt="">'


ICON_BUILDING = _icon('<rect x="4" y="3" width="11" height="18" rx="1.5"/><path d="M15 9h4a1 1 0 0 1 1 1v11H15"/>'
                      '<path d="M8 7h3M8 11h3M8 15h3"/>')
ICON_BOX = _icon('<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>')
ICON_BOX_SM = _icon('<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>', 16, "#9AA3B2")
ICON_CALENDAR = _icon('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>')


def section_head(no: str, title: str, desc: str, icon: str) -> None:
    """폼 구역 제목 (아이콘 · 번호 · 제목 · 설명)."""
    line = '<hr class="jm-rq-hr">' if no != "01" else ""          # 두 번째 구역부터 위에 구분선
    st.html(f'{line}<div class="jm-rq-head"><span class="ic">{icon}</span>'
            f'<div><b>{no}. {title}</b><p>{desc}</p></div></div>')


PAGE_SIZE = 5   # 검색 결과 기본 표시 개수 (나머지는 '더 보기')
PIN = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="#2563EB" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7'
       'c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5Z"/></svg>')


def _select(side: str, idx: int) -> None:
    """검색 결과 카드를 누르면 바로 선택 확정 (결과 목록은 접힘)."""
    results = st.session_state.get(f"addr_results_{side}") or []
    if 0 <= idx < len(results):
        st.session_state[SEL_KEY][side] = results[idx]
        st.session_state.pop(f"addr_results_{side}", None)
        st.session_state.pop(f"addr_more_{side}", None)


def _reset(side: str) -> None:
    st.session_state[SEL_KEY][side] = None
    st.session_state[DETAIL_KEY][side] = ""
    st.session_state.pop(f"addr_results_{side}", None)
    st.session_state.pop(f"addr_more_{side}", None)


def _keep_detail(side: str) -> None:
    st.session_state[DETAIL_KEY][side] = st.session_state.get(f"addr_detail_{side}", "").strip()


def _address_lines(loc: dict) -> tuple[str, str, str]:
    """(제목, 도로명 주소, 지번 주소) — 장소명이 없으면 도로명(없으면 지번)을 제목으로."""
    road = loc.get("road_address") or ""
    jibun = loc.get("jibun_address") or ""
    title = loc.get("place_name") or road or jibun or loc["address"]
    road_line = road if road and road != title else ""
    jibun_line = jibun if jibun and jibun != title else ""
    return title, road_line, jibun_line


def _address_html(loc: dict) -> str:
    title, road, jibun = (escape(t) for t in _address_lines(loc))
    return (f'<p class="t">{title}</p>' + (f'<p class="r">{road}</p>' if road else "")
            + (f'<p class="j">지번 {jibun}</p>' if jibun else ""))


def address_picker(side: str, label: str) -> None:
    """출발지·도착지 공통: 검색 전(입력+검색) → 검색 후(결과 카드) → 선택 후(요약 카드+상세주소+재검색)."""
    selected = st.session_state[SEL_KEY].get(side)
    with st.container(key=f"jm_addr_box_{side}"):
        st.html(f'<p class="jm-addr-label">{label}</p>')
        if selected:
            st.html(f'<div class="jm-addr-selected"><p class="k">{PIN}<span>선택된 {label}</span></p>'
                    f"{_address_html(selected)}</div>")
            st.session_state.setdefault(f"addr_detail_{side}", st.session_state[DETAIL_KEY].get(side, ""))
            # 상세주소: Enter 또는 [입력] 버튼으로 저장
            d_col, s_col = st.columns([4, 1], vertical_alignment="bottom")
            d_col.text_input(f"{label} 상세주소 (선택)", key=f"addr_detail_{side}", max_chars=100,
                             placeholder="동·호수, 층 등", on_change=_keep_detail, args=(side,))
            s_col.button("입력", key=f"addr_detail_save_{side}", on_click=_keep_detail, args=(side,),
                         width="stretch")
            saved_detail = st.session_state[DETAIL_KEY].get(side, "")
            if saved_detail:
                st.caption(f":material/check: 상세주소 저장됨: {saved_detail}")
            st.button("다른 주소로 다시 검색", key=f"addr_reset_{side}", on_click=_reset, args=(side,),
                      icon=":material/search:", type="tertiary")
            return

        # 작은 폼으로 감싸 검색어 입력 후 Enter를 눌러도 [주소 검색]과 똑같이 검색된다
        with st.form(f"addr_form_{side}", border=False, enter_to_submit=True):
            q_col, b_col = st.columns([4, 1], vertical_alignment="bottom")
            query = q_col.text_input(f"{label} 주소 검색", key=f"addr_query_{side}",
                                     placeholder="도로명·지번 주소 또는 건물명 (예: 세종대로 110, 서울시청)")
            searched = b_col.form_submit_button("주소 검색", key=f"addr_search_{side}", type="primary",
                                                width="stretch")
        if searched:
            st.session_state.pop(f"addr_more_{side}", None)
            if len(" ".join(query.split())) < 2:
                st.session_state[f"addr_results_{side}"] = []
                st.warning("검색어를 2글자 이상 입력해 주세요.")
            else:
                try:
                    st.session_state[f"addr_results_{side}"] = search_address(query)
                except KakaoApiError as e:
                    st.session_state.pop(f"addr_results_{side}", None)
                    st.error(str(e))
                else:
                    if not st.session_state[f"addr_results_{side}"]:
                        st.warning("검색 결과가 없습니다. 도로명·지번 주소나 건물명을 다시 확인해 주세요.")

        results = st.session_state.get(f"addr_results_{side}")
        if results:
            shown = results if st.session_state.get(f"addr_more_{side}") else results[:PAGE_SIZE]
            st.html(f'<p class="jm-addr-hint">{label} 검색 결과 {len(results)}건 — 주소를 눌러 선택해 주세요</p>')
            for i, loc in enumerate(shown):
                # 카드 전체를 덮는 투명 버튼(st.button)으로 클릭을 받는다 → 화면은 카드, 동작은 Streamlit 버튼
                with st.container(key=f"jm_addr_card_{side}_{i}"):
                    st.html(f'<div class="jm-addr-card">{_address_html(loc)}</div>')
                    st.button(result_label(loc), key=f"addr_choose_{side}_{i}", on_click=_select, args=(side, i),
                              width="stretch")
            if len(results) > PAGE_SIZE and not st.session_state.get(f"addr_more_{side}"):
                if st.button(f"검색 결과 더 보기 ({len(results) - PAGE_SIZE}건)", key=f"addr_more_btn_{side}",
                             type="tertiary", icon=":material/expand_more:"):
                    st.session_state[f"addr_more_{side}"] = True
                    st.rerun()
        st.caption("검색 결과에서 주소를 선택해야 다음 단계로 진행할 수 있어요.")


left = st.container()  # 단계 표시와 같은 전체 폭 사용 (예전 3:1 칸 나눔은 오른쪽이 비어 왼쪽으로 쏠려 보였음)

with left:
    st.caption(f"운송 차량: {' · '.join(VEHICLE_TYPES)} (입력한 짐에 맞춰 추천 예정)")

    # [기능 2-1] 출발지 및 도착지 주소 검색 (카카오) — 검색 버튼이 필요해 폼 밖에 둔다
    st.markdown("**출발지 · 도착지**")
    for side, label in SIDES.items():
        address_picker(side, label)

    selection = st.session_state[SEL_KEY]
    render_location_map([{**loc, "label": SIDES[side]} for side, loc in selection.items() if loc])

    # [기능 2-2] 운송 정보 입력 폼 구성 (01 건물 정보 · 02 물품 정보 · 03 일정·추가 인력)
    with st.form("transport_request_form"):
        # 01. 건물 정보: 층수 · 엘리베이터
        section_head("01", "건물 정보", "짐을 싣고 내리는 장소의 작업 환경을 알려 주세요.", ICON_BUILDING)
        c1, c2 = st.columns(2, gap="large")
        floors = {}
        for col, side, key in ((c1, "출발지", "origin"), (c2, "도착지", "dest")):
            with col, st.container(key=f"rq_place_{key}"):
                st.html(f'<p class="jm-rq-side">{side}</p>')
                floor = saved.get(f"{key}_floor", 1)
                floors[key] = st.selectbox("층수", FLOOR_OPTIONS, format_func=floor_label, key=f"rq_{key}_floor",
                                           index=FLOOR_OPTIONS.index(floor) if floor in FLOOR_OPTIONS else FLOOR_OPTIONS.index(1))
                floors[f"{key}_elev"] = st.radio("엘리베이터", ["있음", "없음"], horizontal=True, key=f"rq_{key}_elev",
                                                 index=0 if saved.get(f"{key}_has_elevator", True) else 1)
        origin_floor, origin_elev = floors["origin"], floors["origin_elev"]
        dest_floor, dest_elev = floors["dest"], floors["dest_elev"]
        st.caption("엘리베이터가 없으면 1층 기준 한 층마다 계단 작업 요금이 더해져요. (출발지·도착지 각각)")

        # 02. 물품 정보: 크기별 개수 (기존 2단계 estimate 함수 호환을 위해 소문자 키로 저장)
        section_head("02", "물품 정보", "운송할 짐의 크기별 개수를 입력해 주세요.", ICON_BOX)
        counts = {}
        for row in (ITEM_SIZES[:2], ITEM_SIZES[2:]):
            for col, size in zip(st.columns(2), row):
                key = f"item_{size.lower()}_count"
                with col, st.container(key=f"rq_item_{size.lower()}"):
                    st.html(f'<div class="jm-rq-item"><b>{size} 사이즈</b>{ICON_BOX_SM}'
                            f'<span>{escape(ITEM_GRADES[size]["description"])}</span></div>')
                    counts[key] = st.number_input(f"{size} 개수", min_value=0, max_value=ITEM_MAX, step=1,
                                                  value=saved.get(key, 0), label_visibility="collapsed")

        # 03. 운송 일정 및 추가 인력
        section_head("03", "운송 일정 및 추가 인력", "원하는 날짜와 운반 도움 여부를 선택해 주세요.", ICON_CALENDAR)
        with st.container(key="rq_schedule"):
            c3, c4 = st.columns(2, gap="large")
            sched_date = c3.date_input("희망 운송 날짜", value=default_dt.date(), min_value=date.today())
            sched_time = c4.time_input("시간", value=default_dt.time(), step=timedelta(minutes=30))

            helper_keys = list(HELPER_OPTIONS)
            helper = st.radio("추가 인력", helper_keys, format_func=HELPER_OPTIONS.get, horizontal=True,
                              index=helper_keys.index(saved.get("helper_option", "NONE")) if saved.get("helper_option", "NONE") in helper_keys else 0)

        # 폼 제출 버튼
        submitted = st.form_submit_button("매칭 시작하기", type="primary", width="stretch")

    # [기능 3] 입력 데이터 검증 및 세션 저장 후 페이지 이동
    if submitted:
        pickup, dropoff = selection.get("pickup") or {}, selection.get("dropoff") or {}
        details = st.session_state[DETAIL_KEY]
        request = {
            # 카카오 검색으로 선택한 위치 (거리 계산 연결용)
            **{f"pickup_{k}": pickup.get(k) for k in ("address", "lat", "lng", "road_address", "jibun_address", "place_name")},
            **{f"dropoff_{k}": dropoff.get(k) for k in ("address", "lat", "lng", "road_address", "jibun_address", "place_name")},
            "pickup_detail_address": details.get("pickup", ""),
            "dropoff_detail_address": details.get("dropoff", ""),
            # 기존 키 (fare.estimate_request·매칭 화면 호환) — 상세주소 없이 기본 주소만
            "origin_address": pickup.get("address", ""),
            "dest_address": dropoff.get("address", ""),
            "origin_floor": int(origin_floor),
            "origin_has_elevator": origin_elev == "있음",
            "dest_floor": int(dest_floor),
            "dest_has_elevator": dest_elev == "있음",
            **{k: int(v) for k, v in counts.items()},
            "scheduled_at": datetime.combine(sched_date, sched_time),
            "helper_option": helper,
        }

        # 유효성 검사 실행
        errors = validate_request(request)
        if errors:
            for msg in errors:
                st.error(msg)
        else:
            # 세션에 요청 데이터 저장 및 이전 기사 선택 초기화
            st.session_state[REQUEST_KEY] = request
            st.session_state.pop(SELECTED_DRIVER_KEY, None)

            # 다음 단계(기사 매칭 및 운임 계산 결과) 페이지로 이동
            st.switch_page("pages/2_Driver_Matching.py")

# [기능 4] 홈으로 돌아가기 버튼
if st.button("홈으로"):
    st.switch_page("pages/0_Home.py")
