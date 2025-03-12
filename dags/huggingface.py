from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import json
from huggingface_hub import HfApi
from airflow.models import Variable
from dotenv import load_dotenv
load_dotenv()

# Paths
LOCAL_SERVER = os.getenv("LOCAL_SERVER")
FILE_HISTORY_PATH = os.path.join(LOCAL_SERVER, "file_history_HF.json")

# Hugging Face credentials
HF_TOKEN = Variable.get("HF_TOKEN")  # Secure token storage in Airflow
# HF_TOKEN = os.getenv("HF_TOKEN")
REPO_ID = "Loic54321/lsfb_dataset"  # Your HF dataset repo

# Function to load history
def load_file_history():
    """Load previous file upload history from JSON, handling empty or corrupted files."""
    if os.path.exists(FILE_HISTORY_PATH):
        if os.stat(FILE_HISTORY_PATH).st_size == 0:  # ✅ Check if file is empty
            return {}  # Return empty dict instead of failing
        
        try:
            with open(FILE_HISTORY_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Warning: file_history.json is corrupted. Resetting history.")
            return {}  # Return empty history instead of crashing
    return {}


# Function to save history
def save_file_history(history):
    """Save updated file upload history."""
    with open(FILE_HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=4)

# Function to synchronize files (upload new & delete missing)
def sync_files_with_huggingface():
    """Uploads new files and deletes missing files from Hugging Face Hub."""
    api = HfApi()
    file_history = load_file_history()
    
    # Ensure the repository exists
    try:
        api.create_repo(REPO_ID, token=HF_TOKEN, repo_type="dataset", exist_ok=True)
    except Exception as e:
        print(f"⚠️ Error creating repo: {e}")

    uploaded_files = {}
    new_files = []

    # Get list of remote files from HF
    try:
        remote_files = {f for f in api.list_repo_files(REPO_ID, repo_type="dataset")}

        # remote_files = {f.rfilename for f in api.list_repo_files(REPO_ID, repo_type="dataset")}
    except Exception as e:
        print(f"⚠️ Error fetching remote files: {e}")
        remote_files = set()

    local_files = set()

    # Walk through local_server and check for changes
    for root, _, files in os.walk(LOCAL_SERVER):
        for file in files:
            file_path = os.path.join(root, file)
            remote_path = os.path.relpath(file_path, LOCAL_SERVER)  # Maintain folder structure
            file_size = os.path.getsize(file_path)  # Get file size
            previous_size = file_history.get(remote_path)  # Get previous size

            local_files.add(remote_path)

            # Upload only if the file is new or its size has changed
            if previous_size is None or previous_size != file_size:
                print(f"⬆️ Uploading: {file_path} to {REPO_ID}/{remote_path}")
                try:
                    api.upload_file(
                        path_or_fileobj=file_path,
                        path_in_repo=remote_path,
                        repo_id=REPO_ID,
                        repo_type="dataset",
                        token=HF_TOKEN,
                        commit_message=f"🔄 Auto-update: {file}",
                    )
                    print(f"✅ Uploaded: {file}")
                    new_files.append(remote_path)
                    uploaded_files[remote_path] = file_size  # Store new file size
                except Exception as e:
                    print(f"❌ Failed to upload {file}: {e}")

    # Find missing files (files in HF but not in local server)
    files_to_delete = remote_files - local_files

    # Delete missing files from Hugging Face
    for remote_file in files_to_delete:
        print(f"🗑️ Deleting {remote_file} from Hugging Face")
        try:
            api.delete_file(path_in_repo=remote_file, repo_id=REPO_ID, token=HF_TOKEN, repo_type="dataset")
            print(f"✅ Deleted {remote_file}")
        except Exception as e:
            print(f"❌ Failed to delete {remote_file}: {e}")

    # Update file history with new uploads
    if new_files:
        print(f"🎉 Uploaded {len(new_files)} new or modified files!")
        file_history.update(uploaded_files)
        save_file_history(file_history)
    else:
        print("✅ No new changes detected.")

# Define the DAG
default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 2, 25),
    "catchup": False,
}

with DAG(
    "huggingface_sync_dag",
    default_args=default_args,
    schedule_interval=None,  # Manual trigger
    tags=["huggingface", "sync", "incremental"],
) as dag:

    sync_task = PythonOperator(
        task_id="sync_files",
        python_callable=sync_files_with_huggingface
    )

    sync_task
