from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

AIRFLOW_HOME = "/opt/airflow"
DBT_PROJECT_DIR = f"{AIRFLOW_HOME}/dbt/ecommerce"

default_args = {
    "owner": "data-eng",
    "retries": 0,
}

with DAG(
    dag_id="ecommerce_pipeline",
    description="Generate synthetic e-commerce data, ingest to MinIO, load bronze in DuckDB, run dbt, enrich reviews",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    default_args=default_args,
    tags=["ecommerce", "medallion"],
) as dag:

    generate_data = BashOperator(
        task_id="generate_data",
        bash_command=f"cd {AIRFLOW_HOME} && python data_generation/generate_synthetic_data.py --out-dir data/raw",
    )

    upload_to_minio = BashOperator(
        task_id="upload_to_minio",
        bash_command=f"cd {AIRFLOW_HOME} && python ingestion/upload_to_minio.py --raw-dir data/raw",
    )

    load_bronze = BashOperator(
        task_id="load_bronze",
        bash_command=f"cd {AIRFLOW_HOME} && python ingestion/load_bronze.py --db {AIRFLOW_HOME}/warehouse/ecommerce.duckdb",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {AIRFLOW_HOME} && dbt run --project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROJECT_DIR}",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {AIRFLOW_HOME} && dbt test --project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROJECT_DIR}",
    )

    ai_enrichment = BashOperator(
        task_id="ai_enrichment",
        bash_command=f"cd {AIRFLOW_HOME} && python ai/enrichment.py --db {AIRFLOW_HOME}/warehouse/ecommerce.duckdb --limit 50",
    )

    generate_data >> upload_to_minio >> load_bronze >> dbt_run >> dbt_test >> ai_enrichment
