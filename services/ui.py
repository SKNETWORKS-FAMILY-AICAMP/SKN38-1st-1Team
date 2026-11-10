"""짐니 공통 UI — 테마(.streamlit/config.toml)로 표현할 수 없는 부분만 모은 곳.

- apply_global_style(): 헤더·본문 폭·버튼·입력창·카드·히어로·푸터 스타일 (app.py에서 한 번 호출)
- show_logo() / render_footer(): 모든 페이지 공통 헤더 로고와 푸터 (app.py)
- step_header(), status_stepper(), how_it_works(): 표시 전용 HTML 조각
- 화면 요소(버튼·링크·입력)는 모두 Streamlit 기본 컴포넌트를 사용하고, CSS는 모양만 바꾼다.

디자인 기준: 팀 디자인 가이드(메인 #2563EB · 네이비 #111F3F · 퍼플 #3A3368 · 옐로우 #FBB71D,
본문 #282529, Pretendard Medium) + 큰 제목·넉넉한 여백·분명한 버튼의 단순한 섹션 구성.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st
from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / "assets"
BLUE, BLUE_DARK, NAVY, PURPLE, YELLOW, TEXT, SOFT = (
    "#2563EB", "#1D4ED8", "#111F3F", "#3A3368", "#FBB71D", "#282529", "#F5F7FB")
MUTED, LINE = "#5B6475", "#E6EBF3"

REQUEST_STEPS = ["정보 입력", "매칭 결과", "기사님 선택", "예약하기", "예약 완료"]
STEP_DETAILS = [  # (캐릭터, 설명) — 홈 '이용 방법' 카드
    ("jimni2.png", "출발지·도착지와 짐 크기, 원하는 날짜를 입력해요."),
    ("jimni6.png", "거리와 짐에 맞는 차량과 예상 운임을 확인해요."),
    ("jimni3.png", "추천 기사님의 차량과 이력을 보고 골라요."),
    ("jimni4.png", "이름과 연락처만으로 간편하게 예약해요."),
    ("jimni5.png", "예약번호로 운송 상태를 언제든 확인해요."),
]

_CSS = f"""
<style>
/* ── 기본 타이포 ─────────────────────────────────────────────── */
h1, h2, h3, h4 {{ letter-spacing: -0.025em; color: {NAVY}; }}
[data-testid="stCaptionContainer"], .stCaption {{ font-size: 13px; color: {MUTED}; }}

/* ── 헤더: 76px, 로고 왼쪽 · 메뉴 오른쪽, 본문 폭에 정렬 ─────────── */
header[data-testid="stHeader"] {{
    height: 76px; background: rgba(255,255,255,.94); backdrop-filter: saturate(180%) blur(8px);
    border-bottom: 1px solid {LINE};
}}
[data-testid="stToolbar"] {{
    height: 76px; padding-left: max(24px, calc((100vw - 1180px) / 2)); padding-right: max(16px, calc((100vw - 1180px) / 2 - 8px));
}}
img[data-testid="stHeaderLogo"] {{ height: 34px !important; width: auto; max-width: 240px; }}
nav[data-testid="stTopNav"] {{ margin-left: auto; justify-content: flex-end; gap: 4px; }}
a[data-testid="stTopNavLink"] {{
    height: 42px; padding: 0 18px; border-radius: 999px; transition: background-color .15s ease, color .15s ease;
}}
a[data-testid="stTopNavLink"] p {{ font-size: 15px; font-weight: 600; color: {TEXT}; }}
a[data-testid="stTopNavLink"]:hover {{ background: #EEF3FF; }}
a[data-testid="stTopNavLink"]:hover p, a[data-testid="stTopNavLink"]:hover span {{ color: {BLUE}; }}
a[data-testid="stTopNavLink"][aria-current="page"] {{ background: #EAF1FF; }}
a[data-testid="stTopNavLink"][aria-current="page"] p,
a[data-testid="stTopNavLink"][aria-current="page"] span {{ color: {BLUE}; font-weight: 700; }}

/* ── 본문 폭·여백 통일 ───────────────────────────────────────── */
[data-testid="stMainBlockContainer"] {{
    max-width: 1180px; padding-top: 112px; padding-left: 24px; padding-right: 24px; padding-bottom: 32px;
}}
[data-testid="stMainBlockContainer"] h1 {{ margin-bottom: 4px; }}

/* ── 버튼: 높이 48px, 둥근 플랫 + 호버 ─────────────────────────── */
.stButton > button, .stFormSubmitButton > button, .stLinkButton > a {{
    min-height: 48px; font-size: 15px; font-weight: 600; padding: 0 22px; border-radius: 12px;
    transition: transform .15s ease, box-shadow .15s ease, background-color .15s ease, border-color .15s ease;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stLinkButton > a:hover {{
    transform: translateY(-1px); box-shadow: 0 6px 16px rgba(37, 99, 235, .16);
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover {{
    background-color: {BLUE_DARK}; border-color: {BLUE_DARK};
}}

/* ── 입력창: 높이 44px, 글자 14px ─────────────────────────────── */
.stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input,
.stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{ font-size: 14px; }}
.stTextInput div[data-baseweb="input"], .stNumberInput div[data-baseweb="input"],
.stDateInput div[data-baseweb="input"], .stTimeInput div[data-baseweb="select"] > div,
.stSelectbox div[data-baseweb="select"] > div {{ min-height: 44px; }}

/* ── 카드: 테두리·반경 통일 ───────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] > div {{ padding: 8px 8px; }}
[data-testid="stExpander"] details {{ border-radius: 14px; border-color: {LINE}; }}
[data-testid="stExpander"] summary:hover {{ color: {BLUE}; }}

/* ── 섹션 제목 (눈썹 문구 + 큰 제목) ───────────────────────────── */
.jm-eyebrow {{ color: {BLUE}; font-weight: 700; font-size: 15px; margin: 0 0 6px; }}
.jm-section-title {{ font-size: 32px; font-weight: 800; color: {NAVY}; letter-spacing: -0.03em; line-height: 1.3; margin: 0; }}
.jm-section-desc {{ font-size: 17px; color: {MUTED}; margin: 10px 0 0; line-height: 1.6; }}

/* ── 히어로 — st.container(key="hero...") : 흰 배경 · 큰 제목 · 오른쪽 일러스트 ── */
[class*="st-key-hero"] {{ padding: 40px 0 24px; }}
.jm-hero-badge {{
    display: inline-block; padding: 7px 14px; border-radius: 999px; background: #EAF1FF; color: {BLUE};
    font-size: 14px; font-weight: 700; margin-bottom: 20px;
}}
.jm-hero-title {{
    font-size: 52px; font-weight: 800; line-height: 1.22; letter-spacing: -0.035em; color: {NAVY}; margin: 0;
}}
.jm-hero-title .hl {{ color: {BLUE}; background: linear-gradient(transparent 62%, rgba(251,183,29,.45) 62%); }}
.jm-hero-desc {{ font-size: 19px; line-height: 1.65; color: {MUTED}; margin: 22px 0 30px; }}
.jm-hero-desc-row {{ display: flex; align-items: center; gap: 18px; margin: 22px 0 30px; }}
.jm-hero-desc-row .jm-hero-desc {{ margin: 0; }}
.jm-hero-desc-row img {{ height: 3.3em; width: auto; flex: none; font-size: 19px; }}   /* 돋보기 (sub2): 설명 2줄 높이 */
.jm-hero-chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 22px; }}
.jm-hero-chips span {{
    font-size: 13px; color: {MUTED}; background: {SOFT}; border: 1px solid {LINE}; padding: 6px 12px; border-radius: 999px;
}}
[class*="st-key-hero"] .stButton > button {{ min-height: 56px; font-size: 17px; padding: 0 28px; border-radius: 14px; }}

/* ── 연한 배경 섹션 — st.container(key="soft...") ─────────────── */
[class*="st-key-soft"] {{ background: {SOFT}; border-radius: 24px; padding: 32px 32px; }}

/* ── 홈 공공데이터 소개 숫자 카드 ─────────────────────────────── */
.jm-home-stat {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 20px; padding: 22px 24px; }}
.jm-home-stat .label {{ font-size: 14px; font-weight: 600; color: {MUTED}; margin: 0; }}
.jm-home-stat .value {{ font-size: 40px; font-weight: 800; color: {NAVY}; letter-spacing: -0.03em; margin: 6px 0 4px; }}
.jm-home-stat .value span {{ font-size: 22px; font-weight: 700; margin-left: 2px; }}
.jm-home-stat .note {{ font-size: 13px; color: {MUTED}; margin: 0; }}

/* ── 화물차 현황: 데이터 안내 · 출처 카드 ─────────────────────── */
.jm-note {{ background: {SOFT}; border-radius: 20px; padding: 24px 26px; height: 100%; box-sizing: border-box; }}
.jm-note h4, .jm-source h4 {{ font-size: 17px; font-weight: 700; color: {NAVY}; margin: 0 0 10px; }}
.jm-note p {{ font-size: 15px; line-height: 1.7; color: {TEXT}; margin: 0; }}
.jm-note ul {{ margin: 14px 0 0; padding: 0; list-style: none; }}
.jm-note li {{ font-size: 13px; color: {MUTED}; line-height: 1.6; padding-left: 14px; position: relative; }}
.jm-note li::before {{ content: ""; position: absolute; left: 2px; top: 9px; width: 5px; height: 5px;
                       border-radius: 50%; background: {BLUE}; opacity: .5; }}
.jm-source {{ border: 1px solid {LINE}; border-radius: 20px; padding: 24px 26px; height: 100%; box-sizing: border-box; }}
.jm-source dl {{ display: grid; grid-template-columns: 64px 1fr; gap: 10px 16px; margin: 0 !important; padding: 0 !important; font-size: 14px; }}
.jm-source dt {{ margin: 0; padding: 0; color: {MUTED}; font-weight: 600; }}
.jm-source dd {{ margin: 0; padding: 0; color: {TEXT}; word-break: keep-all; }}
.jm-source a {{ color: {BLUE}; font-weight: 600; text-decoration: none; }}
.jm-source a:hover {{ text-decoration: underline; }}
.jm-source .foot {{ font-size: 12px; color: {MUTED}; margin: 16px 0 0; line-height: 1.6; }}

/* ── 화물차 현황 지도: 둥근 카드 + 오른쪽 아래 범례 ───────────────────── */
[class*="st-key-map_wrap"] {{ position: relative; gap: 0; }}
[class*="st-key-map_wrap"] [data-testid="stDeckGlJsonChart"] {{
    border-radius: 20px; overflow: hidden; border: 1px solid {LINE}; box-shadow: 0 10px 30px rgba(37, 99, 235, .08);
}}
/* 배경 지도만 연한 블루 톤으로 (버블·글자는 영향 없음) */
[class*="st-key-map_wrap"] .mapboxgl-canvas {{ filter: grayscale(1) sepia(.35) hue-rotate(192deg) saturate(3) brightness(1.02); }}
[class*="st-key-map_wrap"] [data-testid="stElementContainer"]:has(.jm-map-legend) {{
    position: absolute; bottom: 34px; right: 14px; z-index: 5; width: auto; pointer-events: none;
}}
.jm-map-legend {{ background: rgba(255,255,255,.94); border: 1px solid {LINE}; border-radius: 14px; padding: 12px 14px;
                  box-shadow: 0 6px 18px rgba(17,31,63,.08); font-size: 12px; color: {TEXT}; }}
.jm-map-legend b {{ display: block; font-size: 13px; color: {NAVY}; margin-bottom: 6px; }}
.jm-map-legend ul {{ list-style: none; margin: 0; padding: 0; }}
.jm-map-legend li {{ display: flex; align-items: center; gap: 8px; margin: 4px 0 0; }}
.jm-map-legend i {{ width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(37,99,235,.25); flex: none; }}

/* ── 운송 신청: 출발지·도착지 주소 검색 (같은 디자인) ───────────────── */
[class*="st-key-jm_addr_box"] {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 18px; padding: 20px 22px;
                                 gap: 8px; }}
.jm-addr-label {{ font-size: 16px; font-weight: 700; color: {NAVY}; margin: 0; }}
.jm-addr-hint {{ font-size: 13px; color: {MUTED}; margin: 2px 0 -4px; }}
.jm-addr-card p, .jm-addr-selected p {{ margin: 0; }}
.jm-addr-card .t, .jm-addr-selected .t {{ font-size: 16px; font-weight: 700; color: {NAVY}; line-height: 1.4; }}
.jm-addr-card .r, .jm-addr-selected .r {{ font-size: 14px; color: {TEXT}; margin-top: 3px; line-height: 1.5; }}
.jm-addr-card .j, .jm-addr-selected .j {{ font-size: 13px; color: {MUTED}; margin-top: 2px; line-height: 1.5; }}
/* 검색 결과 카드는 목록이라 한 단계 작게 */
.jm-addr-card .t {{ font-size: 14px; line-height: 1.35; }}
.jm-addr-card .r {{ font-size: 13px; margin-top: 1px; line-height: 1.4; }}
.jm-addr-card .j {{ font-size: 12px; margin-top: 0; line-height: 1.4; }}
/* 검색 결과 카드: 카드 전체를 덮는 투명 버튼으로 클릭 */
[class*="st-key-jm_addr_card"] {{ position: relative; gap: 0; }}
.jm-addr-card {{ border: 1px solid {LINE}; border-radius: 12px; padding: 9px 14px; background: #FFFFFF; pointer-events: none;
                 transition: border-color .12s ease, background-color .12s ease; word-break: keep-all; overflow-wrap: anywhere; }}
[class*="st-key-jm_addr_card"]:hover .jm-addr-card {{ border-color: {BLUE}; background: #F5F8FF; }}
[class*="st-key-jm_addr_card"]:has(button:focus-visible) .jm-addr-card,
[class*="st-key-jm_addr_card"]:has(button:active) .jm-addr-card {{ border-color: {BLUE}; background: #EAF1FF; }}
[class*="st-key-jm_addr_card"] [data-testid="stElementContainer"]:has(.stButton) {{
    position: absolute; inset: 0; z-index: 10; margin: 0; }}
[class*="st-key-jm_addr_card"] [data-testid="stElementContainer"]:not(:has(.stButton)) {{ pointer-events: none; }}
[class*="st-key-jm_addr_card"] .stButton, [class*="st-key-jm_addr_card"] .stButton > div {{ height: 100%; }}
[class*="st-key-jm_addr_card"] .stButton > button, [class*="st-key-jm_addr_card"] .stButton button {{
    width: 100%; height: 100%; min-height: 0; opacity: 0; cursor: pointer; }}
/* 상세주소: [입력] 버튼이 있으므로 'Press Enter' 안내는 숨김 (Enter도 그대로 동작) */
[class*="st-key-jm_addr_box"] [data-testid="InputInstructions"] {{ display: none; }}
/* [주소 검색] 버튼을 입력창과 같은 높이·같은 줄에 맞춤 */
[class*="st-key-jm_addr_box"] .stFormSubmitButton > button {{ min-height: 40px; height: 40px; }}
[class*="st-key-jm_addr_box"] [data-testid="stForm"] {{ padding: 0; }}
/* '다른 주소로 다시 검색': 작은 보조 버튼 */
[class*="st-key-addr_reset"] button {{ min-height: 32px; padding: 0 10px 0 6px; font-size: 13px; color: {MUTED}; }}
[class*="st-key-addr_reset"] button p {{ font-size: 13px; }}
[class*="st-key-addr_reset"] button:hover {{ color: {BLUE}; transform: none; box-shadow: none; background: #F3F7FF; }}
/* 선택된 주소 요약 카드 */
.jm-addr-selected {{ background: #F3F7FF; border: 1px solid #BFD3FB; border-radius: 14px; padding: 16px 18px;
                     word-break: keep-all; overflow-wrap: anywhere; }}
.jm-addr-selected .k {{ display: flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 700;
                        color: {BLUE}; margin-bottom: 6px; }}

/* ── 예약하기: 최종 운임·작업 조건 카드 ───────────────────────────── */
.jm-terms {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 18px; padding: 24px 26px; }}
.jm-terms-title {{ font-size: 20px; font-weight: 800; color: {NAVY}; margin: 0; }}
.jm-terms-sub {{ font-size: 14px; color: {MUTED}; margin: 4px 0 18px; }}
.jm-terms dl.grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 24px;
                     margin: 0 !important; padding: 0 !important; }}
.jm-terms dd, .jm-notice dd, .jm-notice dl {{ margin-left: 0 !important; }}
.jm-terms dl.grid div {{ min-width: 0; }}
.jm-terms dt {{ font-size: 13px; font-weight: 600; color: {MUTED}; margin: 0 0 2px; }}
.jm-terms dd {{ font-size: 15px; color: {TEXT}; margin: 0; line-height: 1.5; word-break: keep-all; overflow-wrap: anywhere; }}
.jm-terms dd small {{ display: block; font-size: 13px; color: {MUTED}; }}
.jm-terms table.fare {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: {SOFT}; border-radius: 14px;
                        overflow: hidden; }}
.jm-terms table.fare th, .jm-terms table.fare td {{ padding: 10px 16px; font-size: 14px; border: 0; }}
.jm-terms table.fare th {{ text-align: left; font-weight: 500; color: {TEXT}; }}
.jm-terms table.fare td {{ text-align: right; color: {TEXT}; white-space: nowrap; }}
.jm-terms table.fare tr.total th, .jm-terms table.fare tr.total td {{ border-top: 1px solid {LINE}; font-size: 17px;
                                                                    font-weight: 800; color: {NAVY}; padding: 14px 16px; }}
.jm-terms table.fare tr.total td {{ color: {BLUE}; font-size: 20px; }}
.jm-terms-note {{ font-size: 12px; color: {MUTED}; margin: 12px 0 0; }}
[class*="st-key-jm_booking_form"] {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 18px; padding: 20px 22px;
                                     gap: 12px; }}
[class*="st-key-jm_booking_form"] .stCheckbox {{ background: #F3F7FF; border: 1px solid #BFD3FB; border-radius: 12px;
                                                 padding: 12px 14px; }}
[class*="st-key-jm_booking_form"] .stCheckbox p {{ font-weight: 600; color: {NAVY}; }}

/* ── 매칭 완료 팝업 (st.dialog) ─────────────────────────────────── */
[data-testid="stDialog"] [role="dialog"] {{ border-radius: 22px !important; animation: jm-pop-in .28s cubic-bezier(.2, .8, .3, 1) both; }}
@keyframes jm-pop-in {{ from {{ opacity: 0; transform: scale(.94) translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
@media (prefers-reduced-motion: reduce) {{ [data-testid="stDialog"] [role="dialog"] {{ animation: none; }} }}
.jm-match-pop {{ text-align: center; padding: 4px 4px 8px; }}
.jm-match-pop img {{ height: 96px; width: auto; display: block; margin: 0 auto 10px; }}
.jm-match-pop .t {{ font-size: 22px; font-weight: 800; color: {NAVY}; margin: 0; line-height: 1.35; word-break: keep-all; }}
.jm-match-pop .d {{ font-size: 15px; color: {MUTED}; margin: 8px 0 16px; line-height: 1.6; }}
.jm-match-pop dl {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0; margin: 0 !important; padding: 0 !important;
                    background: #F3F7FF; border: 1px solid #BFD3FB; border-radius: 14px; overflow: hidden; }}
.jm-match-pop dl div {{ padding: 12px 10px; }}
.jm-match-pop dl div + div {{ border-left: 1px solid #BFD3FB; }}
.jm-match-pop dt {{ font-size: 12px; font-weight: 600; color: {MUTED}; margin: 0; }}
.jm-match-pop dd {{ font-size: 16px; font-weight: 800; color: {BLUE}; margin: 2px 0 0 !important; word-break: keep-all; }}
.jm-match-pop .n {{ font-size: 12px; color: {MUTED}; margin: 12px 0 0; }}

/* ── 웹 알림 카드 (매칭 완료·기사 출발·운송 완료) ─────────────────────── */
.jm-notice {{ display: flex; gap: 16px; align-items: flex-start; background: #F3F7FF; border: 1px solid #BFD3FB;
              border-radius: 18px; padding: 20px 22px; }}
.jm-notice .ic {{ font-size: 28px; line-height: 1; }}
.jm-notice .body {{ min-width: 0; flex: 1; }}
.jm-notice .t {{ font-size: 20px; font-weight: 800; color: {NAVY}; margin: 0; }}
.jm-notice .d {{ font-size: 15px; color: {TEXT}; margin: 6px 0 0; line-height: 1.6; }}
.jm-notice dl {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px 20px; margin: 16px 0 0;
                 padding: 14px 16px; background: #FFFFFF; border-radius: 12px; }}
.jm-notice dt {{ font-size: 12px; font-weight: 600; color: {MUTED}; margin: 0; padding: 0; }}
.jm-notice dd {{ font-size: 15px; font-weight: 700; color: {NAVY}; margin: 2px 0 0; padding: 0; overflow-wrap: anywhere; }}
@media (max-width: 640px) {{
    .jm-terms {{ padding: 20px 18px; }}
    .jm-terms dl.grid {{ grid-template-columns: 1fr; }}
    .jm-notice {{ padding: 18px 16px; gap: 12px; }}
}}

/* ── 이용 방법 카드 ─────────────────────────────────────────────── */
.jm-how {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-top: 28px; }}
.jm-how .card {{
    background: #FFFFFF; border: 1px solid {LINE}; border-radius: 20px; padding: 22px 20px 24px;
    transition: transform .15s ease, box-shadow .15s ease;
}}
.jm-how .card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 24px rgba(17,31,63,.08); }}
.jm-how .num {{ font-size: 13px; font-weight: 800; color: {BLUE}; }}
.jm-how img {{ display: block; height: 104px; width: auto; margin: 12px 0 14px; }}
.jm-how h4 {{ font-size: 18px; font-weight: 700; margin: 0 0 6px; color: {NAVY}; }}
.jm-how p {{ font-size: 14px; line-height: 1.55; color: {MUTED}; margin: 0; }}

/* ── 요약 숫자 카드 ─────────────────────────────────────────────── */
.jm-stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
.jm-stats .stat {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 20px; padding: 22px 24px; }}
.jm-stats .label {{ font-size: 14px; color: {MUTED}; margin: 0; }}
.jm-stats .value {{ font-size: 28px; font-weight: 800; color: {NAVY}; letter-spacing: -0.02em; margin: 6px 0 0; }}
.jm-stats .sub {{ font-size: 13px; color: {MUTED}; margin: 4px 0 0; }}

/* ── 단계 표시 (운송 신청 흐름) ─────────────────────────────────── */
.jm-steps {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 0 0 20px; }}
.jm-step {{ flex: 1 1 120px; border-radius: 14px; padding: 12px 14px; background: {SOFT};
           color: #6B7280; font-size: 13px; line-height: 1.4; }}
.jm-step b {{ display: block; font-size: 15px; color: #6B7280; }}
.jm-step.done b, .jm-step.done {{ color: {BLUE}; }}
.jm-step.now {{ background: {BLUE}; color: #FFFFFF; }}
.jm-step.now b {{ color: #FFFFFF; }}

/* ── 운송 상태 단계 (예약 조회) ─────────────────────────────────── */
.jm-status {{ display: flex; align-items: flex-start; margin: 8px 0 4px; }}
.jm-status .s {{ flex: 1; text-align: center; position: relative; font-size: 13px; color: #9CA3AF; }}
.jm-status img {{ display: block; height: 72px; width: auto; margin: 0 auto 8px; transition: transform .15s ease; }}
.jm-status .s:not(.done):not(.now) img {{ filter: grayscale(1); opacity: .35; }}   /* 아직 오지 않은 단계는 흐리게 */
.jm-status .s.now img {{ transform: scale(1.1); }}
.jm-status .s::before {{ content: ""; position: absolute; top: 13px; left: -50%; width: 100%; height: 3px;
                         background: #E3E8F2; z-index: 0; }}
.jm-status .s:first-child::before {{ display: none; }}
.jm-status.has-img .s::before {{ top: 93px; }}   /* 그림(72px)+여백(8px) 아래 동그라미 가운데 */
.jm-status .s i {{ display: block; width: 28px; height: 28px; margin: 0 auto 6px; border-radius: 50%;
                   background: #E3E8F2; position: relative; z-index: 1; font-style: normal; line-height: 28px;
                   color: #FFFFFF; font-size: 14px; }}
.jm-status .s.done, .jm-status .s.now {{ color: {BLUE}; }}
.jm-status .s.done i, .jm-status .s.now i {{ background: {BLUE}; }}
.jm-status .s.done::before, .jm-status .s.now::before {{ background: {BLUE}; }}
.jm-status .s.now {{ font-weight: 700; }}

/* ── 푸터 — st.container(key="footer") ──────────────────────────── */
/* 카드가 아닌 화면 맨 아래 가로 전체 띠로 표시 (홈 하단 파란 안내 영역과 구분) */
[class*="st-key-footer"] {{ background: {NAVY}; border-radius: 0; padding: 40px 0 28px; margin-top: 88px;
    margin-bottom: -32px; box-shadow: 0 0 0 100vmax {NAVY}; clip-path: inset(0 -100vmax -100vmax); }}
[class*="st-key-footer"] p, [class*="st-key-footer"] [data-testid="stCaptionContainer"] {{ color: rgba(255,255,255,.72); }}
[class*="st-key-footer"] .jm-foot-title {{ color: #FFFFFF; font-weight: 700; font-size: 15px; margin: 0 0 6px; }}
[class*="st-key-footer"] a[data-testid="stPageLink-NavLink"] {{ padding: 4px 0; background: transparent; }}
[class*="st-key-footer"] a[data-testid="stPageLink-NavLink"] p {{ color: rgba(255,255,255,.86); font-size: 14px; }}
[class*="st-key-footer"] a[data-testid="stPageLink-NavLink"]:hover p {{ color: {YELLOW}; }}
[class*="st-key-footer"] hr {{ border-color: rgba(255,255,255,.14); margin: 20px 0 14px; }}

/* ── 태블릿 ────────────────────────────────────────────────────── */
@media (max-width: 1024px) {{
    a[data-testid="stTopNavLink"] {{ padding: 0 10px; }}
    a[data-testid="stTopNavLink"] p {{ font-size: 14px; }}
    nav[data-testid="stTopNav"] {{ gap: 0; }}
    img[data-testid="stHeaderLogo"] {{ height: 28px !important; max-width: 190px; }}
    .jm-how {{ grid-template-columns: repeat(3, 1fr); }}
    .jm-hero-title {{ font-size: 44px; }}
}}
/* ── 모바일 ────────────────────────────────────────────────────── */
@media (max-width: 640px) {{
    [data-testid="stMainBlockContainer"] {{ padding-top: 96px; padding-left: 16px; padding-right: 16px; }}
    [data-testid="stToolbar"] {{ padding-left: 16px; padding-right: 8px; }}
    img[data-testid="stHeaderLogo"] {{ height: 26px !important; max-width: 170px; }}
    [class*="st-key-hero"] {{ padding: 8px 0 8px; }}
    .jm-hero-title {{ font-size: 34px; }}
    .jm-hero-desc {{ font-size: 16px; margin: 16px 0 22px; }}
    .jm-hero-desc-row {{ margin: 16px 0 22px; gap: 10px; }}
    .jm-hero-desc-row img {{ font-size: 16px; }}
    .jm-section-title {{ font-size: 26px; }}
    .jm-section-desc {{ font-size: 15px; }}
    .jm-how {{ grid-template-columns: repeat(2, 1fr); gap: 12px; }}
    .jm-how .card {{ padding: 18px 16px; }}
    .jm-how img {{ height: 80px; }}
    .jm-status img {{ height: 48px; }}
    .jm-status.has-img .s::before {{ top: 69px; }}
    .jm-stats {{ grid-template-columns: 1fr; }}
    [class*="st-key-soft"] {{ padding: 22px 18px; }}
    .jm-home-stat .value {{ font-size: 32px; }}
    .jm-map-legend {{ padding: 8px 10px; font-size: 11px; }}
    .jm-map-legend b {{ font-size: 12px; margin-bottom: 2px; }}
    [class*="st-key-footer"] {{ padding: 28px 0 20px; margin-top: 64px; }}
    h1 {{ font-size: 26px !important; }}
}}
</style>
"""


def apply_global_style() -> None:
    st.html(_CSS)


@st.cache_resource(show_spinner=False)
def logo_image(name: str) -> Image.Image:
    """로고 이미지의 투명 여백을 잘라 작은 크기에서도 잘 보이게 한다 (원본 파일은 수정하지 않음)."""
    im = Image.open(ASSETS / name).convert("RGBA")
    box = im.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    return im.crop(box) if box else im


@st.cache_data(show_spinner=False)
def image_data_uri(name: str) -> str:
    """HTML 카드에 넣을 이미지 (원본 파일 그대로 base64, png·jpg)."""
    mime = "image/jpeg" if name.lower().endswith((".jpg", ".jpeg")) else "image/png"
    return f"data:{mime};base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


@st.cache_resource(show_spinner=False)
def trimmed_image(name: str, pad: int = 12) -> Image.Image:
    """흰 배경 이미지의 바깥 흰 여백을 잘라 낸다 (원본 파일은 수정하지 않음)."""
    im = Image.open(ASSETS / name).convert("RGB")
    mask = im.convert("L").point(lambda v: 255 if v < 245 else 0)   # 거의 흰색이 아닌 부분
    box = mask.getbbox()
    if not box:
        return im
    l, t, r, b = box
    return im.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, im.width), min(b + pad, im.height)))


def show_logo() -> None:
    st.logo(logo_image("logo_main.png"), size="large")


def asset(name: str) -> str:
    return str(ASSETS / name)


def section_title(eyebrow: str, title: str, desc: str | None = None) -> None:
    """섹션 제목 (눈썹 문구 + 큰 제목 + 설명). 표시 전용."""
    desc_html = f'<p class="jm-section-desc">{desc}</p>' if desc else ""
    st.html(f'<div><p class="jm-eyebrow">{eyebrow}</p><h2 class="jm-section-title">{title}</h2>{desc_html}</div>')


def how_it_works() -> None:
    """홈 '이용 방법' 5단계 카드. 표시 전용."""
    cards = "".join(
        f'<div class="card"><div class="num">STEP {i:02d}</div>'
        f'<img src="{image_data_uri(img)}" alt="{label} 단계 지니 캐릭터">'
        f"<h4>{label}</h4><p>{desc}</p></div>"
        for i, (label, (img, desc)) in enumerate(zip(REQUEST_STEPS, STEP_DETAILS), start=1)
    )
    st.html(f'<div class="jm-how">{cards}</div>')


def stat_cards(items: list[tuple[str, str, str]]) -> None:
    """요약 숫자 카드 [(라벨, 값, 보조 설명)]. 표시 전용 — 값은 호출하는 쪽의 실제 데이터."""
    cards = "".join(f'<div class="stat"><p class="label">{a}</p><p class="value">{b}</p><p class="sub">{c}</p></div>'
                    for a, b, c in items)
    st.html(f'<div class="jm-stats">{cards}</div>')


def render_footer() -> None:
    """모든 페이지 공통 푸터. 링크는 st.page_link (실제 페이지 이동)."""
    with st.container(key="footer"):
        brand, links1, links2 = st.columns([2, 1, 1], gap="large")
        with brand:
            st.image(logo_image("logo_white.png"), width=190)   # 남색 푸터용 흰색 로고 (가로형)
            st.write("다마스·라보·1톤 용달을 내 짐에 맞게 연결하는  \n생활 화물 운송 중개 플랫폼")
        with links1:
            st.html('<p class="jm-foot-title">서비스</p>')
            st.page_link("pages/0_Home.py", label="홈")
            st.page_link("pages/1_Delivery_Request.py", label="운송 신청")
            st.page_link("pages/4_Truck_Map.py", label="화물차 현황")
            st.page_link("pages/3_Booking_Lookup.py", label="예약 조회")
            st.page_link("pages/5_FAQ.py", label="FAQ")
        with links2:
            st.html('<p class="jm-foot-title">정보</p>')
            st.page_link("pages/7_Fare_Table.py", label="요금표")
        st.html("<hr>")
        st.caption("SK Networks Family AI Camp 38기 1팀 프로젝트")


def status_stepper(labels: list[str], current_index: int, images: list[str] | None = None) -> None:
    """운송 상태 단계 표시 (표시 전용, 값은 DB 상태 그대로). images: 단계별 지니 그림 파일명."""
    items = []
    for i, label in enumerate(labels):
        cls = "now" if i == current_index else ("done" if i < current_index else "")
        mark = "✓" if i <= current_index else ""
        img = f'<img src="{image_data_uri(images[i])}" alt="">' if images else ""
        items.append(f'<div class="s {cls}">{img}<i>{mark}</i>{label}</div>')
    st.html(f'<div class="jm-status{" has-img" if images else ""}">{"".join(items)}</div>')


def step_header(current: int, done_until: int | None = None) -> None:
    """운송 요청 5단계 중 현재 단계(1~5) 표시. 표시 전용."""
    done_until = current - 1 if done_until is None else done_until
    items = []
    for i, label in enumerate(REQUEST_STEPS, start=1):
        cls = "now" if i == current else ("done" if i <= done_until else "")
        items.append(f'<div class="jm-step {cls}"><b>{i}</b>{label}</div>')
    st.html(f'<div class="jm-steps">{"".join(items)}</div>')
