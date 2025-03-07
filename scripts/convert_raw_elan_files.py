# from converter import convert_all_elan_files, for now this script seems useless but i keep it to be safe
from export import create_annotation_files

root = "/opt/airflow"                          
# convert_all_elan_files(
#     f"{root}/data/sample-lsfb/remote_server/ELAN_IN",
#     f"{root}/data/sample-lsfb/local_server/ELAN_OUT",
# )

create_annotation_files(
    f"{root}/data/sample-lsfb/local_server/ELAN_OUT",
    f"{root}/data/sample-lsfb/local_server/JSON",
)

# Function to treat the ELAN files to put in dag if needed
# def run_elan_script():
#     try:
#         result = subprocess.run(
#             ["python3", "/opt/airflow/scripts/convert_raw_elan_files.py"],
#             check=True,
#             capture_output=True,  # Capture stdout/stderr
#             text=True
#         )
#         print("Script output:", result.stdout)
#     except subprocess.CalledProcessError as e:
#         print("Script failed!", e.stderr)
#         raise