"""Natural-language question -> SQL against the DuckDB gold layer, executed read-only.

Usage: python ai/text_to_sql.py "What was total revenue last month?"
"""
import argparse
import re
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
from llm_client import get_llm_client

SCHEMA_DESCRIPTION = """
Available tables (DuckDB, schema-qualified):

gold.dim_customer(customer_id, first_name, last_name, email, signup_date, region, segment)
gold.dim_product(product_id, product_name, category, cost, price, margin)
gold.dim_date(date_day, year, month, day, day_of_week, year_month)
gold.fct_transactions(order_item_id, order_id, customer_id, product_id, order_date, status, quantity, unit_price, line_amount)
gold.mart_customer_performance(customer_id, first_name, last_name, region, segment, total_orders,
    completed_orders, cancelled_orders, returned_orders, total_revenue, avg_order_value,
    cancellation_rate, first_order_date, last_order_date, is_active_customer)

Note: fct_transactions.status and dim_customer-related order statuses are always lowercase:
'completed', 'cancelled', or 'returned'. Never use a capitalized status value.
For "average order value" questions, prefer gold.mart_customer_performance.avg_order_value
or aggregate order_total from raw.orders rather than averaging line-item unit_price.
"""

SYSTEM_PROMPT = f"""You are a SQL generator for a DuckDB e-commerce analytics database.
{SCHEMA_DESCRIPTION}
Rules:
- Generate ONLY a single read-only SELECT query, no other statement types.
- Use only the tables/columns listed above.
- Respond with ONLY the SQL query, no markdown fences, no explanation.
- Only revenue from 'completed' orders/order_items should count as revenue unless asked otherwise.
"""

FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|copy|pragma|call|export|import)\b",
    re.IGNORECASE,
)


def generate_sql(client, question: str) -> str:
    raw = client.generate(prompt=question, system=SYSTEM_PROMPT)
    sql = raw.strip()
    sql = re.sub(r"^```(sql)?", "", sql).strip()
    sql = re.sub(r"```$", "", sql).strip()
    return sql


def validate_sql(sql: str):
    if not sql.lower().lstrip().startswith("select"):
        raise ValueError(f"Only SELECT statements are allowed, got: {sql[:50]}")
    if FORBIDDEN_KEYWORDS.search(sql):
        raise ValueError(f"Query contains a forbidden keyword: {sql}")


def run_query(db_path: str, question: str):
    client = get_llm_client()
    sql = generate_sql(client, question)
    validate_sql(sql)

    con = duckdb.connect(db_path, read_only=True)
    df = con.execute(sql).df()
    con.close()
    return sql, df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", type=str)
    parser.add_argument("--db", default="warehouse/ecommerce.duckdb")
    args = parser.parse_args()

    sql, df = run_query(args.db, args.question)
    print(f"Generated SQL:\n{sql}\n")
    print(df.to_string())


if __name__ == "__main__":
    main()
