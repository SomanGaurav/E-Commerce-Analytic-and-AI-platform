"""Classify reviews into sentiment + issue category using the LLM, write to GOLD.REVIEW_ENRICHMENT.

Usage: python ai/enrichment.py [--db warehouse/ecommerce.duckdb] [--limit 200]
"""
import argparse
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
from llm_client import get_llm_client, parse_json_response

ISSUE_CATEGORIES = [
    "shipping_delay", "product_quality", "wrong_item",
    "customer_service", "packaging_damage", "none",
]

SYSTEM_PROMPT = f"""You are a customer feedback classifier for an e-commerce company.
Given a product review, classify it and respond with ONLY a JSON object with keys:
- "sentiment": one of "positive", "neutral", "negative"
- "issue_type": one of {ISSUE_CATEGORIES}
- "urgency": one of "low", "medium", "high"
No prose, no explanation, just the JSON object."""


def classify_review(client, review_text: str) -> dict:
    raw = client.generate(prompt=review_text, system=SYSTEM_PROMPT, json_mode=True)
    try:
        result = parse_json_response(raw)
    except (ValueError, KeyError):
        result = {"sentiment": "neutral", "issue_type": "none", "urgency": "low"}
    result.setdefault("sentiment", "neutral")
    result.setdefault("issue_type", "none")
    result.setdefault("urgency", "low")
    if result["issue_type"] not in ISSUE_CATEGORIES:
        result["issue_type"] = "none"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="warehouse/ecommerce.duckdb")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    con = duckdb.connect(args.db)
    con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    con.execute("""
        CREATE TABLE IF NOT EXISTS gold.review_enrichment (
            review_id INTEGER PRIMARY KEY,
            sentiment VARCHAR,
            issue_type VARCHAR,
            urgency VARCHAR
        );
    """)

    query = (
        "SELECT r.review_id, r.review_text FROM raw.reviews r "
        "LEFT JOIN gold.review_enrichment e ON r.review_id = e.review_id "
        "WHERE e.review_id IS NULL"
    )
    if args.limit:
        query += f" LIMIT {args.limit}"
    rows = con.execute(query).fetchall()

    if not rows:
        print("No new reviews to enrich.")
        con.close()
        return

    client = get_llm_client()
    for review_id, review_text in rows:
        result = classify_review(client, review_text)
        con.execute(
            "INSERT INTO gold.review_enrichment VALUES (?, ?, ?, ?)",
            [review_id, result["sentiment"], result["issue_type"], result["urgency"]],
        )
        print(f"review {review_id}: {result['sentiment']} / {result['issue_type']} / {result['urgency']}")

    con.close()
    print(f"Enriched {len(rows)} reviews.")


if __name__ == "__main__":
    main()
