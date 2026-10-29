import streamlit as st
import pandas as pd
from analytics import answer_question, initialize_database, data_quality

st.set_page_config(page_title="Mini AI BI Assistant", page_icon="📊", layout="wide")
initialize_database()

st.title("📊 Mini AI Business Intelligence Assistant")
st.caption("Ask questions about the supplied 2026 sales transactions in plain English.")
st.info("Gemini helps interpret your question. All figures are calculated from SQLite using predefined read-only SQL queries; the model cannot write or execute SQL.")
import os
if os.getenv("GEMINI_API_KEY", "").strip():
    st.caption("AI mode: Gemini API configured (falls back to local rules if the API is unavailable).")
else:
    st.caption("AI mode: local rule-based fallback. Add GEMINI_API_KEY to a .env file to enable Gemini.")

examples = [
    "What is the total revenue?",
    "Which product generated the highest revenue?",
    "What is the monthly revenue trend?",
    "Which region generated the highest sales?",
    "How did revenue change between January and February?",
]
with st.sidebar:
    st.header("Try a question")
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["question"] = ex
    st.divider()
    st.subheader("Data quality")
    dq = data_quality()
    st.write(f"Rows loaded: **{dq['total_rows']}**")
    st.write(f"Missing/invalid prices: **{dq['missing_or_invalid_price']}**")
    st.write(f"Returned transactions: **{dq['returned_rows']}**")
    st.write(f"Zero-quantity rows: **{dq['zero_quantity_rows']}**")
    st.caption("Returned, zero-quantity, and invalid-price rows are not counted as revenue.")

question = st.text_input("Your sales question", key="question", placeholder="e.g. Which region generated the highest sales?")
if st.button("Ask assistant", type="primary") and question.strip():
    result = answer_question(question)
    if result["ok"]:
        st.subheader("Answer")
        st.success(result["answer"])
        if result["data"]:
            df = pd.DataFrame(result["data"])
            st.subheader("Supporting figures")
            st.dataframe(df, use_container_width=True, hide_index=True)
            if result["intent"] == "monthly_revenue" and "revenue" in df.columns:
                chart_df = df.set_index("month")[["revenue"]]
                st.subheader("Monthly revenue chart")
                st.bar_chart(chart_df)
        st.caption(f"Calculation method: {result.get('method', 'SQL-backed analytics')}")
    else:
        st.warning(result["answer"])
elif st.button("Show data quality"):
    st.subheader("Data quality")
    st.json(data_quality())

st.divider()
st.caption("Mini project prototype • Sales data supplied with the GET AI-Assisted Development Challenge")
