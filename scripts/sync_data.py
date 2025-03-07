import os
import shutil
import re
import glob
import xml.etree.ElementTree as ET
import time
import json
from is_it_new import is_it_new, update_last_dag_run 
from converter import convert_elan_file
from dotenv import load_dotenv
load_dotenv()

# Paths 
REMOTE_SERVER = os.getenv("REMOTE_SERVER")
LOCAL_SERVER = os.getenv("LOCAL_SERVER")
FILE_HISTORY = os.path.join(LOCAL_SERVER, "file_history.json")
FILE_UPDATE = os.path.join(LOCAL_SERVER, "file_update.json")
VIDEO_CONT_PATH = os.path.join(LOCAL_SERVER, "cont", "videos")
VIDEO_ISOL_PATH = os.path.join(LOCAL_SERVER, "isol", "videos")
POSES_CONT_PATH = os.path.join(LOCAL_SERVER, "cont", "poses")
POSES_ISOL_PATH = os.path.join(LOCAL_SERVER, "isol", "poses")
ELAN_FILES = os.path.join(LOCAL_SERVER, "ELAN_OUT")

BODY_PARTS = ["face", "pose", "left_hand", "right_hand"]
    
# Ensure LOCAL_SERVER folder exists
os.makedirs(LOCAL_SERVER, exist_ok=True)

# Regex for valid video filenames (e.g., CLSFBI0202A_S003_B.mp4)
VALID_VIDEO_REGEX = re.compile(r"^CLSFBI\d{4}[A-Z]_S\d{3}_B\.mp4$")
VALID_ELAN_REGEX = re.compile(r"^CLSFBI\d{4}\.eaf$")

def load_file_history():
    """Load tracked files from history JSON."""
    if os.path.exists(FILE_HISTORY):
        try:
            with open(FILE_HISTORY, "r") as f:
                data = f.read().strip()  # Read and strip whitespace
                return json.loads(data) if data else {}  # Return empty dict if file is empty
        except json.JSONDecodeError:
            print("⚠️ file_history.json is corrupted. Resetting file history.", flush=True)
            return {}  # Return empty dict if JSON is corrupted
    return {}

def save_file_history(file_history):
    """Save the current state of tracked files."""
    with open(FILE_HISTORY, "w") as f:
        json.dump(file_history, f, indent=4)

def save_file_update(file_update):
    """Save the added and updated files."""
    with open(FILE_UPDATE, "w") as f:
        json.dump(file_update, f, indent=4)

# def get_files(directory):
#     """Retrieve all files in a directory with their last modification time."""
#     return {file: os.path.getmtime(os.path.join(directory, file)) for file in os.listdir(directory)}

# def get_files(directory):
#     """Retrieve all files in a directory and its subdirectories with their last modification time."""
#     file_dict = {}
#     for root, _, files in os.walk(directory):  # Recursively walk through folders
#         for file in files:
#             file_path = os.path.join(root, file)  # Get full path
#             file_dict[file_path] = os.path.getmtime(file_path)  # Store modification time
#     return file_dict

def get_files(directory):
    """Retrieve all files in a directory and its subdirectories with their last modification time, keeping only filenames."""
    file_dict = {}
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_dict[os.path.basename(file_path)] = os.path.getmtime(file_path)  # Keep only filename
    return file_dict

def sync_files():
    """Compare remote and local files, determine changes."""
    remote_files = get_files(REMOTE_SERVER)
    local_files = get_files(LOCAL_SERVER)
    file_history = load_file_history()

    print("remote_files : ",remote_files, flush=True)
    print("local_files : ",local_files, flush=True)
    print("file_history : ",file_history, flush=True)

    added_files = {}
    modified_files = {}
    deleted_files = {}
    file_update = {}
    next_file_history = {}

    for file, mod_time in remote_files.items():
        next_file_history[file] = mod_time
        if file in local_files and is_it_new(mod_time):
            modified_files[file] = mod_time  # Modified file
            if file.endswith(".eaf") and VALID_ELAN_REGEX.match(file):
                file_update[file] = mod_time
        if file not in local_files:
            if file.endswith(".eaf") and VALID_ELAN_REGEX.match(file):
                file_update[file] = mod_time
            # If the file is not in history, it's a new addition
            if file not in file_history:
                # file_history[file] = mod_time
                added_files[file] = mod_time
            # elif is_it_new(mod_time):
            #     modified_files[file] = mod_time  # Modified file

    for file in local_files:
        if file.endswith(".mp4") and VALID_VIDEO_REGEX.match(file):
            if file not in remote_files:
                deleted_files[file] = local_files[file]
        elif file.endswith(".eaf") and VALID_ELAN_REGEX.match(file):
            if file not in remote_files:
                deleted_files[file] = local_files[file]

    # Save updated history
    save_file_history(next_file_history)

    file_update = {**modified_files, **added_files}
    save_file_update(file_update)

    return added_files, modified_files, deleted_files

def extract_base_names(elan_path):
    """Extracts all base names from the ELAN file's MEDIA_DESCRIPTOR section."""
    try:
        tree = ET.parse(elan_path)
        root = tree.getroot()
        base_names = set()

        for media_descriptor in root.findall(".//MEDIA_DESCRIPTOR"):
            media_url = media_descriptor.get("MEDIA_URL")
            if media_url:
                base_name = os.path.splitext(os.path.basename(media_url))[0]
                base_names.add(base_name)

        return list(base_names)

    except Exception as e:
        print(f"⚠️ Error parsing ELAN file {elan_path}: {e}", flush=True)
        return []

def extract_annotations(elan_path):
    """Extracts start and end times for annotations in the ELAN file."""
    try:
        tree = ET.parse(elan_path)
        root = tree.getroot()
        time_slots = {}

        # Parse time slots
        for time_slot in root.findall(".//TIME_SLOT"):
            slot_id = time_slot.get("TIME_SLOT_ID")
            time_value = time_slot.get("TIME_VALUE")
            if slot_id and time_value:
                time_slots[slot_id] = int(time_value)

        annotations = []
        for annotation in root.findall(".//ALIGNABLE_ANNOTATION"):
            start_id = annotation.get("TIME_SLOT_REF1")
            end_id = annotation.get("TIME_SLOT_REF2")
            if start_id in time_slots and end_id in time_slots:
                annotations.append((time_slots[start_id], time_slots[end_id]))

        return annotations

    except Exception as e:
        print(f"⚠️ Error extracting annotations from {elan_path}: {e}", flush=True)
        return []

def clean_deleted(deleted_files):
    """Remove clips, poses, videos associated with deleted ELAN files."""
    for elan_file in deleted_files:
        if elan_file.endswith(".eaf"):
            elan_path = os.path.join(ELAN_FILES, elan_file)

            # Extract information from ELAN
            # base_name, annotations = extract_elan_info(elan_path)
            base_names = extract_base_names(elan_path)
            annotations = extract_annotations(elan_path)

            # if not base_name or not annotations:
            #     print(f"⚠️ Could not extract information from {elan_file}. Skipping.", flush=True)
            #     continue

            for base_name in base_names:

                # Delete associated clips
                for start, end in annotations:
                    clip_name = f"{base_name}_{start}_{end}.mp4"
                    clip_path = os.path.join(VIDEO_ISOL_PATH, clip_name)
                    print(f"Searching clip: {clip_path}", flush=True)
                    if os.path.exists(clip_path):
                        print(f"🗑️ Deleting clip: {clip_path}", flush=True)
                        os.remove(clip_path)

                    # Delete associated pose files
                    for bodypart in BODY_PARTS:
                        pose_file = f"{base_name}_{start}_{end}_{bodypart}.npy"
                        pose_path = os.path.join(POSES_ISOL_PATH, bodypart, pose_file)
                        if os.path.exists(pose_path):
                            print(f"🗑️ Deleting pose file: {pose_path}", flush=True)
                            os.remove(pose_path)

                # Delete the base video
                base_video_path = os.path.join(VIDEO_CONT_PATH, f"{base_name}.mp4")
                if os.path.exists(base_video_path):
                    print(f"🗑️ Deleting base video: {base_video_path}", flush=True)
                    os.remove(base_video_path)

                # Delete associated pose files
                for bodypart in BODY_PARTS:
                    pose_file = f"{base_name}_{bodypart}.npy"
                    pose_path = os.path.join(POSES_CONT_PATH, bodypart, pose_file)
                    if os.path.exists(pose_path):
                        print(f"🗑️ Deleting pose file: {pose_path}", flush=True)
                        os.remove(pose_path)

            # Finally, delete the .eaf file itself
            print(f"🗑️ Deleting ELAN file: {elan_path}", flush=True)
            os.remove(elan_path)

def update_database(added_files, modified_files):
    """Move new and modified files to the database."""
    for filepath in {**added_files, **modified_files}:
        file = os.path.basename(filepath)

        if file.endswith(".eaf") and VALID_ELAN_REGEX.match(file):
            elan_path = os.path.join(ELAN_FILES, file)
            print(f"Copying {file} to database...")
            convert_elan_file(os.path.join(REMOTE_SERVER, "ELAN_IN", file[:8], file), ELAN_FILES)
            base_names = extract_base_names(elan_path)
            for base_name in base_names:
                video_file = f"{base_name}.mp4"
                if VALID_VIDEO_REGEX.match(video_file):
                    print(f"Copying {video_file} to database...")
                    shutil.copy2(os.path.join(REMOTE_SERVER, "VIDEOS_NETTES", f"CLSFB - {video_file[6:8]} ok", video_file), os.path.join(VIDEO_CONT_PATH, video_file))
            


        # if not file.endswith(".mp4"):
        #     if not file.endswith(".eaf"):
        #         print(f"Skipping invalid file: {file}")
        #         continue
        # if file.endswith(".mp4") and not VALID_VIDEO_REGEX.match(file):
        #     print(f"Skipping invalid video file: {file}")
        #     continue
        # if file.endswith(".eaf") and not VALID_ELAN_REGEX.match(file):
        #     print(f"Skipping invalid elan file: {file}")
        #     continue
        # print(f"Copying {file} to database...")

        # if file.endswith(".mp4"):
        #     shutil.copy2(os.path.join(REMOTE_SERVER, "VIDEOS_NETTES", f"CLSFB - {file[6:8]} ok", file), os.path.join(VIDEO_CONT_PATH, file))
        # else:
        #     convert_elan_file(os.path.join(REMOTE_SERVER, "ELAN_IN", file[:8], file), ELAN_FILES)
        #     # shutil.copy2(os.path.join(REMOTE_SERVER, file), os.path.join(ELAN_FILES, file))


# This updates the database based on changes to the ELAN files. if a video is deleted or modified and the associated elan isn't modified, there won't be an update.


def main():
    print("🔄 Syncing files...")
    added_files, modified_files, deleted_files = sync_files()
    
    print("🗑️ Cleaning deleted files...")
    clean_deleted(deleted_files)

    print("🗑️ Cleaning modified files...")
    clean_deleted(modified_files)

    print("📂 Updating database...")
    update_database(added_files, modified_files)

    print("deleted files : ",deleted_files, flush=True)
    print("added files : ",added_files, flush=True)
    print("modified files : ",modified_files, flush=True)
    print("✅ Sync complete!")
    update_last_dag_run()

if __name__ == "__main__":
    main()
