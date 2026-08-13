"""RAG over customer reviews/complaints: embed once, retrieve by cosine similarity, answer grounded in retrieved records.

Usage:
    python ai/rag.py --build-index
    python ai/rag.py --ask "What are customers complaining about with shipping?"
"""
import argparse
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
from llm_client import get_llm_client

ANSWER_SYSTEM_PROMPT = """You are a business analyst assistant for an e-commerce company.
Answer the user's question using ONLY the provided customer review excerpts.
If the excerpts don't contain enough information, say so. Keep the answer concise (2-4 sentences)
and cite review IDs like [review 123] when referencing specific feedback."""


def build_index(con, client):
    con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    con.execute("""
        CREATE TABLE IF NOT EXISTS gold.review_embeddings (
            review_id INTEGER PRIMARY KEY,
            embedding FLOAT[768]
        );
    """)
    rows = con.execute("""
        SELECT r.review_id, r.review_text
        FROM raw.reviews r
        LEFT JOIN gold.review_embeddings e ON r.review_id = e.review_id
        WHERE e.review_id IS NULL AND r.rating <= 3
    """).fetchall()

    if not rows:
        print("No new reviews to embed.")
        return

    for review_id, text in rows:
        vec = client.embed(text)
        con.execute("INSERT INTO gold.review_embeddings VALUES (?, ?)", [review_id, vec])
    print(f"Embedded {len(rows)} reviews.")


def retrieve(con, client, question: str, top_k: int = 5):
    q_vec = client.embed(question)
    rows = con.execute("""
        SELECT e.review_id, r.review_text, r.rating,
               array_cosine_similarity(e.embedding, ?::FLOAT[768]) AS score
        FROM gold.review_embeddings e
        JOIN raw.reviews r ON e.review_id = r.review_id
        ORDER BY score DESC
        LIMIT ?
    """, [q_vec, top_k]).fetchall()
    return rows


def ask(con, client, question: str, top_k: int = 5):
    retrieved = retrieve(con, client, question, top_k)
    context = "\n".join(f"[review {rid}] (rating {rating}/5): {text}" for rid, text, rating, _ in retrieved)
    prompt = f"Question: {question}\n\nReview excerpts:\n{context}"
    answer = client.generate(prompt=prompt, system=ANSWER_SYSTEM_PROMPT)
    return answer, retrieved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="warehouse/ecommerce.duckdb")
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--ask", type=str, default=None)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    con = duckdb.connect(args.db)
    client = get_llm_client()

    if args.build_index:
        build_index(con, client)

    if args.ask:
        answer, retrieved = ask(con, client, args.ask, args.top_k)
        print("Answer:\n", answer)
        print("\nRetrieved:")
        for rid, text, rating, score in retrieved:
            print(f"  [{rid}] score={score:.3f} rating={rating}: {text}")

    con.close()


if __name__ == "__main__":
    main()
