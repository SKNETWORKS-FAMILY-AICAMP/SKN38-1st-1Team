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
img[data-testid="stHeaderLogo"] {{ height: 40px !important; width: auto; max-width: 180px; }}
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
.jm-hero-chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 22px; }}
.jm-hero-chips span {{
    font-size: 13px; color: {MUTED}; background: {SOFT}; border: 1px solid {LINE}; padding: 6px 12px; border-radius: 999px;
}}
[class*="st-key-hero"] .stButton > button {{ min-height: 56px; font-size: 17px; padding: 0 28px; border-radius: 14px; }}

/* ── 연한 배경 섹션 — st.container(key="soft...") ─────────────── */
[class*="st-key-soft"] {{ background: {SOFT}; border-radius: 24px; padding: 32px 32px; }}

/* ── 하단 신청 유도 영역 — st.container(key="cta...") ──────────── */
[class*="st-key-cta"] {{ background: {BLUE}; border-radius: 24px; padding: 40px 44px; }}
[class*="st-key-cta"] p, [class*="st-key-cta"] h2 {{ color: #FFFFFF; }}
[class*="st-key-cta"] .stButton > button[kind="primary"] {{
    background: {YELLOW}; border-color: {YELLOW}; color: {NAVY}; min-height: 56px; font-size: 17px;
}}
[class*="st-key-cta"] .stButton > button[kind="primary"]:hover {{ background: #F5A800; border-color: #F5A800; }}
[class*="st-key-cta"] img {{ max-height: 200px; width: auto; margin: 0 auto; display: block; }}

/* ── 이용 방법 카드 ─────────────────────────────────────────────── */
.jm-how {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-top: 28px; }}
.jm-how .card {{
    background: #FFFFFF; border: 1px solid {LINE}; border-radius: 20px; padding: 22px 20px 24px;
    transition: transform .15s ease, box-shadow .15s ease;
}}
.jm-how .card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 24px rgba(17,31,63,.08); }}
.jm-how .num {{ font-size: 13px; font-weight: 800; color: {BLUE}; }}
.jm-how img {{ display: block; height: 76px; width: auto; margin: 14px 0 16px; }}
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
.jm-status .s::before {{ content: ""; position: absolute; top: 13px; left: -50%; width: 100%; height: 3px;
                         background: #E3E8F2; z-index: 0; }}
.jm-status .s:first-child::before {{ display: none; }}
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
    .jm-how {{ grid-template-columns: repeat(3, 1fr); }}
    .jm-hero-title {{ font-size: 44px; }}
}}
/* ── 모바일 ────────────────────────────────────────────────────── */
@media (max-width: 640px) {{
    [data-testid="stMainBlockContainer"] {{ padding-top: 96px; padding-left: 16px; padding-right: 16px; }}
    [data-testid="stToolbar"] {{ padding-left: 16px; padding-right: 8px; }}
    img[data-testid="stHeaderLogo"] {{ height: 32px !important; }}
    [class*="st-key-hero"] {{ padding: 8px 0 8px; }}
    .jm-hero-title {{ font-size: 34px; }}
    .jm-hero-desc {{ font-size: 16px; margin: 16px 0 22px; }}
    .jm-section-title {{ font-size: 26px; }}
    .jm-section-desc {{ font-size: 15px; }}
    .jm-how {{ grid-template-columns: repeat(2, 1fr); gap: 12px; }}
    .jm-how .card {{ padding: 18px 16px; }}
    .jm-how img {{ height: 60px; }}
    .jm-stats {{ grid-template-columns: 1fr; }}
    [class*="st-key-soft"] {{ padding: 22px 18px; }}
    [class*="st-key-cta"] {{ padding: 28px 22px; }}
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
    """HTML 카드에 넣을 이미지 (원본 파일 그대로 base64)."""
    return "data:image/png;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


def show_logo() -> None:
    st.logo(logo_image("logo1.png"), size="large")


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
            st.image(logo_image("logo4.png"), width=150)
            st.write("다마스·라보·1톤 용달을 내 짐에 맞게 연결하는  \n생활 화물 운송 중개 플랫폼")
        with links1:
            st.html('<p class="jm-foot-title">서비스</p>')
            st.page_link("pages/0_Home.py", label="홈")
            st.page_link("pages/1_Delivery_Request.py", label="운송 신청")
            st.page_link("pages/3_Booking_Lookup.py", label="예약 조회")
            st.page_link("pages/5_FAQ.py", label="FAQ")
        with links2:
            st.html('<p class="jm-foot-title">정보</p>')
            st.page_link("pages/7_Fare_Table.py", label="요금표")
            st.page_link("pages/4_Truck_Map.py", label="지역별 화물차 현황")
        st.html("<hr>")
        st.caption("SK Networks Family AI Camp 38기 1팀 프로젝트 · 본 서비스는 학습용 시연 서비스로, 실제 운송 예약·결제는 이루어지지 않습니다.")


def status_stepper(labels: list[str], current_index: int) -> None:
    """운송 상태 단계 표시 (표시 전용, 값은 DB 상태 그대로)."""
    items = []
    for i, label in enumerate(labels):
        cls = "now" if i == current_index else ("done" if i < current_index else "")
        mark = "✓" if i <= current_index else ""
        items.append(f'<div class="s {cls}"><i>{mark}</i>{label}</div>')
    st.html(f'<div class="jm-status">{"".join(items)}</div>')


def step_header(current: int, done_until: int | None = None) -> None:
    """운송 요청 5단계 중 현재 단계(1~5) 표시. 표시 전용."""
    done_until = current - 1 if done_until is None else done_until
    items = []
    for i, label in enumerate(REQUEST_STEPS, start=1):
        cls = "now" if i == current else ("done" if i <= done_until else "")
        items.append(f'<div class="jm-step {cls}"><b>{i}</b>{label}</div>')
    st.html(f'<div class="jm-steps">{"".join(items)}</div>')
