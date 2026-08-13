FROM apache/airflow:2.10.3-python3.12

COPY requirements-dev.txt /requirements-dev.txt
RUN pip install --no-cache-dir -r /requirements-dev.txt

ENV PYTHONPATH="/opt/airflow/ai:/opt/airflow/ingestion:/opt/airflow/data_generation:${PYTHONPATH}"
