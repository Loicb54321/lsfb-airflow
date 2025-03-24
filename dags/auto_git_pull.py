from airflow import DAG
from airflow.operators.python import PythonOperator
from git import Repo, GitCommandError, InvalidGitRepositoryError
from datetime import datetime
import logging
import os

def force_git_pull():
    logger = logging.getLogger("airflow.task")
    repo_path = "/opt/airflow"
    
    try:
        # Verify repository exists
        if not os.path.exists(os.path.join(repo_path, '.git')):
            raise InvalidGitRepositoryError(f"{repo_path} is not a Git repository")
        
        repo = Repo(repo_path)
        origin = repo.remotes.origin
        
        # Force reset to origin
        logger.info("Resetting local changes")
        origin.fetch()
        repo.git.reset('--hard', 'origin/main')  # Replace 'main' with your branch
        
        logger.info("Successfully updated repository")

    except InvalidGitRepositoryError as e:
        logger.error(f"Invalid repository: {str(e)}")
        raise
    except GitCommandError as e:
        logger.error(f"Git command failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

dag = DAG(
    'git_repo_sync',
    description='Force synchronize Git repository',
    schedule_interval='*/5 * * * *',  # Every 5 minutes
    start_date=datetime(2025, 3, 24),
    catchup=False,
    default_args={
        'retries': 2,
        'retry_delay': timedelta(minutes=2),
        'email_on_retry': False
    }
)

sync_task = PythonOperator(
    task_id='force_sync_repository',
    python_callable=force_git_pull,
    dag=dag,
)