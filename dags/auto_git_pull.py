from airflow import DAG
from airflow.operators.python import PythonOperator
import git
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

LOCAL_SERVER = os.getenv("LOCAL_SERVER")

# Function to pull the latest changes from the Git repository
def pull_git_repo():
    repo_dir = LOCAL_SERVER
    try:
        # Open the repo
        repo = git.Repo(repo_dir)

        # Check if the repository is clean (no changes)
        if repo.is_dirty():
            print("Repo is dirty, not pulling.")
        else:
            # Pull the latest changes
            print("Pulling the latest changes from the repository.")
            origin = repo.remotes.origin
            origin.pull()

    except Exception as e:
        print(f"Error pulling the repository: {str(e)}")

# Define the DAG
dag = DAG(
    'git_pull_dag',
    description='A simple DAG to pull from a Git repository',
    schedule_interval='* * * * *',
    start_date=datetime(2025, 3, 24),
    catchup=False,
)

# Define the task
pull_task = PythonOperator(
    task_id='pull_git_repo',
    python_callable=pull_git_repo,
    dag=dag,
)