# version avec multiprocessing et limite mémoire :

import psutil  
import os  
import numpy as np
import mediapipe as mp
import sys
from PIL import Image
from moviepy.editor import VideoFileClip
from scipy.signal import savgol_filter
from airflow.utils.log.logging_mixin import LoggingMixin
from dotenv import load_dotenv
import multiprocessing as mpc
import time
import queue
import threading

load_dotenv()
log = LoggingMixin().log 
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

LOCAL_SERVER = os.getenv("LOCAL_SERVER")

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
video_folder = os.path.join(LOCAL_SERVER, "cont/videos") 
base_output_path = os.path.join(LOCAL_SERVER, "cont/poses_raw") 
filtered_output_path = os.path.join(LOCAL_SERVER, "cont/poses") 
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

# A thread-safe queue for logging
log_queue = queue.Queue()

# Thread function to process logs
def log_worker():
    while True:
        message = log_queue.get()
        if message is None:  # Sentinel to exit
            break
        log.info(message)
        sys.stdout.flush()
        log_queue.task_done()

# # Function to process a single video
# def process_video(video_file, total_videos, processed_videos):
#     log.info(f"Inside the process_video for {video_file}")
#     video_index = processed_videos.value
#     processed_videos.value += 1

#     mp_holistic = mp.solutions.holistic
#     holistic = mp_holistic.Holistic(static_image_mode=False, model_complexity=2)
    
#     # Skip non-video files
#     if not video_file.endswith(('.mp4')): 
#         return
    
#     video_path = os.path.join(video_folder, video_file)
#     base_name = os.path.splitext(video_file)[0]

#     # Define expected output file paths
#     expected_files = {
#         "pose": os.path.join(output_folders["pose"], f"{base_name}_pose.npy"),
#         "face": os.path.join(output_folders["face"], f"{base_name}_face.npy"),
#         "left_hand": os.path.join(output_folders["left_hand"], f"{base_name}_left_hand.npy"),
#         "right_hand": os.path.join(output_folders["right_hand"], f"{base_name}_right_hand.npy"),
#     }
#     expected_filtered_files = { 
#         "pose": os.path.join(filtered_output_folders["pose"], f"{base_name}_pose.npy"),
#         "face": os.path.join(filtered_output_folders["face"], f"{base_name}_face.npy"),
#         "left_hand": os.path.join(filtered_output_folders["left_hand"], f"{base_name}_left_hand.npy"),
#         "right_hand": os.path.join(filtered_output_folders["right_hand"], f"{base_name}_right_hand.npy"),
#     }

#     # Check if all expected output files already exist
#     if all(os.path.exists(path) for path in {**expected_files, **expected_filtered_files}.values()):
#         log.info(f"✅ Video {video_index}/{total_videos}: {video_file} - Already processed. Skipping.")
#         return
#     log.info(f"🚀 Video {video_index}/{total_videos}: {video_file} - Starting process...")
#     sys.stdout.flush()
#     start_time = time.time()

#     try:
#         # Load the video using MoviePy
#         video_clip = VideoFileClip(video_path)
#         frame_rate = video_clip.fps  # Get the frame rate of the video
#         total_frames = int(video_clip.duration * frame_rate)
        
#         # Process each frame
#         pose_data, face_data, left_hand_data, right_hand_data = [], [], [], []
        
#         # Log progress every 10% of frames
#         progress_interval = max(1, total_frames // 10)
#         frame_count = 0
        
#         for frame in video_clip.iter_frames(fps=frame_rate, dtype="uint8"):
#             # Convert the frame to an Image object
#             img = Image.fromarray(frame)

#             # Convert image to Mediapipe format
#             img_np = np.array(img)
#             results = holistic.process(img_np)

#             # Extract landmarks
#             def extract_landmarks(landmark_list, num_points):
#                 if landmark_list:
#                     return np.array([[lm.x, lm.y, lm.z] for lm in landmark_list.landmark])
#                 else:
#                     return np.zeros((num_points, 3))  # Placeholder if no detection

#             pose_data.append(extract_landmarks(results.pose_landmarks, 33))
#             face_data.append(extract_landmarks(results.face_landmarks, 468))
#             left_hand_data.append(extract_landmarks(results.left_hand_landmarks, 21))
#             right_hand_data.append(extract_landmarks(results.right_hand_landmarks, 21))
            
#             frame_count += 1
#             if frame_count % progress_interval == 0:
#                 progress = (frame_count / total_frames) * 100
#                 log.info(f"  🔄 Video {video_index}/{total_videos}: {video_file} - {progress:.1f}% processed ({frame_count}/{total_frames} frames)")

#         # Convert to NumPy arrays
#         pose_data_np = np.array(pose_data)  
#         face_data_np = np.array(face_data)  
#         left_hand_data_np = np.array(left_hand_data)  
#         right_hand_data_np = np.array(right_hand_data)
#         data_np = [pose_data_np, face_data_np, left_hand_data_np, right_hand_data_np]
#         body_parts = ["pose", "face", "left_hand", "right_hand"]

#         log.info(f"  💾 Video {video_index}/{total_videos}: {video_file} - Saving data to disk...")
        
#         for i in range(4):
#             np.save(expected_files[body_parts[i]], data_np[i])  # Save raw poses data
#             if data_np[i].shape[0] > 7:  # Ensure enough frames for filtering
#                 filtered_pose_data = filtering(data_np[i])  
#                 np.save(expected_filtered_files[body_parts[i]], filtered_pose_data)  
#             else:
#                 np.save(expected_filtered_files[body_parts[i]], data_np[i])
        
#         # Close video to free resources
#         video_clip.close()
        
#         end_time = time.time()
#         duration = end_time - start_time
#         log.info(f"✅ Video {video_index}/{total_videos}: {video_file} - Completed in {duration:.2f} seconds")
        
#     except Exception as e:
#         log.info(f"❌ Video {video_index}/{total_videos}: {video_file} - Error: {str(e)}")
        
#     return

def check_if_processed(video_file):
    base_name = os.path.splitext(video_file)[0]
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
    return all(os.path.exists(path) for path in {**expected_files, **expected_filtered_files}.values())

def main():
    # Start the logging thread
    log_thread = threading.Thread(target=log_worker)
    log_thread.daemon = True
    log_thread.start()

    all_videos = [f for f in os.listdir(video_folder) if f.endswith(('.mp4'))]
    videos_to_process = [video for video in all_videos if not check_if_processed(video)]
    total_videos = len(videos_to_process)
    log.info(f"Found {len(all_videos)} videos in the folder. {total_videos} need processing.")

    # Get video sizes and sort
    video_sizes = []
    for video_file in videos_to_process:
        video_path = os.path.join(video_folder, video_file)
        try:
            size = os.path.getsize(video_path)
            video_sizes.append((video_file, size))
        except FileNotFoundError:
            log.warning(f"File not found: {video_path}")
            total_videos -= 1
            continue

    video_sizes.sort(key=lambda item: item[1])  # Sort by size
    videos_to_process_sorted = [item[0] for item in video_sizes]
    log.info(f"Videos to process sorted by size. Total: {total_videos}")

    manager = mpc.Manager()
    processed_videos_list = manager.list()
    list_lock = manager.Lock()
    processed_count = 0

    while processed_count < total_videos:
        cpu_usage = psutil.cpu_percent(interval=1)
        mem_usage = psutil.virtual_memory().percent
        swap_usage = psutil.swap_memory().percent
        
        log.info(f"--- Processing Iteration ---")
        log.info(f"📈 Current CPU Usage: {cpu_usage}%, Memory Usage: {mem_usage}%, Swap Usage: {swap_usage}%, Processed Videos: {processed_count}/{total_videos}")

        # Determine the number of processes based on resource availability
        if cpu_usage > 95 or mem_usage > 80 or swap_usage > 50:
            num_processes = max(1, os.cpu_count() - 6)
            log.warning(f"High resource usage. Using {num_processes} parallel processes.")
        elif cpu_usage < 95 and mem_usage < 70 and swap_usage < 40:
            num_processes = max(1, os.cpu_count() - 2)
            log.info(f"Resource usage is moderate. Using {num_processes} parallel processes.")
        else:
            num_processes = max(1, os.cpu_count() - 4)
            log.info(f"Resource usage is normal. Using {num_processes} parallel processes.")

        remaining_videos_sorted = [video for video in videos_to_process_sorted if video not in processed_videos_list]
        if not remaining_videos_sorted:
            break

        videos_to_process_in_this_iteration = remaining_videos_sorted[:num_processes]

        if videos_to_process_in_this_iteration:
            tasks = [(video, total_videos, processed_videos_list, list_lock) for video in videos_to_process_in_this_iteration]

            log.info(f"Starting a new pool with {num_processes} processes for {len(videos_to_process_in_this_iteration)} videos.")
            with mpc.Pool(processes=num_processes) as pool:
                pool.starmap(process_video_resource_aware, tasks)

            with list_lock:
                processed_count = len(processed_videos_list)
            log.info(f"Processed {len(videos_to_process_in_this_iteration)} videos in this batch. Total processed: {processed_count}")
        else:
            log.info("No videos to process in this iteration.")
            time.sleep(5)

        time.sleep(5) # Wait before the next iteration

    # Signal the logging thread to exit
    log_queue.put(None)
    log_thread.join()

    log.info("Processing complete! NPY files saved in separate folders.")

def process_video_resource_aware(video_file, total_videos, processed_videos_list, list_lock):
    log.info(f"Processing {video_file}")
    start_time = time.time()
    mp_holistic = mp.solutions.holistic
    holistic = mp_holistic.Holistic(static_image_mode=False, model_complexity=2)

    try:
        video_path = os.path.join(video_folder, video_file)
        base_name = os.path.splitext(video_file)[0]

        video_clip = VideoFileClip(video_path)
        frame_rate = video_clip.fps
        total_frames = int(video_clip.duration * frame_rate)

        pose_data, face_data, left_hand_data, right_hand_data = [], [], [], []
        progress_interval = max(1, total_frames // 10)
        frame_count = 0

        for frame in video_clip.iter_frames(fps=frame_rate, dtype="uint8"):
            img = Image.fromarray(frame)
            img_np = np.array(img)
            results = holistic.process(img_np)

            def extract_landmarks(landmark_list, num_points):
                if landmark_list:
                    return np.array([[lm.x, lm.y, lm.z] for lm in landmark_list.landmark])
                else:
                    return np.zeros((num_points, 3))

            pose_data.append(extract_landmarks(results.pose_landmarks, 33))
            face_data.append(extract_landmarks(results.face_landmarks, 468))
            left_hand_data.append(extract_landmarks(results.left_hand_landmarks, 21))
            right_hand_data.append(extract_landmarks(results.right_hand_landmarks, 21))

            frame_count += 1
            if frame_count % progress_interval == 0:
                progress = (frame_count / total_frames) * 100
                log.info(f"  🔄 Video: {video_file} - {progress:.1f}% processed ({frame_count}/{total_frames} frames)")

        pose_data_np = np.array(pose_data)
        face_data_np = np.array(face_data)
        left_hand_data_np = np.array(left_hand_data)
        right_hand_data_np = np.array(right_hand_data)
        data_np = [pose_data_np, face_data_np, left_hand_data_np, right_hand_data_np]
        body_parts = ["pose", "face", "left_hand", "right_hand"]

        output_files = {
            "pose": os.path.join(output_folders["pose"], f"{base_name}_pose.npy"),
            "face": os.path.join(output_folders["face"], f"{base_name}_face.npy"),
            "left_hand": os.path.join(output_folders["left_hand"], f"{base_name}_left_hand.npy"),
            "right_hand": os.path.join(output_folders["right_hand"], f"{base_name}_right_hand.npy"),
        }
        filtered_output_files = {
            "pose": os.path.join(filtered_output_folders["pose"], f"{base_name}_pose.npy"),
            "face": os.path.join(filtered_output_folders["face"], f"{base_name}_face.npy"),
            "left_hand": os.path.join(filtered_output_folders["left_hand"], f"{base_name}_left_hand.npy"),
            "right_hand": os.path.join(filtered_output_folders["right_hand"], f"{base_name}_right_hand.npy"),
        }

        log.info(f"  💾 Video: {video_file} - Saving data to disk...")
        for i in range(4):
            np.save(output_files[body_parts[i]], data_np[i])
            if data_np[i].shape[0] > 7:
                filtered_pose_data = filtering(data_np[i])
                np.save(filtered_output_files[body_parts[i]], filtered_pose_data)
            else:
                np.save(filtered_output_files[body_parts[i]], data_np[i])

        video_clip.close()
        end_time = time.time()
        duration = end_time - start_time
        log.info(f"✅ Video: {video_file} - Completed in {duration:.2f} seconds")
        with list_lock:
            processed_videos_list.append(video_file)

    except Exception as e:
        log.info(f"❌ Video: {video_file} - Error: {str(e)}")

    finally:
        if 'holistic' in locals():
            holistic.close()

if __name__ == "__main__":
    main()




# def main():
#     # Start the logging thread
#     log_thread = threading.Thread(target=log_worker)
#     log_thread.daemon = True
#     log_thread.start()

#     videos_to_process = [f for f in os.listdir(video_folder) if f.endswith(('.mp4'))]
#     total_videos = len(videos_to_process)
#     log.info(f"Found {total_videos} videos to process")

#     manager = mpc.Manager()
#     processed_videos_list = manager.list() # Track processed videos
#     list_lock = manager.Lock() # Create a lock

#     while len(processed_videos_list) < total_videos:
#         cpu_usage = psutil.cpu_percent(interval=1)
#         mem_usage = psutil.virtual_memory().percent
#         swap_usage = psutil.swap_memory().percent

#         log.info(f"--- Processing Iteration ---")
#         log.info(f"Current CPU Usage: {cpu_usage}%, Memory Usage: {mem_usage}%, Swap Usage: {swap_usage}%, Processed Videos: {len(processed_videos_list)}/{total_videos}")

#         # Determine the number of processes based on resource availability
#         if cpu_usage > 95 or mem_usage > 80 or swap_usage > 50:
#             num_processes = max(1, os.cpu_count() - 6) # Reduce drastically
#             log.warning(f"High resource usage. Using {num_processes} parallel processes.")
#         elif cpu_usage < 95 and mem_usage < 60 and swap_usage < 30:
#             num_processes = max(1, os.cpu_count() - 2) # Use more cores
#             log.info(f"Resource usage is low. Using {num_processes} parallel processes.")
#         else:
#             num_processes = max(1, os.cpu_count() - 4) # Moderate usage
#             log.info(f"Moderate resource usage. Using {num_processes} parallel processes.")

#         remaining_videos = [video for video in videos_to_process if video not in processed_videos_list]
#         if not remaining_videos:
#             break

#         videos_to_process_in_this_iteration = remaining_videos[:num_processes] # Process a limited number of videos

#         if videos_to_process_in_this_iteration:
#             tasks = [(video, total_videos, processed_videos_list, list_lock) for video in videos_to_process_in_this_iteration]

#             pool = mpc.Pool(processes=num_processes)
#             pool.starmap(process_video_resource_aware, tasks)
#             pool.close()
#             pool.join()
#             log.info("Pool closed and joined.")
#         else:
#             log.info("No videos to process in this iteration.")

#         time.sleep(5) # Wait before the next iteration

#     # Signal the logging thread to exit
#     log_queue.put(None)
#     log_thread.join()

#     log.info("Processing complete! NPY files saved in separate folders.")

# def process_video_resource_aware(video_file, total_videos, processed_videos_list, list_lock):
#     log.info(f"Processing {video_file}")
#     mp_holistic = mp.solutions.holistic
#     holistic = mp_holistic.Holistic(static_image_mode=False, model_complexity=2)

#     # Skip non-video files (this check might be redundant as we filter in main)
#     if not video_file.endswith(('.mp4')):
#         return

#     video_path = os.path.join(video_folder, video_file)
#     base_name = os.path.splitext(video_file)[0]

#     # Define expected output file paths
#     expected_files = {
#         "pose": os.path.join(output_folders["pose"], f"{base_name}_pose.npy"),
#         "face": os.path.join(output_folders["face"], f"{base_name}_face.npy"),
#         "left_hand": os.path.join(output_folders["left_hand"], f"{base_name}_left_hand.npy"),
#         "right_hand": os.path.join(output_folders["right_hand"], f"{base_name}_right_hand.npy"),
#     }
#     expected_filtered_files = {
#         "pose": os.path.join(filtered_output_folders["pose"], f"{base_name}_pose.npy"),
#         "face": os.path.join(filtered_output_folders["face"], f"{base_name}_face.npy"),
#         "left_hand": os.path.join(filtered_output_folders["left_hand"], f"{base_name}_left_hand.npy"),
#         "right_hand": os.path.join(filtered_output_folders["right_hand"], f"{base_name}_pose.npy"), # Typo here, should be right_hand
#     }
#     expected_filtered_files["right_hand"] = os.path.join(filtered_output_folders["right_hand"], f"{base_name}_right_hand.npy")


#     # Check if all expected output files already exist
#     if all(os.path.exists(path) for path in {**expected_files, **expected_filtered_files}.values()):
#         log.info(f"✅ Video: {video_file} - Already processed. Skipping.")
#         with list_lock:
#             processed_videos_list.append(video_file)
#         return
#     log.info(f"🚀 Video: {video_file} - Starting process...")
#     sys.stdout.flush()
#     start_time = time.time()

#     try:
#         # Load the video using MoviePy
#         video_clip = VideoFileClip(video_path)
#         frame_rate = video_clip.fps  # Get the frame rate of the video
#         total_frames = int(video_clip.duration * frame_rate)

#         # Process each frame
#         pose_data, face_data, left_hand_data, right_hand_data = [], [], [], []

#         # Log progress every 10% of frames
#         progress_interval = max(1, total_frames // 10)
#         frame_count = 0

#         for frame in video_clip.iter_frames(fps=frame_rate, dtype="uint8"):
#             # Convert the frame to an Image object
#             img = Image.fromarray(frame)

#             # Convert image to Mediapipe format
#             img_np = np.array(img)
#             results = holistic.process(img_np)

#             # Extract landmarks
#             def extract_landmarks(landmark_list, num_points):
#                 if landmark_list:
#                     return np.array([[lm.x, lm.y, lm.z] for lm in landmark_list.landmark])
#                 else:
#                     return np.zeros((num_points, 3))  # Placeholder if no detection

#             pose_data.append(extract_landmarks(results.pose_landmarks, 33))
#             face_data.append(extract_landmarks(results.face_landmarks, 468))
#             left_hand_data.append(extract_landmarks(results.left_hand_landmarks, 21))
#             right_hand_data.append(extract_landmarks(results.right_hand_landmarks, 21))

#             frame_count += 1
#             if frame_count % progress_interval == 0:
#                 progress = (frame_count / total_frames) * 100
#                 log.info(f"  🔄 Video: {video_file} - {progress:.1f}% processed ({frame_count}/{total_frames} frames)")

#         # Convert to NumPy arrays
#         pose_data_np = np.array(pose_data)
#         face_data_np = np.array(face_data)
#         left_hand_data_np = np.array(left_hand_data)
#         right_hand_data_np = np.array(right_hand_data)
#         data_np = [pose_data_np, face_data_np, left_hand_data_np, right_hand_data_np]
#         body_parts = ["pose", "face", "left_hand", "right_hand"]

#         log.info(f"  💾 Video: {video_file} - Saving data to disk...")

#         for i in range(4):
#             np.save(expected_files[body_parts[i]], data_np[i])  # Save raw poses data
#             if data_np[i].shape[0] > 7:  # Ensure enough frames for filtering
#                 filtered_pose_data = filtering(data_np[i])
#                 np.save(expected_filtered_files[body_parts[i]], filtered_pose_data)
#             else:
#                 np.save(expected_filtered_files[body_parts[i]], data_np[i])

#         # Close video to free resources
#         video_clip.close()

#         end_time = time.time()
#         duration = end_time - start_time
#         log.info(f"✅ Video: {video_file} - Completed in {duration:.2f} seconds")
#         with list_lock:
#             processed_videos_list.append(video_file)

#     except Exception as e:
#         log.info(f"❌ Video: {video_file} - Error: {str(e)}")

#     finally:
#         if 'holistic' in locals():
#             holistic.close()

# if __name__ == "__main__":
#     main()












































# version avec multiprocessing :
# import os  
# import numpy as np
# import mediapipe as mp
# import sys
# from PIL import Image
# from moviepy.editor import VideoFileClip
# from scipy.signal import savgol_filter
# from airflow.utils.log.logging_mixin import LoggingMixin
# from dotenv import load_dotenv
# import multiprocessing as mpc
# import time
# import queue
# import threading

# load_dotenv()
# log = LoggingMixin().log 
# sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

# LOCAL_SERVER = os.getenv("LOCAL_SERVER")

# # Define filtering class (Savitzky-Golay)
# class SavitchyGolayFiltering: 
#     def __init__(self, window_length: int, polynom_order: int):
#         self.window_length = window_length
#         self.polynom_order = polynom_order

#     def __call__(self, pose_sequence: np.ndarray):
#         return np.apply_along_axis(
#             lambda seq: savgol_filter(seq, self.window_length, self.polynom_order),
#             axis=0,
#             arr=pose_sequence,
#         )

# # Initialize the filter with chosen parameters
# filtering = SavitchyGolayFiltering(window_length=7, polynom_order=2)

# # Paths
# video_folder = os.path.join(LOCAL_SERVER, "cont/videos") 
# base_output_path = os.path.join(LOCAL_SERVER, "cont/poses_raw") 
# filtered_output_path = os.path.join(LOCAL_SERVER, "cont/poses") 
# output_folders = {
#     "pose": base_output_path+"/pose",
#     "face": base_output_path+"/face",
#     "left_hand": base_output_path+"/left_hand",
#     "right_hand": base_output_path+"/right_hand",
# }
# filtered_output_folders = {  
#     "pose": filtered_output_path+"/pose",
#     "face": filtered_output_path+"/face",
#     "left_hand": filtered_output_path+"/left_hand",
#     "right_hand": filtered_output_path+"/right_hand",
# }

# # Ensure output directories exist
# for folder in {**output_folders, **filtered_output_folders}.values():
#     os.makedirs(folder, exist_ok=True)

# # A thread-safe queue for logging
# log_queue = queue.Queue()

# # Thread function to process logs
# def log_worker():
#     while True:
#         message = log_queue.get()
#         if message is None:  # Sentinel to exit
#             break
#         log.info(message)
#         sys.stdout.flush()
#         log_queue.task_done()

# # Function to process a single video
# def process_video(video_file, total_videos, processed_videos):
#     video_index = processed_videos.value
#     processed_videos.value += 1

#     mp_holistic = mp.solutions.holistic
#     holistic = mp_holistic.Holistic(static_image_mode=False, model_complexity=2)
    
#     # Skip non-video files
#     if not video_file.endswith(('.mp4')): 
#         return
    
#     video_path = os.path.join(video_folder, video_file)
#     base_name = os.path.splitext(video_file)[0]

#     # Define expected output file paths
#     expected_files = {
#         "pose": os.path.join(output_folders["pose"], f"{base_name}_pose.npy"),
#         "face": os.path.join(output_folders["face"], f"{base_name}_face.npy"),
#         "left_hand": os.path.join(output_folders["left_hand"], f"{base_name}_left_hand.npy"),
#         "right_hand": os.path.join(output_folders["right_hand"], f"{base_name}_right_hand.npy"),
#     }
#     expected_filtered_files = { 
#         "pose": os.path.join(filtered_output_folders["pose"], f"{base_name}_pose.npy"),
#         "face": os.path.join(filtered_output_folders["face"], f"{base_name}_face.npy"),
#         "left_hand": os.path.join(filtered_output_folders["left_hand"], f"{base_name}_left_hand.npy"),
#         "right_hand": os.path.join(filtered_output_folders["right_hand"], f"{base_name}_right_hand.npy"),
#     }

#     # Check if all expected output files already exist
#     if all(os.path.exists(path) for path in {**expected_files, **expected_filtered_files}.values()):
#         log.info(f"✅ Video {video_index}/{total_videos}: {video_file} - Already processed. Skipping.")
#         return
#     log.info(f"🚀 Video {video_index}/{total_videos}: {video_file} - Starting process...")
#     sys.stdout.flush()
#     start_time = time.time()

#     try:
#         # Load the video using MoviePy
#         video_clip = VideoFileClip(video_path)
#         frame_rate = video_clip.fps  # Get the frame rate of the video
#         total_frames = int(video_clip.duration * frame_rate)
        
#         # Process each frame
#         pose_data, face_data, left_hand_data, right_hand_data = [], [], [], []
        
#         # Log progress every 10% of frames
#         progress_interval = max(1, total_frames // 10)
#         frame_count = 0
        
#         for frame in video_clip.iter_frames(fps=frame_rate, dtype="uint8"):
#             # Convert the frame to an Image object
#             img = Image.fromarray(frame)

#             # Convert image to Mediapipe format
#             img_np = np.array(img)
#             results = holistic.process(img_np)

#             # Extract landmarks
#             def extract_landmarks(landmark_list, num_points):
#                 if landmark_list:
#                     return np.array([[lm.x, lm.y, lm.z] for lm in landmark_list.landmark])
#                 else:
#                     return np.zeros((num_points, 3))  # Placeholder if no detection

#             pose_data.append(extract_landmarks(results.pose_landmarks, 33))
#             face_data.append(extract_landmarks(results.face_landmarks, 468))
#             left_hand_data.append(extract_landmarks(results.left_hand_landmarks, 21))
#             right_hand_data.append(extract_landmarks(results.right_hand_landmarks, 21))
            
#             frame_count += 1
#             if frame_count % progress_interval == 0:
#                 progress = (frame_count / total_frames) * 100
#                 log.info(f"  🔄 Video {video_index}/{total_videos}: {video_file} - {progress:.1f}% processed ({frame_count}/{total_frames} frames)")

#         # Convert to NumPy arrays
#         pose_data_np = np.array(pose_data)  
#         face_data_np = np.array(face_data)  
#         left_hand_data_np = np.array(left_hand_data)  
#         right_hand_data_np = np.array(right_hand_data)
#         data_np = [pose_data_np, face_data_np, left_hand_data_np, right_hand_data_np]
#         body_parts = ["pose", "face", "left_hand", "right_hand"]

#         log.info(f"  💾 Video {video_index}/{total_videos}: {video_file} - Saving data to disk...")
        
#         for i in range(4):
#             np.save(expected_files[body_parts[i]], data_np[i])  # Save raw poses data
#             if data_np[i].shape[0] > 7:  # Ensure enough frames for filtering
#                 filtered_pose_data = filtering(data_np[i])  
#                 np.save(expected_filtered_files[body_parts[i]], filtered_pose_data)  
#             else:
#                 np.save(expected_filtered_files[body_parts[i]], data_np[i])
        
#         # Close video to free resources
#         video_clip.close()
        
#         end_time = time.time()
#         duration = end_time - start_time
#         log.info(f"✅ Video {video_index}/{total_videos}: {video_file} - Completed in {duration:.2f} seconds")
        
#     except Exception as e:
#         log.info(f"❌ Video {video_index}/{total_videos}: {video_file} - Error: {str(e)}")
        
#     return

# def main():
#     # Start the logging thread
#     log_thread = threading.Thread(target=log_worker)
#     log_thread.daemon = True
#     log_thread.start()
    
#     videos_to_process = [f for f in os.listdir(video_folder) if f.endswith(('.mp4'))]
    
#     total_videos = len(videos_to_process)
#     log.info(f"Found {total_videos} videos to process")
    
#     # Create a manager to handle the shared variable processed_videos
#     with mpc.Manager() as manager:
#         processed_videos = manager.Value('i', 0)  # Shared integer variable for processed videos
        
#         # Determine the number of processes to use (leave two core free)
#         num_processes = max(1, mpc.cpu_count() - 4)
#         log.info(f"Using {num_processes} parallel processes")
        
#         # Create a pool of processes
#         with mpc.Pool(processes=num_processes) as pool:
#             # Create a list of (video_file, total_videos) tuples for each video
#             tasks = [(video, total_videos, processed_videos) for video in videos_to_process]
            
#             # Map the process_video function to the tasks
#             pool.starmap(process_video, tasks)
    
#     # Signal the logging thread to exit
#     log_queue.put(None)
#     log_thread.join() 
    
#     log.info("Processing complete! NPY files saved in separate folders.")

# if __name__ == "__main__":
#     main()











# version sans multiprocessing : 
# 
# import os
# import numpy as np
# import mediapipe as mp
# import sys
# from PIL import Image
# from moviepy.editor import VideoFileClip
# from scipy.signal import savgol_filter
# from airflow.utils.log.logging_mixin import LoggingMixin
# from dotenv import load_dotenv
# load_dotenv()
# log = LoggingMixin().log 
# sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

# LOCAL_SERVER = os.getenv("LOCAL_SERVER")

# # Initialize Mediapipe Holistic model
# mp_holistic = mp.solutions.holistic
# holistic = mp_holistic.Holistic(static_image_mode=False, model_complexity=2)

# # Define filtering class (Savitzky-Golay)
# class SavitchyGolayFiltering: 
#     def __init__(self, window_length: int, polynom_order: int):
#         self.window_length = window_length
#         self.polynom_order = polynom_order

#     def __call__(self, pose_sequence: np.ndarray):
#         return np.apply_along_axis(
#             lambda seq: savgol_filter(seq, self.window_length, self.polynom_order),
#             axis=0,
#             arr=pose_sequence,
#         )

# # Initialize the filter with chosen parameters
# filtering = SavitchyGolayFiltering(window_length=7, polynom_order=2)

# # Paths
# video_folder = os.path.join(LOCAL_SERVER, "cont/videos") 
# base_output_path = os.path.join(LOCAL_SERVER, "cont/poses_raw") 
# filtered_output_path = os.path.join(LOCAL_SERVER, "cont/poses") 
# output_folders = {
#     "pose": base_output_path+"/pose",
#     "face": base_output_path+"/face",
#     "left_hand": base_output_path+"/left_hand",
#     "right_hand": base_output_path+"/right_hand",
# }
# filtered_output_folders = {  
#     "pose": filtered_output_path+"/pose",
#     "face": filtered_output_path+"/face",
#     "left_hand": filtered_output_path+"/left_hand",
#     "right_hand": filtered_output_path+"/right_hand",
# }

# # Ensure output directories exist
# for folder in {**output_folders, **filtered_output_folders}.values():
#     os.makedirs(folder, exist_ok=True)

# videos_to_process = os.listdir(video_folder)
# progression = 0

# # Process each video
# for video_file in videos_to_process:
#     progression += 1
#     log.info(f"⏱️ Video {progression}/{len(videos_to_process)}: {video_file} ...")
#     sys.stdout.flush()
    
#     if not video_file.endswith(('.mp4')):  # Ensure it's a video file
#         continue

#     video_path = os.path.join(video_folder, video_file)

#     base_name = os.path.splitext(video_file)[0]

#     # Define expected output file paths
#     expected_files = {
#         "pose": os.path.join(output_folders["pose"], f"{base_name}_pose.npy"),
#         "face": os.path.join(output_folders["face"], f"{base_name}_face.npy"),
#         "left_hand": os.path.join(output_folders["left_hand"], f"{base_name}_left_hand.npy"),
#         "right_hand": os.path.join(output_folders["right_hand"], f"{base_name}_right_hand.npy"),
#     }
#     expected_filtered_files = { 
#         "pose": os.path.join(filtered_output_folders["pose"], f"{base_name}_pose.npy"),
#         "face": os.path.join(filtered_output_folders["face"], f"{base_name}_face.npy"),
#         "left_hand": os.path.join(filtered_output_folders["left_hand"], f"{base_name}_left_hand.npy"),
#         "right_hand": os.path.join(filtered_output_folders["right_hand"], f"{base_name}_right_hand.npy"),
#     }

#     # Check if all expected output files already exist
#     if all(os.path.exists(path) for path in {**expected_files, **expected_filtered_files}.values()):
#         print(f"✅ All output files exist for {video_path}. Skipping processing.", flush=True)
#         continue  # Skip this video

#     print(f"Processing {video_file} ...", flush=True)

#     # Load the video using MoviePy
#     video_clip = VideoFileClip(video_path)
#     frame_rate = video_clip.fps  # Get the frame rate of the video

#     # Process each frame
#     pose_data, face_data, left_hand_data, right_hand_data = [], [], [], []
    
#     for frame in video_clip.iter_frames(fps=frame_rate, dtype="uint8"):
#         # Convert the frame to an Image object
#         img = Image.fromarray(frame)

#         # Convert image to Mediapipe format
#         img_np = np.array(img)
#         results = holistic.process(img_np)

#         # Extract landmarks
#         def extract_landmarks(landmark_list, num_points):
#             if landmark_list:
#                 return np.array([[lm.x, lm.y, lm.z] for lm in landmark_list.landmark])
#             else:
#                 return np.zeros((num_points, 3))  # Placeholder if no detection

#         pose_data.append(extract_landmarks(results.pose_landmarks, 33))
#         face_data.append(extract_landmarks(results.face_landmarks, 468))    # à vérifier, possible perte d'info, 468 si visage détecté, 478 sinon, en mettant 468 j'ai pas de pb si le visage n'est pas détécté dans une frame mais jsp si je perd de l'information
#         left_hand_data.append(extract_landmarks(results.left_hand_landmarks, 21))
#         right_hand_data.append(extract_landmarks(results.right_hand_landmarks, 21))

#     # print(f"face_data type: {type(face_data)}", flush=True)
#     # print(f"face_data length: {len(face_data)}", flush=True)
#     # print(f"face_data[0] shape: {np.shape(face_data[0]) if len(face_data) > 0 else 'empty'}", flush=True)

#     # Convert to NumPy arrays
#     pose_data_np = np.array(pose_data)  
#     face_data_np = np.array(face_data)  
#     left_hand_data_np = np.array(left_hand_data)  
#     right_hand_data_np = np.array(right_hand_data)
#     data_np = [pose_data_np, face_data_np, left_hand_data_np, right_hand_data_np]
#     body_parts = ["pose", "face", "left_hand", "right_hand"]

#     for i in range(4):
#         np.save(expected_files[body_parts[i]], data_np[i])  # Save raw poses data
#         if data_np[i].shape[0] > 7:  # Ensure enough frames for filtering
#             filtered_pose_data = filtering(data_np[i])  
#             np.save(expected_filtered_files[body_parts[i]], filtered_pose_data)  
#         else:
#             np.save(expected_filtered_files[body_parts[i]], data_np[i])

            
# print("Processing complete! NPY files saved in separate folders.")





