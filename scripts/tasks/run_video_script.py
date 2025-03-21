import subprocess
import os
import json
from dotenv import load_dotenv
load_dotenv()

LOCAL_SERVER = os.getenv("LOCAL_SERVER")

def run_video_script():
    script_path = "/opt/airflow/scripts/convert_video_files.py"
    elan_dir = os.path.join(LOCAL_SERVER, "ELAN_OUT")     
    output_dir = os.path.join(LOCAL_SERVER, "isol/videos")  
    update_file = os.path.join(LOCAL_SERVER, "file_update.json")

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
    
    progression = 0

    for elan_file in elan_files:
        progression += 1
        print(f"⏱️ Processing ELAN file {progression}/{len(elan_files)}: {elan_file}")
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

