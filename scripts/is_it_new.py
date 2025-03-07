import os
import time

"""
copy this to use : 

from scripts.is_it_new import is_it_new, update_last_dag_run

if not is_it_new(file_path):
    print(f"Skipping {video_path} (Not modified since last run)", flush=True)
    continue

update_last_dag_run()
"""

timestamp_file_path = "/opt/airflow/data/sample-lsfb/local_server/last_dag_run.txt"

def is_it_new(file_or_timestamp, timestamp_file=timestamp_file_path):
    """
    Checks if a file is new (modified after the last DAG run).
    
    Args:
        file_path (str): Path to the file.
        timestamp_file (str): Path to the file storing the last DAG run timestamp.
    
    Returns:
        bool: True if the file is new, False otherwise.
    """

    # # If the file doesn't exist, process it and sends a warning
    # if not os.path.exists(file_path):
    #     print(f"⚠️ Missing file: {file_path}", flush=True)
    #     return False

    # Get the last DAG run time (default to 0 if file is missing)
    if os.path.exists(timestamp_file):
        with open(timestamp_file, "r") as f:
            last_dag_run = float(f.read().strip())
    else:
        last_dag_run = 0  # If first run, process all files

    # If input is a file path, get its modification time
    if isinstance(file_or_timestamp, str) and os.path.exists(file_or_timestamp):
        file_mtime = os.path.getmtime(file_or_timestamp)
    elif isinstance(file_or_timestamp, (int, float)):  # If it's already a timestamp
        file_mtime = file_or_timestamp
    else:
        print(f"⚠️ Invalid input: {file_or_timestamp}", flush=True)
        return False  # Invalid input, treat as not new

    # # Get file modification time
    # file_mtime = os.path.getmtime(file_path)

    # If file is new, return True
    return file_mtime > last_dag_run

def update_last_dag_run(timestamp_file=timestamp_file_path):
    """
    Updates the last DAG run timestamp file with the current time.
    
    Args:
        timestamp_file (str): Path to the timestamp file.
    """
    current_time = time.time()
    with open(timestamp_file, "w") as f:
        f.write(str(current_time))
    print(f"✅ Updated last DAG run timestamp to {current_time}", flush=True)