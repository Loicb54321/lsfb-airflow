import os
import numpy as np
import mediapipe as mp
from PIL import Image
from moviepy.editor import VideoFileClip

# Initialize Mediapipe Holistic model
mp_holistic = mp.solutions.holistic
holistic = mp_holistic.Holistic(static_image_mode=False, model_complexity=2)

# Paths
video_folder = "/opt/airflow/data/sample-lsfb/local_server/isol/videos" 
base_output_path = "/opt/airflow/data/sample-lsfb/local_server/isol/poses"  
output_folders = {
    "pose": base_output_path+"/pose",
    "face": base_output_path+"/face",
    "left_hand": base_output_path+"/left_hand",
    "right_hand": base_output_path+"/right_hand",
}

# Ensure output directories exist
for folder in output_folders.values():
    os.makedirs(folder, exist_ok=True)

# Process each video
for video_file in os.listdir(video_folder):
    if not video_file.endswith(('.mp4', '.avi', '.mov')):  # Ensure it's a video file
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

    # Check if all expected output files already exist
    if all(os.path.exists(path) for path in expected_files.values()):
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

    print(f"face_data type: {type(face_data)}", flush=True)
    print(f"face_data length: {len(face_data)}", flush=True)
    print(f"face_data[0] shape: {np.shape(face_data[0]) if len(face_data) > 0 else 'empty'}", flush=True)

    # Convert to NumPy arrays
    np.save(os.path.join(output_folders["pose"], f"{base_name}_pose.npy"), np.array(pose_data))
    np.save(os.path.join(output_folders["face"], f"{base_name}_face.npy"), np.array(face_data))
    np.save(os.path.join(output_folders["left_hand"], f"{base_name}_left_hand.npy"), np.array(left_hand_data))
    np.save(os.path.join(output_folders["right_hand"], f"{base_name}_right_hand.npy"), np.array(right_hand_data))

print("Processing complete! NPY files saved in separate folders.")
