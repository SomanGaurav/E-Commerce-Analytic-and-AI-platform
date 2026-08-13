# E-commerce Data Platform

End-to-end data platform for a synthetic e-commerce/retail business:

**Source (synthetic data) → S3 (MinIO) → Snowflake (DuckDB) → dbt → Airflow → AI (Ollama) → Streamlit**

This is a local-first build: since there's no Snowflake/AWS/OpenAI account, this project uses
local substitutes that preserve the real architecture so swapping in real cloud services later
is a config change, not a rewrite:

| Production | Local substitute here |
|---|---|
| Snowflake | DuckDB (via `dbt-duckdb`) |
| AWS S3 | MinIO (S3-compatible, via Docker) |
| OpenAI | Ollama (local LLM), behind a swappable `ai/llm_client.py` interface |

## Architecture

```
data_generation/  -- Faker-based synthetic customers/products/orders/reviews
       |
       v
ingestion/upload_to_minio.py  -- push raw CSVs to MinIO (s3://ecommerce-raw/<entity>/dt=.../)
       |
       v
ingestion/load_bronze.py  -- MinIO -> DuckDB RAW schema (bronze)
       |
       v
dbt/ecommerce/  -- staging models (silver) -> gold dims/facts/marts, with tests
       |
       v
ai/enrichment.py, ai/rag.py, ai/text_to_sql.py  -- Ollama-backed AI capabilities
       |
       v
streamlit_app/app.py  -- KPI dashboard + text-to-SQL + RAG UI

airflow/dags/ecommerce_pipeline_dag.py orchestrates: generate -> ingest -> bronze -> dbt run -> dbt test -> enrich
```

## Prerequisites

- Docker + Docker Compose
- Python 3.12
- [Ollama](https://ollama.com) installed locally (runs on the host, not in Docker)

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
```

Pull the local LLM models (used for enrichment, RAG embeddings, and text-to-SQL):

```bash
ollama serve &
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

By default `ollama serve` binds to `127.0.0.1`, which Docker containers (Airflow) cannot reach.
For the Airflow DAG's `ai_enrichment` task to work, start Ollama bound to all interfaces instead:

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve &
```

## Running the pipeline manually (outside Airflow)

Useful for development/debugging — each step is a standalone script.

```bash
source .env && set -a

# 1. Generate synthetic data
.venv/bin/python data_generation/generate_synthetic_data.py

# 2. Bring up MinIO and ingest
docker compose up -d minio
.venv/bin/python ingestion/upload_to_minio.py

# 3. Load bronze into DuckDB
.venv/bin/python ingestion/load_bronze.py

# 4. Run dbt (staging -> gold)
.venv/bin/dbt build --project-dir dbt/ecommerce --profiles-dir dbt/ecommerce

# 5. AI enrichment (classify reviews)
.venv/bin/python ai/enrichment.py

# 6. Build the RAG index over low-rating reviews
.venv/bin/python ai/rag.py --build-index
.venv/bin/python ai/rag.py --ask "What do customers complain about regarding shipping?"

# 7. Try text-to-SQL
.venv/bin/python ai/text_to_sql.py "What was total revenue?"

# 8. Launch the dashboard
.venv/bin/streamlit run streamlit_app/app.py
```

## Running the full pipeline via Airflow

```bash
docker compose up -d minio postgres
docker compose up airflow-init          # one-time DB migration + admin user
docker compose up -d airflow-webserver airflow-scheduler
```

Airflow UI: http://localhost:8080 (user: `admin`, password: `admin`)
MinIO console: http://localhost:9001 (user/password from `.env`)

Trigger the DAG from the UI, or:

```bash
docker exec ecommerce-airflow-scheduler airflow dags trigger ecommerce_pipeline
```

The DAG runs: `generate_data >> upload_to_minio >> load_bronze >> dbt_run >> dbt_test >> ai_enrichment`.

Note: Airflow containers reach the host's Ollama server via `host.docker.internal` (mapped through
`extra_hosts` in `docker-compose.yml`), so `ollama serve` must be running on the host before
`ai_enrichment` runs.

## Repository layout

```
data_generation/   Synthetic data generator (Faker)
ingestion/         MinIO upload + bronze load into DuckDB
dbt/ecommerce/     dbt project: staging (silver) + marts (gold), with tests
ai/                llm_client.py (swappable Ollama/Gemini interface), enrichment, RAG, text-to-SQL
airflow/           Dockerfile + DAG
streamlit_app/     KPI dashboard + AI UI
docs/              Data dictionary
warehouse/         DuckDB database file (gitignored)
```

## Known limitations (first pass)

- The 3B-parameter local LLM occasionally produces malformed SQL or mis-cased string literals
  in text-to-SQL; the app catches and surfaces these errors rather than crashing.
- DuckDB is single-writer: avoid running the Streamlit app and an Airflow DAG run (or manual
  `dbt run`/enrichment scripts) against the same `warehouse/ecommerce.duckdb` file at the same time.
- RAG only indexes reviews with rating <= 3 (the complaint-relevant subset).
