"""E-commerce KPI dashboard + AI capabilities (text-to-SQL, RAG over complaints).

Usage: streamlit run streamlit_app/app.py
"""
import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "ai"))
from rag import ask as rag_ask
from llm_client import get_llm_client
from text_to_sql import run_query

DB_PATH = str(Path(__file__).parent.parent / "warehouse" / "ecommerce.duckdb")

st.set_page_config(page_title="E-commerce Analytics", layout="wide")


def get_connection():
    """Fresh short-lived read-only connection per call.

    DuckDB connections are not safe to share across concurrent Streamlit
    sessions/threads (a shared cursor gets corrupted by interleaved calls),
    so we avoid st.cache_resource here and open a new connection each time.
    """
    return duckdb.connect(DB_PATH, read_only=True)


def load_kpis(con):
    revenue = con.execute(
        "SELECT round(sum(line_amount), 2) FROM gold.fct_transactions WHERE status = 'completed'"
    ).fetchone()[0] or 0
    aov = con.execute(
        "SELECT round(avg(order_total), 2) FROM raw.orders WHERE status = 'completed'"
    ).fetchone()[0] or 0
    cancel_rate = con.execute(
        "SELECT round(avg(cancellation_rate), 4) FROM gold.mart_customer_performance"
    ).fetchone()[0] or 0
    active_customers = con.execute(
        "SELECT count(*) FROM gold.mart_customer_performance WHERE is_active_customer"
    ).fetchone()[0] or 0
    top_products = con.execute("""
        SELECT p.product_name, p.category, round(sum(f.line_amount), 2) as revenue
        FROM gold.fct_transactions f
        JOIN gold.dim_product p ON f.product_id = p.product_id
        WHERE f.status = 'completed'
        GROUP BY 1, 2
        ORDER BY revenue DESC
        LIMIT 10
    """).df()
    return revenue, aov, cancel_rate, active_customers, top_products


revenue, aov, cancel_rate, active_customers, top_products = load_kpis(get_connection())

st.title("E-commerce Analytics Dashboard")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Revenue", f"${revenue:,.0f}")
col2.metric("Avg Order Value", f"${aov:,.2f}")
col3.metric("Cancellation Rate", f"{cancel_rate * 100:.1f}%")
col4.metric("Active Customers (180d)", f"{active_customers:,}")

st.subheader("Top 10 Products by Revenue")
st.bar_chart(top_products.set_index("product_name")["revenue"])
st.dataframe(top_products, use_container_width=True)

st.divider()
tab1, tab2 = st.tabs(["Ask a question (Text-to-SQL)", "Ask about complaints (RAG)"])

with tab1:
    st.write("Ask a natural-language question about the e-commerce data. A read-only SQL query will be generated and run.")
    question = st.text_input("Question", key="sql_question", placeholder="What are the top 5 regions by revenue?")
    if st.button("Run", key="run_sql"):
        with st.spinner("Generating SQL and running query..."):
            try:
                sql, df = run_query(DB_PATH, question)
                st.code(sql, language="sql")
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Could not answer that question: {e}")

with tab2:
    st.write("Ask about customer complaints and reviews. The answer is grounded in retrieved review excerpts.")
    rag_question = st.text_input("Question", key="rag_question", placeholder="What do customers complain about regarding shipping?")
    if st.button("Ask", key="run_rag"):
        with st.spinner("Retrieving relevant reviews and generating an answer..."):
            try:
                client = get_llm_client()
                answer, retrieved = rag_ask(get_connection(), client, rag_question)
                st.write(answer)
                with st.expander("Retrieved review excerpts"):
                    for rid, text, rating, score in retrieved:
                        st.write(f"**[review {rid}]** (rating {rating}/5, score {score:.3f}): {text}")
            except Exception as e:
                st.error(f"Could not answer that question: {e}")
