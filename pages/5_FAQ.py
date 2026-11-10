"""FAQ — 짐니 팀이 작성한 FAQ(data/faq/jimni_faq.md)를 카테고리·키워드로 조회

- 데이터: MySQL faqs → 비어 있거나 연결 실패 시 data/processed/jimni_faq.json (services/faq.py)
- 크롤링한 타사 FAQ(sendy_FAQ)는 짐니 정책이 아니므로 이 화면에서 사용하지 않는다.
- 화면 배치: 운임 요금표 → 자주 묻는 질문(카테고리 → 키워드 검색 → 질문 목록)
"""

import streamlit as st

from services.faq import ALL, answer_markdown, categories, category_label, filter_faqs, load_faqs

st.title("FAQ")

# ── 운임 요금표 (상세 표는 [요금표 보기] → 요금표 페이지) ────────────────────
with st.container(border=True):
    head, link = st.columns([3, 1], vertical_alignment="center")
    head.subheader("운임 요금표")
    if link.button("요금표 보기", width="stretch"):
        st.switch_page("pages/7_Fare_Table.py")
    st.caption("거리별 기본 운임 · 작업 추가 요금 · 계단 요금 · 수수료는 [요금표 보기]에서 확인하세요.")

# ── 자주 묻는 질문 ────────────────────────────────────────────────────
st.subheader("자주 묻는 질문")
faqs, source, note = load_faqs()
if note:
    st.warning(note)

category = st.pills("카테고리", categories(faqs), default=ALL, format_func=category_label,
                    label_visibility="collapsed") or ALL
keyword = st.text_input("키워드 검색", placeholder="궁금한 내용을 검색하세요. (질문과 답변 모두 검색)")
results = filter_faqs(faqs, category, keyword)

if keyword.strip():
    st.caption(f"'{keyword.strip()}' 검색 결과 {len(results)}건 · {category_label(category)}")
else:
    st.caption(f"{category_label(category)} {len(results)}건")

if faqs and not results:
    st.info("검색 결과가 없습니다. 다른 단어로 검색하거나 카테고리를 '전체'로 바꿔 보세요.")

for faq in results:
    with st.expander(f"Q. {faq['question']}"):
        st.markdown(answer_markdown(faq["answer"]))
        st.caption(category_label(faq["category"]))

st.caption("답변은 짐니 팀이 작성한 안내이며, 결제·예약 변경/취소 등 일부 기능과 운영 정책은 준비 중입니다.")