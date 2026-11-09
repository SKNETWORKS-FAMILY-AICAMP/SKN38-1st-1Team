"""FAQ 조회·검색 — MySQL faqs 우선, 비어 있거나 연결 실패 시 data/processed/jimni_faq.json

데이터는 scripts/load_faqs.py가 원본(data/faq/jimni_faq.md)에서 만든다.
화면(pages/5_FAQ.py)은 load_faqs() → filter_faqs() 순서로 사용한다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import streamlit as st

from services.db import DBConnectionError, get_connection

FAQ_JSON = Path(__file__).resolve().parents[1] / "data" / "processed" / "jimni_faq.json"
ALL = "전체"


@st.cache_data(ttl=300, show_spinner=False)
def _from_db() -> list[dict]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT faq_id, category, question, answer, source_name FROM faqs ORDER BY faq_id")
        return list(cur.fetchall())


@st.cache_data(show_spinner=False)
def _from_json(mtime: float) -> list[dict]:  # mtime: 파일이 다시 만들어지면 새로 읽음
    return json.loads(FAQ_JSON.read_text(encoding="utf-8"))["faqs"]


def load_faqs() -> tuple[list[dict], str, str | None]:
    """반환: (FAQ 목록, 데이터 출처 설명, 안내 메시지 또는 None)"""
    note = None
    try:
        rows = _from_db()
        if rows:
            return rows, "MySQL faqs", None
    except DBConnectionError as e:
        note = f"{e} 저장된 FAQ 파일로 표시합니다."
    if FAQ_JSON.exists():
        return _from_json(FAQ_JSON.stat().st_mtime), "FAQ 파일(jimni_faq.json)", note
    return [], "", note or "FAQ 데이터가 없습니다. scripts/load_faqs.py를 실행해 주세요."


DRIVER_CATEGORY = "기사님"  # 원본 '기사님 FAQ' 블록 (카테고리 표시 없음)


def categories(faqs: list[dict]) -> list[str]:
    """원본 순서 유지, 기사님 FAQ는 이용자 카테고리 뒤에 둔다."""
    seen = []
    for f in faqs:
        if f["category"] not in seen:
            seen.append(f["category"])
    seen.sort(key=lambda c: c == DRIVER_CATEGORY)
    return [ALL, *seen]


def category_label(category: str) -> str:
    return "기사님 전용" if category == DRIVER_CATEGORY else category


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).lower()


def filter_faqs(faqs: list[dict], category: str | None, keyword: str | None) -> list[dict]:
    """카테고리 + 키워드(질문·답변, 띄어쓰기로 나눈 단어를 모두 포함) 필터."""
    terms = _norm(keyword).split()
    out = []
    for f in faqs:
        if category and category != ALL and f["category"] != category:
            continue
        text = _norm(f"{f['question']} {f['answer']}")
        if all(t in text for t in terms):
            out.append(f)
    return out


def answer_markdown(answer: str) -> str:
    """원본 줄바꿈을 화면에서도 유지 (표·목록 줄은 그대로, 일반 줄은 강제 줄바꿈)."""
    lines = []
    for line in answer.split("\n"):
        stripped = line.strip()
        keep = not stripped or stripped.startswith(("|", "- ", "* ")) or re.match(r"^\d+\.\s", stripped)
        lines.append(line if keep else line + "  ")
    return "\n".join(lines)
