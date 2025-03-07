import os
import pathlib
import glob
from typing import Optional
from typing import List

import pympi
import re
from tqdm import tqdm

from video import Video


regex_patterns = dict(
    video_filename=r'CLSFBI[\d]{4}A_S[\d]{3}_[A,B]\.mp4',
    left_hand_tier='(MG)|(MAINGAUCHE)|(GAUCHE)',
    right_hand_tier='(MD)|(MAINDROITE)|(DROITE)',
    subtitles_tier='(TRADUCTION)|(TRADCUTION)',
)


def extract_videos(eaf_path: str, eaf: Optional[pympi.Eaf] = None):
    if eaf is None:
        eaf = pympi.Eaf(file_path=eaf_path)
    videos = []
    faulty_videos = []
    eaf_filename = str(pathlib.Path(eaf_path).name)
    eaf_session = int(eaf_filename[6:8])
    eaf_task = int(eaf_filename[8:10])
    for file in eaf.get_linked_files():
        if not {'MEDIA_URL', 'MIME_TYPE'} <= file.keys():
            continue
        path_attribute = 'MEDIA_URL'
        if 'RELATIVE_MEDIA_URL' in file:
            path_attribute = 'RELATIVE_MEDIA_URL'
        video_filename = str(pathlib.Path(file[path_attribute]).name)
        video_filename_parts = video_filename.split('_')
        if video_filename_parts[0][-1] != 'A':
            video_filename_parts[0] += 'A'
            video_filename = '_'.join(video_filename_parts)
        if re.match(regex_patterns['video_filename'], video_filename):
            session = int(video_filename[6:8])
            task = int(video_filename[8:10])
            signer = int(video_filename_parts[1][1:])
            signer_letter = video_filename_parts[1][-1] if len(video_filename_parts) > 2 else '?'
            video = Video(
                session=session,
                task=task,
                angle=video_filename[10:11],
                signer=signer,
                signer_letter=signer_letter,
                video_format=video_filename[-3:],
                video_filename=video_filename,
                eaf_filename=eaf_filename,
            )
            if session != eaf_session or task != eaf_task:
                faulty_videos.append(video)
            else:
                videos.append(video)

    return videos, faulty_videos


def extract_old_tier_names(eaf: pympi.Eaf, video: Video):
    pattern_signer = f'(S?0?0?{video.signer:02})'
    for tier_key in video.tiers:
        if tier_key == 'right':
            pattern = regex_patterns['right_hand_tier']
        elif tier_key == 'left':
            pattern = regex_patterns['left_hand_tier']
        elif tier_key == 'subtitles':
            pattern = regex_patterns['subtitles_tier']
        else:
            continue
        if pattern is None:
            raise ValueError(f'Could not find tier for this video: {video.video_filename}')
        pattern = f'(({pattern})-({pattern_signer}))|(({pattern_signer})-({pattern}))'
        for tier_name in eaf.get_tier_names():
            normalized_name = tier_name.upper().replace(' ', '').replace('–', '-')
            match = re.search(pattern, normalized_name)
            if match is not None:
                video.tiers[tier_key] = tier_name
    return video.tiers


def extract_new_tier_names(eaf: pympi.Eaf, video: Video):
    for tier_name in eaf.get_tier_names():
        tier_params = eaf.get_parameters_for_tier(tier_name)
        if not tier_params.get('PARTICIPANT') == f'S{video.signer:03}':
            continue
        if tier_name.endswith('MG-LEMMES'):
            video.tiers['left'] = tier_name
        elif tier_name.endswith('MD-LEMMES'):
            video.tiers['right'] = tier_name
        elif tier_name.endswith('TRADUCTION'):
            video.tiers['subtitles'] = tier_name
        elif tier_name.endswith('MG-VARIATIONS'):
            video.tiers['left-variations'] = tier_name
        elif tier_name.endswith('MD-VARIATIONS'):
            video.tiers['right-variations'] = tier_name
    return video.tiers


def extract_annotations(eaf: pympi.Eaf, video: Video):
    for annot_key in video.annotations:
        tier_name = video.tiers[annot_key]
        if tier_name is not None:
            video.annotations[annot_key] = eaf.get_annotation_data_for_tier(tier_name)
    return video.annotations


def check_tiers(videos: List[Video], old_format=False):
    errors = []
    for video in videos:
        for tier_key in video.tiers:
            tier_name = video.tiers[tier_key]
            if old_format and 'variations' in tier_key:
                continue
            if tier_name is None:
                errors.append((
                    video,
                    f"Missing {tier_key} tier for signer {video.signer} in "
                    f"video {video.video_filename} in {video.eaf_filename}"
                ))
    return errors


class ElanParser:

    def __init__(self, old_format: bool = False):
        self.videos: list[Video] = []
        self.errors = []
        self.errors = []
        self.old = old_format

    def parse_eaf(self, eaf_path: str):
        eaf = pympi.Eaf(file_path=eaf_path)
        videos, faulty_videos = extract_videos(eaf_path, eaf=eaf)
        self.errors += [(video, 'The video does not correspond to the EAF file.') for video in faulty_videos]
        for video in videos:
            if self.old:
                extract_old_tier_names(eaf, video)
            else:
                extract_new_tier_names(eaf, video)
            extract_annotations(eaf, video)
        self.videos += videos
        self.errors += check_tiers(videos, old_format=self.old)

    def parse_all_from_dir(self, dir_path: str, show_progress=False):
        eaf_paths = list(glob.glob(os.path.join(dir_path, 'CLSFBI*/CLSFBI*.eaf')))
        # eaf_paths = list(glob.glob('./CLSFBI*/CLSFBI*.eaf', root_dir=dir_path))
        progress = tqdm(eaf_paths, disable=(not show_progress))
        for eaf_path in progress:
            progress.set_postfix_str(eaf_path)
            self.parse_eaf(os.path.join(dir_path, eaf_path))

    def get_videos(self):
        return self.videos

    def get_errors(self):
        return self.errors
