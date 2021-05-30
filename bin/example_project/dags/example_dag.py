from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.utils.timezone import datetime

dag = DAG(
    dag_id="example_dag",
    default_args={"start_date": datetime(2020, 5, 1), "owner": "airflow"},
    schedule_interval=None,
)

bash_task = BashOperator(
    task_id="bash_task",
    bash_command="echo Test",
    dag=dag,
)
