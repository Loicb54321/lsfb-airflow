import subprocess

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
