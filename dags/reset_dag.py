from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import json

# Define paths
LOCAL_SERVER = "/opt/airflow/data/sample-lsfb/local_server"
LAST_DAG_RUN_PATH = os.path.join(LOCAL_SERVER, "last_dag_run.txt")
FILE_HISTORY_PATH = os.path.join(LOCAL_SERVER, "file_history.json")
FILE_UPDATE_PATH = os.path.join(LOCAL_SERVER, "file_update.json")

# Function to reset files
def reset_files():
    """Reset last_dag_run.txt and clear JSON history files."""
    # Reset last_dag_run.txt
    with open(LAST_DAG_RUN_PATH, "w") as f:
        f.write("0")

    # Clear JSON files
    for file_path in [FILE_HISTORY_PATH, FILE_UPDATE_PATH]:
        with open(file_path, "w") as f:
            json.dump({}, f)  # Empty JSON object

    print("✅ Reset complete: last_dag_run.txt set to 0, file_history.json and file_update.json cleared.")

# Define the DAG
default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 2, 25),
    "catchup": False,  # Avoid running past executions
}

with DAG(
    "manual_reset_dag",
    default_args=default_args,
    schedule_interval=None,  # Manual trigger only
    tags=["manual", "reset"],
) as dag:
    
    reset_task = PythonOperator(
        task_id="reset_files",
        python_callable=reset_files
    )

    reset_task  # Run the task when the DAG is executed manually
