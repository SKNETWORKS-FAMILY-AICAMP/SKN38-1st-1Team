"""FAQ — 짐니 팀이 작성한 FAQ(data/faq/jimni_faq.md)를 카테고리·키워드로 조회

- 데이터: MySQL faqs → 비어 있거나 연결 실패 시 data/processed/jimni_faq.json (services/faq.py)
- 크롤링한 타사 FAQ(sendy_FAQ)는 짐니 정책이 아니므로 이 화면에서 사용하지 않는다.
- 화면 배치는 디자인 시안(검색 → 운임 요금표 → 자주 묻는 질문 카테고리)을 따른다.
"""

import streamlit as st

from services.db import DBConnectionError
from services.faq import ALL, answer_markdown, categories, category_label, filter_faqs, load_faqs
from services.fare_rules_db import load_fare_rules

st.title("FAQ")
keyword = st.text_input("키워드 검색", placeholder="궁금한 내용을 검색하세요. (질문과 답변 모두 검색)")

# ── 운임 요금표 (요금 카테고리는 맨 위 요금표로 안내) ────────────────────
with st.container(border=True):
    head, link = st.columns([3, 1], vertical_alignment="center")
    head.subheader("운임 요금표")
    if link.button("요금표 보기", width="stretch"):
        st.switch_page("pages/7_Fare_Table.py")
    try:
        fares = load_fare_rules()
        if fares.empty:
            st.caption("요금표가 아직 확정되지 않았습니다. 운임 기준이 등록되면 이곳에 표시됩니다.")
        else:
            st.dataframe(fares[["차종", "기본요금(원)", "km당 요금(원)"]], hide_index=True)
            st.caption("확정 전 운임 기준으로 참고용입니다.")
    except DBConnectionError as e:
        st.caption(str(e))

# ── 자주 묻는 질문 ────────────────────────────────────────────────────
st.subheader("자주 묻는 질문")
faqs, source, note = load_faqs()
if note:
    st.warning(note)

category = st.pills("카테고리", categories(faqs), default=ALL, format_func=category_label,
                    label_visibility="collapsed") or ALL
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
