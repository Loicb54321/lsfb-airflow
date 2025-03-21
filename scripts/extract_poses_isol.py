import os
import numpy as np
import mediapipe as mp
import sys
from PIL import Image
from moviepy.editor import VideoFileClip
from scipy.signal import savgol_filter
from airflow.utils.log.logging_mixin import LoggingMixin
from dotenv import load_dotenv
load_dotenv()
log = LoggingMixin().log 
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

LOCAL_SERVER = os.getenv("LOCAL_SERVER")

# Initialize Mediapipe Holistic model
mp_holistic = mp.solutions.holistic
holistic = mp_holistic.Holistic(static_image_mode=False, model_complexity=2)

# Define filtering class (Savitzky-Golay)
class SavitchyGolayFiltering: 
    def __init__(self, window_length: int, polynom_order: int):
        self.window_length = window_length
        self.polynom_order = polynom_order

    def __call__(self, pose_sequence: np.ndarray):
        return np.apply_along_axis(
            lambda seq: savgol_filter(seq, self.window_length, self.polynom_order),
            axis=0,
            arr=pose_sequence,
        )

# Initialize the filter with chosen parameters
filtering = SavitchyGolayFiltering(window_length=7, polynom_order=2)

# Paths
video_folder = os.path.join(LOCAL_SERVER, "isol/videos") 
base_output_path = os.path.join(LOCAL_SERVER, "isol/poses_raw")
filtered_output_path = os.path.join(LOCAL_SERVER, "isol/poses")  
output_folders = {
    "pose": base_output_path+"/pose",
    "face": base_output_path+"/face",
    "left_hand": base_output_path+"/left_hand",
    "right_hand": base_output_path+"/right_hand",
}
filtered_output_folders = {  
    "pose": filtered_output_path+"/pose",
    "face": filtered_output_path+"/face",
    "left_hand": filtered_output_path+"/left_hand",
    "right_hand": filtered_output_path+"/right_hand",
}

# Ensure output directories exist
for folder in {**output_folders, **filtered_output_folders}.values():
    os.makedirs(folder, exist_ok=True)

videos_to_process = os.listdir(video_folder)
progression = 0

# Process each video
for video_file in videos_to_process:
    progression += 1
    log.info(f"⏱️ Video {progression}/{len(videos_to_process)}: {video_file} ...")
    sys.stdout.flush()

    if not video_file.endswith(('.mp4')):  # Ensure it's a video file
        continue

    video_path = os.path.join(video_folder, video_file)

    base_name = os.path.splitext(video_file)[0]

    # Define expected output file paths
    expected_files = {
        "pose": os.path.join(output_folders["pose"], f"{base_name}_pose.npy"),
        "face": os.path.join(output_folders["face"], f"{base_name}_face.npy"),
        "left_hand": os.path.join(output_folders["left_hand"], f"{base_name}_left_hand.npy"),
        "right_hand": os.path.join(output_folders["right_hand"], f"{base_name}_right_hand.npy"),
    }
    expected_filtered_files = { 
        "pose": os.path.join(filtered_output_folders["pose"], f"{base_name}_pose.npy"),
        "face": os.path.join(filtered_output_folders["face"], f"{base_name}_face.npy"),
        "left_hand": os.path.join(filtered_output_folders["left_hand"], f"{base_name}_left_hand.npy"),
        "right_hand": os.path.join(filtered_output_folders["right_hand"], f"{base_name}_right_hand.npy"),
    }

    # Check if all expected output files already exist
    if all(os.path.exists(path) for path in {**expected_files, **expected_filtered_files}.values()):
        print(f"✅ All output files exist for {video_path}. Skipping processing.", flush=True)
        continue  # Skip this video

    print(f"Processing {video_file} ...", flush=True)

    # Load the video using MoviePy
    video_clip = VideoFileClip(video_path)
    frame_rate = video_clip.fps  # Get the frame rate of the video

    # Process each frame
    pose_data, face_data, left_hand_data, right_hand_data = [], [], [], []
    
    for frame in video_clip.iter_frames(fps=frame_rate, dtype="uint8"):
        # Convert the frame to an Image object
        img = Image.fromarray(frame)

        # Convert image to Mediapipe format
        img_np = np.array(img)
        results = holistic.process(img_np)

        # Extract landmarks
        def extract_landmarks(landmark_list, num_points):
            if landmark_list:
                return np.array([[lm.x, lm.y, lm.z] for lm in landmark_list.landmark])
            else:
                return np.zeros((num_points, 3))  # Placeholder if no detection

        pose_data.append(extract_landmarks(results.pose_landmarks, 33))
        face_data.append(extract_landmarks(results.face_landmarks, 468))    # à vérifier, possible perte d'info, 468 si visage détecté, 478 sinon, en mettant 468 j'ai pas de pb si le visage n'est pas détécté dans une frame mais jsp si je perd de l'information
        left_hand_data.append(extract_landmarks(results.left_hand_landmarks, 21))
        right_hand_data.append(extract_landmarks(results.right_hand_landmarks, 21))

    # print(f"face_data type: {type(face_data)}", flush=True)
    # print(f"face_data length: {len(face_data)}", flush=True)
    # print(f"face_data[0] shape: {np.shape(face_data[0]) if len(face_data) > 0 else 'empty'}", flush=True)

    # Convert to NumPy arrays
    pose_data_np = np.array(pose_data)  
    face_data_np = np.array(face_data)  
    left_hand_data_np = np.array(left_hand_data)  
    right_hand_data_np = np.array(right_hand_data)
    data_np = [pose_data_np, face_data_np, left_hand_data_np, right_hand_data_np]
    body_parts = ["pose", "face", "left_hand", "right_hand"]

    for i in range(4):
        np.save(expected_files[body_parts[i]], data_np[i])  # Save raw poses data
        if data_np[i].shape[0] > 7:  # Ensure enough frames for filtering
            filtered_pose_data = filtering(data_np[i])  
            np.save(expected_filtered_files[body_parts[i]], filtered_pose_data)  
        else:
            np.save(expected_filtered_files[body_parts[i]], data_np[i])
    

print("Processing complete! NPY files saved in separate folders.")
