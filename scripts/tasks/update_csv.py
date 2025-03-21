import subprocess

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