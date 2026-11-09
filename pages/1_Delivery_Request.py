"""운송 신청 (요청 1단계: 정보 입력) — 홈의 [운송 신청하기]로 진입

- 출발지·도착지는 카카오 주소 검색 결과에서 선택해야만 유효 (services/kakao_local.py)
- 입력값은 services.transport_request.REQUEST_KEY로 session_state에 저장 → 매칭 결과 화면에서 사용
  (pickup_*/dropoff_* 좌표 + 기존 origin_address/dest_address 키)
- 거리·운임·차량 추천·기사 매칭은 각 담당 기능에서 계산 (이 화면에서 계산하지 않음)
"""

from datetime import date, datetime, time, timedelta
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


def _select(side: str) -> None:
    """검색 결과 라디오에서 고르면 바로 선택 확정."""
    idx = st.session_state.get(f"addr_pick_{side}")
    results = st.session_state.get(f"addr_results_{side}") or []
    if idx is not None and 0 <= idx < len(results):
        st.session_state[SEL_KEY][side] = results[idx]
        st.session_state.pop(f"addr_results_{side}", None)


def _reset(side: str) -> None:
    st.session_state[SEL_KEY][side] = None
    st.session_state[DETAIL_KEY][side] = ""
    st.session_state.pop(f"addr_results_{side}", None)


def _keep_detail(side: str) -> None:
    st.session_state[DETAIL_KEY][side] = st.session_state.get(f"addr_detail_{side}", "").strip()


def address_picker(side: str, label: str) -> None:
    """주소 검색 → 결과 선택 → (선택됨) 주소 표시 + 상세주소 입력."""
    selected = st.session_state[SEL_KEY].get(side)
    with st.container(border=True):
        st.markdown(f"**{label}**")
        if selected:
            name = f"{selected['place_name']} · " if selected.get("place_name") else ""
            st.success(f"{name}{selected['address']}", icon=":material/location_on:")
            if selected.get("road_address") and selected.get("jibun_address"):
                st.caption(f"지번 {selected['jibun_address']}")
            st.session_state.setdefault(f"addr_detail_{side}", st.session_state[DETAIL_KEY].get(side, ""))
            st.text_input(f"{label} 상세주소 (선택)", key=f"addr_detail_{side}", max_chars=100,
                          placeholder="동·호수, 층 등", on_change=_keep_detail, args=(side,))
            st.button("다른 주소로 다시 검색", key=f"addr_reset_{side}", on_click=_reset, args=(side,))
            return

        q_col, b_col = st.columns([4, 1], vertical_alignment="bottom")
        query = q_col.text_input(f"{label} 주소 검색", key=f"addr_query_{side}",
                                 placeholder="도로명·지번 주소 또는 건물명 (예: 세종대로 110, 서울시청)")
        if b_col.button("주소 검색", key=f"addr_search_{side}", width="stretch"):
            st.session_state.pop(f"addr_pick_{side}", None)
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
            st.radio(f"{label} 검색 결과 — 주소를 선택해 주세요", list(range(len(results))), index=None,
                     format_func=lambda i: result_label(results[i]), key=f"addr_pick_{side}",
                     on_change=_select, args=(side,))
        st.caption("검색 결과에서 주소를 선택해야 다음 단계로 진행할 수 있어요.")


left, _ = st.columns([3, 1])

with left:
    st.caption(f"운송 차량: {' · '.join(VEHICLE_TYPES)} (입력한 짐에 맞춰 추천 예정)")

    # [기능 2-1] 출발지 및 도착지 주소 검색 (카카오) — 검색 버튼이 필요해 폼 밖에 둔다
    st.markdown("**출발지 · 도착지**")
    for side, label in SIDES.items():
        address_picker(side, label)

    selection = st.session_state[SEL_KEY]
    render_location_map([{**loc, "label": SIDES[side]} for side, loc in selection.items() if loc])

    # [기능 2-2] 운송 정보 입력 폼 구성
    with st.form("transport_request_form"):
        # 1-2. 층수 및 엘리베이터 여부 입력
        c1, c2 = st.columns(2)
        with c1:
            origin_floor = st.number_input("출발지 층수", min_value=FLOOR_MIN, max_value=FLOOR_MAX, step=1,
                                           value=saved.get("origin_floor", 1))
            origin_elev = st.radio("출발지 엘리베이터", ["있음", "없음"], horizontal=True,
                                   index=0 if saved.get("origin_has_elevator", True) else 1)
        with c2:
            dest_floor = st.number_input("도착지 층수", min_value=FLOOR_MIN, max_value=FLOOR_MAX, step=1,
                                         value=saved.get("dest_floor", 1))
            dest_elev = st.radio("도착지 엘리베이터", ["있음", "없음"], horizontal=True,
                                 index=0 if saved.get("dest_has_elevator", True) else 1)

        # 1-3. 물품 크기별 개수 입력 (기존 2단계 estimate 함수 호환을 위해 소문자 키로 저장)
        st.markdown("**물품 크기별 개수**")
        item_cols = st.columns(len(ITEM_SIZES))
        counts = {}
        for col, size in zip(item_cols, ITEM_SIZES):
            # 대소문자 차이로 인한 매칭 오류 방지를 위해 소문자 키(item_s_count 등)로 통일
            key = f"item_{size.lower()}_count"
            counts[key] = col.number_input(size, min_value=0, max_value=ITEM_MAX, step=1, value=saved.get(key, 0))

        # 1-4. 희망 일시 및 추가 인력 선택
        st.markdown("**희망 운송 일시 · 추가 인력**")
        c3, c4 = st.columns(2)
        sched_date = c3.date_input("날짜", value=default_dt.date(), min_value=date.today())
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
