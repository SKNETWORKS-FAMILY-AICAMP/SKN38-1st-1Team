"""짐니 공통 UI — 테마(.streamlit/config.toml)로 표현할 수 없는 부분만 모은 곳.

- apply_global_style(): 호버 효과, 입력창·보조 글자 크기, 카드·히어로 영역 스타일 (app.py에서 한 번 호출)
- show_logo(): 상단 헤더 로고
- step_header(): 운송 요청 5단계 표시
- 화면 요소는 모두 Streamlit 기본 컴포넌트를 사용하고, CSS는 모양만 바꾼다 (클릭 동작은 Streamlit이 처리).
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / "assets"
BLUE, NAVY, PURPLE, YELLOW, TEXT, SOFT = "#2563EB", "#111F3F", "#3A3368", "#FBB71D", "#282529", "#F5F7FB"

REQUEST_STEPS = ["정보 입력", "매칭 결과", "기사님 선택", "예약하기", "예약 완료"]

_CSS = f"""
<style>
/* 제목 자간 (글자색은 테마의 #282529) */
h1, h2, h3, h4 {{ letter-spacing: -0.02em; }}

/* 입력창 글자 14px, 보조 정보 13px */
.stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input,
.stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{ font-size: 14px; }}
[data-testid="stCaptionContainer"], .stCaption {{ font-size: 13px; }}

/* 버튼: 15px, 둥근 플랫 + 호버 */
.stButton > button, .stFormSubmitButton > button, .stLinkButton > a {{
    font-size: 15px; font-weight: 600; padding: 0.55rem 1.2rem;
    transition: transform .15s ease, box-shadow .15s ease, background-color .15s ease;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stLinkButton > a:hover {{
    transform: translateY(-1px); box-shadow: 0 6px 16px rgba(37, 99, 235, .18);
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover {{
    background-color: #1D4ED8; border-color: #1D4ED8;
}}

/* 테두리 카드: 여백 넉넉하게 */
[data-testid="stVerticalBlockBorderWrapper"] > div {{ padding: 4px 4px; }}

/* 히어로(파란 카드) — st.container(key="hero...") */
[class*="st-key-hero"] {{
    background: {BLUE}; border-radius: 24px; padding: 40px 44px;
}}
[class*="st-key-hero"] h1, [class*="st-key-hero"] h2, [class*="st-key-hero"] p,
[class*="st-key-hero"] [data-testid="stCaptionContainer"] {{ color: #FFFFFF; }}
[class*="st-key-hero"] .stButton > button[kind="primary"] {{
    background: {YELLOW}; border-color: {YELLOW}; color: {NAVY};
}}
[class*="st-key-hero"] .stButton > button[kind="primary"]:hover {{
    background: #F5A800; border-color: #F5A800; color: {NAVY};
}}
[class*="st-key-hero"] .stButton > button[kind="secondary"] {{
    background: rgba(255,255,255,.12); border-color: rgba(255,255,255,.6); color: #FFFFFF;
}}

[class*="st-key-hero"] [data-testid="stCaptionContainer"] {{ opacity: .85; }}

/* 이용 방법 카드: 캐릭터 높이를 맞춰 카드 높이 통일 — st.container(key="steps...") */
[class*="st-key-steps"] img {{ height: 72px; width: auto; object-fit: contain; }}

/* 연한 배경 카드 — st.container(key="soft...") */
[class*="st-key-soft"] {{ background: {SOFT}; border-radius: 20px; padding: 24px 28px; }}

/* 단계 표시 */
.jm-steps {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 4px 0 16px; }}
.jm-step {{ flex: 1 1 120px; border-radius: 12px; padding: 10px 12px; background: {SOFT};
           color: #6B7280; font-size: 13px; line-height: 1.4; }}
.jm-step b {{ display: block; font-size: 15px; color: #6B7280; }}
.jm-step.done b, .jm-step.done {{ color: {BLUE}; }}
.jm-step.now {{ background: {BLUE}; color: #FFFFFF; }}
.jm-step.now b {{ color: #FFFFFF; }}

/* 운송 상태 단계 (예약 조회) */
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

/* 모바일 */
@media (max-width: 640px) {{
    [class*="st-key-hero"] {{ padding: 28px 22px; border-radius: 20px; }}
    [class*="st-key-soft"] {{ padding: 18px 18px; }}
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


def show_logo() -> None:
    st.logo(logo_image("logo1.png"), size="large")


def asset(name: str) -> str:
    return str(ASSETS / name)


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
