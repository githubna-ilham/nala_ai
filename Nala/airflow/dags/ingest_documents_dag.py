from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_ingest():
    from app.ingest import ingest_documents

    count = ingest_documents("/opt/airflow/knowledge-base")
    print(f"Ingest selesai: {count} chunk ter-index.")


with DAG(
    dag_id="ingest_documents",
    description="Scan Nala/knowledge-base, chunk, embed, dan index ke OpenSearch",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["nala", "rag"],
) as dag:
    ingest_task = PythonOperator(
        task_id="ingest_documents",
        python_callable=run_ingest,
    )
