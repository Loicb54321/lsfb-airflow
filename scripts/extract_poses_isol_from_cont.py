import os
import numpy as np
import sys
from scipy.signal import savgol_filter
from airflow.utils.log.logging_mixin import LoggingMixin
from dotenv import load_dotenv
load_dotenv()
log = LoggingMixin().log
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

LOCAL_SERVER = os.getenv("LOCAL_SERVER")

# Paths
isol_video_folder = os.path.join(LOCAL_SERVER, "isol/videos")
cont_poses_raw_path = os.path.join(LOCAL_SERVER, "cont/poses_raw")
cont_poses_filtered_path = os.path.join(LOCAL_SERVER, "cont/poses")
isol_poses_raw_path = os.path.join(LOCAL_SERVER, "isol/poses_raw_V2")
isol_poses_filtered_path = os.path.join(LOCAL_SERVER, "isol/poses_V2")

body_parts = ["pose", "face", "left_hand", "right_hand"]

# Output folders
output_folders = {
    "pose": isol_poses_raw_path + "/pose",
    "face": isol_poses_raw_path + "/face",
    "left_hand": isol_poses_raw_path + "/left_hand",
    "right_hand": isol_poses_raw_path + "/right_hand",
}
filtered_output_folders = {
    "pose": isol_poses_filtered_path + "/pose",
    "face": isol_poses_filtered_path + "/face",
    "left_hand": isol_poses_filtered_path + "/left_hand",
    "right_hand": isol_poses_filtered_path + "/right_hand",
}

# Ensure output directories exist
for folder in {**output_folders, **filtered_output_folders}.values():
    os.makedirs(folder, exist_ok=True)

# Get all clip files
clip_files = [f for f in os.listdir(isol_video_folder) if f.endswith(('.mp4', '.avi', '.mov'))]
progression = 0

# Process each clip file
for clip_file in clip_files:
    progression += 1
    log.info(f"⏱️ Processing clip {progression}/{len(clip_files)}: {clip_file} ...")
    sys.stdout.flush()
    
    # Parse clip filename to get original video name and timestamps
    # Format: video_name_start_end.mp4
    parts = os.path.splitext(clip_file)[0].split('_')
    if len(parts) < 3:
        print(f"⚠️ Skipping file with invalid format: {clip_file}", flush=True)
        continue
    
    # Extract base video name and timestamps
    base_video_name = '_'.join(parts[:-2])  # Everything except last two parts (start and end)
    start_ms = int(parts[-2])
    end_ms = int(parts[-1])
    
    # Calculate frame indices based on timestamps
    # Assuming 50 fps                              ###########################################
    fps = 50
    start_frame = int(start_ms / 1000 * fps)
    end_frame = int(end_ms / 1000 * fps)
    
    # Define expected output file paths for this clip
    expected_files = {
        "pose": os.path.join(output_folders["pose"], f"{os.path.splitext(clip_file)[0]}_pose.npy"),
        "face": os.path.join(output_folders["face"], f"{os.path.splitext(clip_file)[0]}_face.npy"),
        "left_hand": os.path.join(output_folders["left_hand"], f"{os.path.splitext(clip_file)[0]}_left_hand.npy"),
        "right_hand": os.path.join(output_folders["right_hand"], f"{os.path.splitext(clip_file)[0]}_right_hand.npy"),
    }
    expected_filtered_files = {
        "pose": os.path.join(filtered_output_folders["pose"], f"{os.path.splitext(clip_file)[0]}_pose.npy"),
        "face": os.path.join(filtered_output_folders["face"], f"{os.path.splitext(clip_file)[0]}_face.npy"),
        "left_hand": os.path.join(filtered_output_folders["left_hand"], f"{os.path.splitext(clip_file)[0]}_left_hand.npy"),
        "right_hand": os.path.join(filtered_output_folders["right_hand"], f"{os.path.splitext(clip_file)[0]}_right_hand.npy"),
    }
    
    # Check if all expected output files already exist
    if all(os.path.exists(path) for path in {**expected_files, **expected_filtered_files}.values()):
        print(f"✅ All output files exist for {clip_file}. Skipping processing.", flush=True)
        continue  # Skip this clip
    
    print(f"Processing {clip_file} from {base_video_name} (frames {start_frame} to {end_frame})...", flush=True)
    
    # Process each body part
    for part in body_parts:
        # Path to the source pose data from the main video
        source_raw_path = os.path.join(cont_poses_raw_path, part, f"{base_video_name}_pose.npy")
        source_filtered_path = os.path.join(cont_poses_filtered_path, part, f"{base_video_name}_pose.npy")
        
        # Check if source files exist
        if not os.path.exists(source_raw_path):
            print(f"⚠️ Source raw pose file not found: {source_raw_path}", flush=True)
            continue
            
        if not os.path.exists(source_filtered_path):
            print(f"⚠️ Source filtered pose file not found: {source_filtered_path}", flush=True)
            continue
        
        try:
            # Load pose data from the main video
            source_raw_data = np.load(source_raw_path)
            source_filtered_data = np.load(source_filtered_path)
            
            # Check if frame range is valid
            if start_frame >= len(source_raw_data) or end_frame > len(source_raw_data):
                print(f"⚠️ Invalid frame range for {clip_file}: video has {len(source_raw_data)} frames, "
                      f"requested frames {start_frame} to {end_frame}", flush=True)
                continue
                
            # Extract the required frames
            clip_raw_data = source_raw_data[start_frame:end_frame+1]
            clip_filtered_data = source_filtered_data[start_frame:end_frame+1]
            
            # Save the extracted pose data
            np.save(expected_files[part], clip_raw_data)
            np.save(expected_filtered_files[part], clip_filtered_data)
            
            print(f"✅ Extracted {part} data for {clip_file} - {len(clip_raw_data)} frames", flush=True)
            
        except Exception as e:
            print(f"❌ Error processing {part} data for {clip_file}: {str(e)}", flush=True)
    
print("Processing complete! NPY files saved in separate folders.")