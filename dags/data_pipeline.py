from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import subprocess
import os
import json

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
    schedule_interval='@daily',  # Runs once a day
    catchup=False,
)

# Function to check and download data from Server X
def check_and_download_data():
    try:
        result = subprocess.run(
            ["python3", "/opt/airflow/scripts/sync_data.py"],
            check=True,
            capture_output=True,  # Capture stdout/stderr
            text=True
        )
        print("Script output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Script failed!", e.stderr)
        raise

# Function to treat the video files + update the CSV files
def run_video_script():
    script_path = "/opt/airflow/scripts/convert_video_files.py"
    elan_dir = "/opt/airflow/data/sample-lsfb/local_server/ELAN_OUT"      
    output_dir = "/opt/airflow/data/sample-lsfb/local_server/isol/videos"  
    update_file = "/opt/airflow/data/sample-lsfb/local_server/file_update.json"

    # Load the update file
    with open(update_file, "r", encoding="utf-8") as f:
        update_data = json.load(f)

    # Extract filenames from JSON keys
    elan_names_to_update = set(update_data.keys())

    # Find all .eaf files that match the update list
    elan_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(elan_dir)
        for file in files if file.endswith(".eaf") and file in elan_names_to_update
    ]

    print(f"✅ Found {len(elan_files)} ELAN files to process:\n{elan_files}")

    if not elan_files:
        print("❌ No ELAN files found in", elan_dir)
        return

    for elan_file in elan_files:
        try:
            print(f"🚀 Processing {elan_file} ...")
            result = subprocess.run(
                ["python3", script_path, "--elan_file", elan_file, "--output_dir", output_dir],  #, "--json_file", update_file],
                check=True, text=True, capture_output=True
            )
            print("✅ Script Output:", result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"❌ Script failed for {elan_file} with error:", e.stderr)
            continue  # Move to the next file instead of stopping execution

def run_extract_poses_cont():
    try:
        result = subprocess.run(
            ["python3", "/opt/airflow/scripts/extract_poses_cont.py"],
            check=True,
            capture_output=True,  # Capture stdout/stderr
            text=True
        )
        print("Script output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Script failed!", e.stderr)
        raise

def run_extract_poses_isol():
    try:
        result = subprocess.run(
            ["python3", "/opt/airflow/scripts/extract_poses_isol.py"],
            check=True,
            capture_output=True,  # Capture stdout/stderr
            text=True
        )
        print("Script output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Script failed!", e.stderr)
        raise

def create_splits():
    try:
        result = subprocess.run(
            ["python3", "/opt/airflow/scripts/create_splits_V2.py"],
            check=True,
            capture_output=True,  # Capture stdout/stderr
            text=True
        )
        print("Script output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Script failed!", e.stderr)
        raise

def update_csv():
    try:
        result = subprocess.run(
            ["python3", "/opt/airflow/scripts/update_csv.py"],
            check=True,
            capture_output=True,  # Capture stdout/stderr
            text=True
        )
        print("Script output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Script failed!", e.stderr)
        raise



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

# task_extract_poses_cont = PythonOperator(
#     task_id="extract_poses_cont",
#     python_callable=run_extract_poses_cont,
#     dag=dag,
# )

# task_extract_poses_isol = PythonOperator(
#     task_id="extract_poses_isol",
#     python_callable=run_extract_poses_isol,
#     dag=dag,
# )

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
# task_check_server >> [task_run_elan_script , task_extract_poses_cont, task_run_video_script]
# task_run_video_script >> task_extract_poses_isol 
# [task_extract_poses_cont, task_extract_poses_isol] >> task_create_splits


task_check_server >> task_run_video_script >> task_create_splits >> task_update_csv