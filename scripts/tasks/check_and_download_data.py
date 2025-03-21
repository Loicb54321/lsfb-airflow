import subprocess

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