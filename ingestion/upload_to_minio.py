"""Upload generated raw CSVs to MinIO, partitioned by ingestion date.

Usage: python upload_to_minio.py [--raw-dir data/raw] [--bucket ecommerce-raw]
"""
import argparse
import os
from datetime import date
from pathlib import Path

from minio_client import ensure_bucket, get_s3_client

ENTITIES = ["customers", "products", "orders", "order_items", "reviews"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--bucket", default=os.environ.get("MINIO_BUCKET", "ecommerce-raw"))
    parser.add_argument("--dt", default=date.today().isoformat())
    args = parser.parse_args()

    client = get_s3_client()
    ensure_bucket(client, args.bucket)

    raw_dir = Path(args.raw_dir)
    for entity in ENTITIES:
        src = raw_dir / f"{entity}.csv"
        if not src.exists():
            print(f"skip {entity}: {src} not found")
            continue
        key = f"{entity}/dt={args.dt}/{entity}.csv"
        client.upload_file(str(src), args.bucket, key)
        print(f"uploaded {src} -> s3://{args.bucket}/{key}")


if __name__ == "__main__":
    main()
