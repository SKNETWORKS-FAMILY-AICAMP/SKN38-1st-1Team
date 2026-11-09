"""짐니 FAQ 원본(Notion 내보내기 md) → JSON 변환 · MySQL faqs 적재

원본: data/faq/jimni_faq.md  (팀이 작성한 짐니 FAQ. 크롤링한 타사 FAQ인 sendy_FAQ는 사용하지 않음)
출력: data/processed/jimni_faq.json  (화면은 DB faqs가 비어 있으면 이 파일을 읽음)

변환 규칙
    - '#### [ 이용자 FAQ ]' / '#### [ 기사님 FAQ ]' 아래 <aside> 블록만 FAQ로 사용
    - <aside> 안의 '**#카테고리**' → category (카테고리 표시가 없는 기사님 블록은 '기사님')
    - 들여쓰기 없는 '- 질문' 다음의 4칸 들여쓴 줄들 → 답변 (줄바꿈·표·목록 유지)
    - 맨 아래 '피드백 정리'(팀 내부 메모)와 상단 '카테고리/키워드 검색형' 표는 FAQ가 아니므로 제외

검증: 질문·답변 짝(빈 답변 없음), 질문 중복, DB 컬럼 길이(category 50자, question 255자)

실행
    python scripts/load_faqs.py           JSON 생성 + 적재 미리보기 (DB에 쓰지 않음)
    python scripts/load_faqs.py --apply   MySQL faqs에 적재 (이미 있는 질문은 건너뜀, 트랜잭션)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SOURCE_MD = ROOT / "data" / "faq" / "jimni_faq.md"
OUT_JSON = ROOT / "data" / "processed" / "jimni_faq.json"
SOURCE_NAME = "짐니 FAQ (팀 작성)"   # faqs.source_name VARCHAR(50)
DRIVER_CATEGORY = "기사님"
MAX_CATEGORY, MAX_QUESTION = 50, 255
SECTIONS = {"이용자 FAQ": "이용자", "기사님 FAQ": "기사님"}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse(md_text: str) -> list[dict]:
    faqs, audience, category, in_aside = [], None, None, False
    question, answer_lines = None, []

    def flush():
        nonlocal question, answer_lines
        if question is not None:
            lines = [ln.rstrip() for ln in answer_lines]
            while lines and not lines[0]:
                lines.pop(0)
            while lines and not lines[-1]:
                lines.pop()
            # 원본에서 #기타·#문의/신고접수 블록이 '기사님 FAQ' 제목 아래에 있지만 내용은 이용자용이므로
            # 카테고리 표시가 없는 블록만 기사님 FAQ로 본다.
            faqs.append({"audience": "이용자" if category else "기사님", "category": category or DRIVER_CATEGORY,
                         "question": question.strip(), "answer": "\n".join(lines)})
        question, answer_lines = None, []

    for raw in md_text.splitlines():
        line = raw.rstrip("\n")
        header = re.match(r"^####\s*\[\s*(.+?)\s*\]", line)
        if header:
            flush()
            audience = SECTIONS.get(header.group(1))
            continue
        if line.strip() == "<aside>":
            in_aside, category = True, None
            continue
        if line.strip() == "</aside>":
            flush()
            in_aside = False
            continue
        if not in_aside or audience is None:
            continue
        if "피드백 정리" in line:  # 팀 내부 메모 블록
            audience = None
            continue
        cat = re.match(r"^\*\*#(.+?)\*\*", line.strip())
        if cat and question is None:
            category = cat.group(1).strip()
            continue
        if line.startswith("- "):           # 들여쓰기 없는 목록 = 새 질문
            flush()
            question = line[2:]
            continue
        if question is not None:
            answer_lines.append(line[4:] if line.startswith("    ") else line.strip())
    flush()
    for i, f in enumerate(faqs, start=1):
        f["faq_id"] = i
    return faqs


def validate(faqs: list[dict]) -> list[str]:
    problems = []
    for f in faqs:
        if not f["question"] or not f["answer"].strip():
            problems.append(f"질문·답변 짝 없음: {f['question'][:30]!r}")
        if len(f["category"]) > MAX_CATEGORY:
            problems.append(f"카테고리 {MAX_CATEGORY}자 초과: {f['category']}")
        if len(f["question"]) > MAX_QUESTION:
            problems.append(f"질문 {MAX_QUESTION}자 초과: {f['question'][:30]}")
    dup = [q for q, n in Counter(_norm(f["question"]) for f in faqs).items() if n > 1]
    if dup:
        problems.append(f"중복 질문: {dup}")
    return problems


def check_fares(faqs: list[dict]) -> list[str]:
    """FAQ에 적힌 운임·추가요금이 예준님 운임표(services/fare_table.py)와 같은지 확인."""
    from services.fare_table import FARE_RULES, SERVICE_RULES

    notes = []
    fare_faq = next((f for f in faqs if f["question"].startswith("운송 요금은 얼마")), None)
    if fare_faq:
        for rule in FARE_RULES:
            row = f"| {rule['min']}~{rule['max']}km | " + " | ".join(
                f"{rule['fares'][v]:,}" for v in ("다마스", "라보", "1톤")) + " |"
            if row not in fare_faq["answer"]:
                notes.append(f"운임표 불일치: {row}")
    text = "\n".join(f["answer"] for f in faqs)
    for key, label in (("DRIVER_HELP", "상·하차"), ("WORKER_1", "추가 작업자 1명"), ("WORKER_2", "추가 작업자 2명")):
        if f"{SERVICE_RULES[key]['fee']:,}원" not in text:
            notes.append(f"추가요금 불일치: {label} {SERVICE_RULES[key]['fee']:,}원")
    return notes


def apply_to_db(faqs: list[dict]) -> tuple[int, int]:
    from services.db import get_connection

    inserted = skipped = 0
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT faq_id, category, question FROM faqs FOR UPDATE")
                rows = cur.fetchall()
                existing = {(r["category"], _norm(r["question"])) for r in rows}
                next_id = max((r["faq_id"] for r in rows), default=0) + 1
                for f in faqs:
                    if (f["category"], _norm(f["question"])) in existing:
                        skipped += 1
                        continue
                    cur.execute(
                        "INSERT INTO faqs (faq_id, category, question, answer, source_name, source_url, crawled_at) "
                        "VALUES (%s, %s, %s, %s, %s, NULL, NULL)",
                        (next_id, f["category"], f["question"], f["answer"], SOURCE_NAME),
                    )
                    next_id += 1
                    inserted += 1
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return inserted, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="짐니 FAQ 변환·적재")
    parser.add_argument("--apply", action="store_true", help="MySQL faqs에 적재 (기본은 미리보기)")
    args = parser.parse_args()

    faqs = parse(SOURCE_MD.read_text(encoding="utf-8"))
    problems = validate(faqs)
    print(f"원본: {SOURCE_MD.relative_to(ROOT)} → FAQ {len(faqs)}건")
    for (aud, cat), n in Counter((f["audience"], f["category"]) for f in faqs).items():
        print(f"  [{aud}] {cat}: {n}건")
    if problems:
        print("[검증 실패]", *problems, sep="\n  ")
        return 1
    print("검증: 질문·답변 짝 OK, 중복 없음, 길이 OK")
    fare_notes = check_fares(faqs)
    print("운임표 대조(fare_table.py):", "일치" if not fare_notes else fare_notes)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"source": str(SOURCE_MD.relative_to(ROOT)).replace("\\", "/"),
                                    "source_name": SOURCE_NAME, "faqs": faqs}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"저장: {OUT_JSON.relative_to(ROOT)}")

    if not args.apply:
        print("\n[미리보기] DB에 쓰지 않았습니다. 적재 대상:")
        for f in faqs:
            print(f"  {f['faq_id']:>2}. [{f['category']}] {f['question']}  (답변 {len(f['answer'])}자)")
        print("적재하려면: python scripts/load_faqs.py --apply")
        return 0
    inserted, skipped = apply_to_db(faqs)
    print(f"MySQL faqs 적재 완료: 추가 {inserted}건, 이미 있어 건너뜀 {skipped}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
