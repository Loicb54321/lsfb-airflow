from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import json
from dotenv import load_dotenv
load_dotenv()

# Define base paths
# DATABASE_PATH = os.getenv("LOCAL_SERVER")
DATABASE_PATH = "/opt/airflow/data/sample-lsfb/test_init_db"
ELAN_OUT_PATH = os.path.join(DATABASE_PATH, "ELAN_OUT")

# Define paths for structured directories
CONT_PATH = os.path.join(DATABASE_PATH, "cont")
ISOL_PATH = os.path.join(DATABASE_PATH, "isol")

POSES_SUBFOLDERS = ["face", "pose", "left_hand", "right_hand"]
METADATA_SPLITS_PATH = "metadata/splits"

# Define default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2024, 3, 12),
    "retries": 0,
}

# DAG definition
dag = DAG(
    "initialize_database",
    default_args=default_args,
    description="Manually triggered DAG to initialize database structure",
    schedule_interval=None,  # Manually triggered
    catchup=False,
)


def check_database_empty():
    """Check if the database directory is empty before proceeding."""
    if os.path.exists(DATABASE_PATH) and any(os.listdir(DATABASE_PATH)):
        raise Exception(
            f"⚠️ WARNING: The database at {DATABASE_PATH} is NOT empty! Initialization aborted to prevent data loss."
        )
    print("✅ Database is empty. Proceeding with initialization.")


def create_folders_and_files():
    """Function to create the required folders and empty files."""
    folders = [
        ISOL_PATH,
        ELAN_OUT_PATH,
        CONT_PATH,
        os.path.join(CONT_PATH, "metadata", "splits"),
        os.path.join(CONT_PATH, "poses_raw", "face"),
        os.path.join(CONT_PATH, "poses_raw", "pose"),
        os.path.join(CONT_PATH, "poses_raw", "left_hand"),
        os.path.join(CONT_PATH, "poses_raw", "right_hand"),
        os.path.join(CONT_PATH, "poses", "face"),
        os.path.join(CONT_PATH, "poses", "pose"),
        os.path.join(CONT_PATH, "poses", "left_hand"),
        os.path.join(CONT_PATH, "poses", "right_hand"),
        os.path.join(CONT_PATH, "videos"),
        os.path.join(ISOL_PATH, "metadata", "splits"),
        os.path.join(ISOL_PATH, "poses_raw", "face"),
        os.path.join(ISOL_PATH, "poses_raw", "pose"),
        os.path.join(ISOL_PATH, "poses_raw", "left_hand"),
        os.path.join(ISOL_PATH, "poses_raw", "right_hand"),
        os.path.join(ISOL_PATH, "poses", "face"),
        os.path.join(ISOL_PATH, "poses", "pose"),
        os.path.join(ISOL_PATH, "poses", "left_hand"),
        os.path.join(ISOL_PATH, "poses", "right_hand"),
        os.path.join(ISOL_PATH, "videos"),
    ]

    # Create all directories
    for folder in folders:
        os.makedirs(folder, exist_ok=True)

    # Create empty JSON files
    empty_json_files = [
        os.path.join(DATABASE_PATH, "file_history.json"),
        os.path.join(DATABASE_PATH, "file_history_HF.json"),
        os.path.join(DATABASE_PATH, "file_update.json"),
    ]
    for json_file in empty_json_files:
        with open(json_file, "w") as f:
            json.dump({}, f)

    # Create last_dag_run.txt with "0" inside
    with open(os.path.join(DATABASE_PATH, "last_dag_run.txt"), "w") as f:
        f.write("0")

    # Create empty subtitles.csv
    with open(os.path.join(CONT_PATH, "subtitles.csv"), "w") as f:
        f.write("")

    # Create empty instances.csv
    with open(os.path.join(ISOL_PATH, "instances.csv"), "w") as f:
        f.write("")

    print("✅ Database structure initialized successfully.")


# Airflow Python Operators
check_database_task = PythonOperator(
    task_id="check_database_empty",
    python_callable=check_database_empty,
    dag=dag,
)

initialize_database_task = PythonOperator(
    task_id="initialize_database",
    python_callable=create_folders_and_files,
    dag=dag,
)

# Set task order: Check first, then initialize
check_database_task >> initialize_database_task
