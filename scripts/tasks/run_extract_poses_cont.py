import subprocess

def run_extract_poses_cont():
    try:
        process = subprocess.Popen(
            ["python3", "/opt/airflow/scripts/extract_poses_cont.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in process.stdout:
            print(line, end='', flush=True)
        exit_code = process.wait()
        if exit_code != 0:
            raise subprocess.CalledProcessError(exit_code, process.args)
    except Exception as e:
        print(f"Script failed! {str(e)}")
        raise