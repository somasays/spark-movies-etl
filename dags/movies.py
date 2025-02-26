from typing import Optional, Dict, Any
from datetime import timedelta
from airflow import DAG
from airflow.providers.apache.livy.operators.livy import LivyOperator
from datetime import datetime


ETL_CODE_LOCATION = "s3://movies-binaries/spark-movies-etl/latest"
LIVY_PROXY_USER = "datalake-srv-user"
LIVY_CONN_ID = "livy-emr-conn"
DAG_DEFAULT_ARGS = {
    "owner": "Guido Kosloff Gancedo",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _build_livy_operator(task: str, spark_conf_extra: Optional[Dict[Any, Any]] = None) -> LivyOperator:

    spark_conf_base = {
        "spark.jars.packages": "org.apache.spark:spark-avro_2.12:3.1.2,io.delta:delta-core_2.12:1.0.0",
        "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension",
        "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        "spark.yarn.appMasterEnv.PYSPARK_PYTHON": "./env/bin/python",
    }
    spark_conf_extra = spark_conf_extra or {}

    return LivyOperator(
        task_id=task,
        file=f"{ETL_CODE_LOCATION}/main.py",
        args=["--task", task, "--execution-date", "{{ ds }}"],
        archives=[f"{ETL_CODE_LOCATION}/venv_build.tar.gz#env"],
        conf={**spark_conf_base, **spark_conf_extra},
        proxy_user=LIVY_PROXY_USER,
        livy_conn_id=LIVY_CONN_ID,
    )


with DAG(
    dag_id="movies-etl",
    default_args=DAG_DEFAULT_ARGS,
    start_date=datetime(2021, 1, 1, 0, 0),
    schedule_interval="0 0 * * *",
) as dag:

    ingest = _build_livy_operator(task="ingest", spark_conf_extra={"spark.sql.shuffle.partitions": 5})
    transform = _build_livy_operator(task="transform", spark_conf_extra={"spark.sql.shuffle.partitions": 10})

    ingest >> transform
