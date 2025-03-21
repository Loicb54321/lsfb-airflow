from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

# Import functions
from scripts.tasks.check_and_download_data import check_and_download_data
from scripts.tasks.run_video_script import run_video_script
from scripts.tasks.run_extract_poses_cont import run_extract_poses_cont
from scripts.tasks.run_extract_poses_isol import run_extract_poses_isol
from scripts.tasks.create_splits import create_splits
from scripts.tasks.update_csv import update_csv

# Define default DAG arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 2, 19),
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
}

# Define the DAG
dag = DAG(
    'data_pipeline',
    default_args=default_args,
    description='Pipeline to check Server X, process video data, and store results',
    # schedule_interval='@daily',  # Runs once a day
    schedule=None,  # Manually triggered
    catchup=False,
)

# Define tasks
task_check_server = PythonOperator(
    task_id='check_server',
    python_callable=check_and_download_data,
    dag=dag,
)

task_run_video_script = PythonOperator(
    task_id='run_video_script',
    python_callable=run_video_script,
    dag=dag,
)

task_extract_poses_cont = PythonOperator(
    task_id="extract_poses_cont",
    python_callable=run_extract_poses_cont,
    dag=dag,
)

task_extract_poses_isol = PythonOperator(
    task_id="extract_poses_isol",
    python_callable=run_extract_poses_isol,
    dag=dag,
)

task_create_splits = PythonOperator(
    task_id='create_splits',
    python_callable=create_splits,
    dag=dag,
)

task_update_csv = PythonOperator(
    task_id='update_csv',
    python_callable=update_csv,
    dag=dag,
)

# Define task dependencies
task_check_server >> [task_extract_poses_cont, task_run_video_script]
task_run_video_script >> task_extract_poses_isol 
[task_extract_poses_cont, task_extract_poses_isol] >> task_create_splits >> task_update_csv

