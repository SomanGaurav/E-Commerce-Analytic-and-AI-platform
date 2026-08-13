"""Load latest raw partition from MinIO into DuckDB RAW schema tables.

Usage: python load_bronze.py [--db warehouse/ecommerce.duckdb] [--bucket ecommerce-raw]
"""
import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
from minio_client import get_s3_client

ENTITIES = ["customers", "products", "orders", "order_items", "reviews"]


def latest_partition_key(client, bucket: str, entity: str) -> str | None:
    resp = client.list_objects_v2(Bucket=bucket, Prefix=f"{entity}/")
    contents = resp.get("Contents", [])
    if not contents:
        return None
    latest = max(contents, key=lambda o: o["LastModified"])
    return latest["Key"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="warehouse/ecommerce.duckdb")
    parser.add_argument("--bucket", default=os.environ.get("MINIO_BUCKET", "ecommerce-raw"))
    args = parser.parse_args()

    endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    access_key = os.environ.get("MINIO_ROOT_USER", "minioadmin")
    secret_key = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin123")
    host = urlparse(endpoint).netloc

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db)
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"""
        SET s3_endpoint='{host}';
        SET s3_access_key_id='{access_key}';
        SET s3_secret_access_key='{secret_key}';
        SET s3_url_style='path';
        SET s3_use_ssl=false;
    """)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")

    client = get_s3_client()
    for entity in ENTITIES:
        key = latest_partition_key(client, args.bucket, entity)
        if key is None:
            print(f"skip {entity}: no objects found in bucket {args.bucket}")
            continue
        s3_path = f"s3://{args.bucket}/{key}"
        table = f"raw.{entity}"
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto('{s3_path}');")
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"loaded {table} <- {s3_path} ({count} rows)")

    con.close()


if __name__ == "__main__":
    main()
