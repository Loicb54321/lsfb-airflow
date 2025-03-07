import pathlib
import json
from math import floor, ceil
import gc

import cv2
from tqdm import tqdm
import numpy as np

from lsfb_processing.annotations.utils import load_annotations


def isolate_videos(video_filepath: str, dest_folder: str, annotations: list[dict], padding=(0, 0)):
    video_filepath = pathlib.Path(video_filepath)
    dest_folder = pathlib.Path(dest_folder)
    video_filename = video_filepath.name.replace('.mp4', '')
    cap = cv2.VideoCapture(str(video_filepath))

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    size = (frame_width, frame_height)
    fps = cap.get(cv2.CAP_PROP_FPS)

    for annot in annotations:
        start_ms, end_ms = int(annot['start']), int(annot['end'])
        segment_filename = f'{video_filename}_{start_ms}_{end_ms}.mp4'
        start_frame = max(0, floor(start_ms * fps / 1000) - padding[0])
        end_frame = min(n_frames, ceil(end_ms * fps / 1000) + padding[0])

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(dest_folder/segment_filename), fourcc, fps, size)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        for frame_index in range(start_frame, end_frame+1):
            success, frame = cap.read()
            if not success:
                break
            writer.write(frame)
        writer.release()

    cap.release()


def isolate_poses(cont_root: str, isol_root: str, video_id: str, annotations, padding=(0, 0), raw=False, fps=50):
    pose_folder = 'poses_raw' if raw else 'poses'
    for pose_type in ['pose', 'face', 'left_hand', 'right_hand']:
        pose = np.load(f"{cont_root}/{pose_folder}/{pose_type}/{video_id}.npy").astype('float16')
        n_frames = pose.shape[0]
        for annot in annotations:
            start_ms, end_ms = int(annot['start']), int(annot['end'])
            start_frame = max(0, floor(start_ms * fps / 1000) - padding[0])
            end_frame = min(n_frames, ceil(end_ms * fps / 1000) + padding[0])
            np.save(
                f"{isol_root}/{pose_folder}/{pose_type}/{video_id}_{start_ms}_{end_ms}.npy",
                pose[start_frame:end_frame+1]
            )


def isolate_all_signs(cont_root: str, isol_root: str, show_progress=True):
    annotations = load_annotations(cont_root, 'signs_both_hands')

    for video_id in tqdm(annotations, disable=(not show_progress)):
        video_annotations = annotations[video_id]
        isolate_poses(cont_root, isol_root, video_id, video_annotations, padding=(1, 1))
        isolate_poses(cont_root, isol_root, video_id, video_annotations, padding=(1, 1), raw=True)
        isolate_videos(
            video_filepath=f"{cont_root}/videos/{video_id}.mp4",
            dest_folder=f"{isol_root}/videos",
            annotations=annotations[video_id],
            padding=(1, 1),
        )
        gc.collect()
