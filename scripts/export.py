import json

from parser_ import ElanParser


def create_annotation_files(elan_folder: str, dest_folder: str):
    print("Parsing ELAN files...")
    parser = ElanParser()
    parser.parse_all_from_dir(elan_folder)
    annotations = {
        'signs_left_hand': {},
        'signs_right_hand': {},
        'subtitles': {},
    }
    print("Saving annotations in JSON format...")
    for video in parser.videos:
        video_id = video.video_filename.replace('.mp4', '')
        for annot_type in video.annotations:
            if annot_type == 'left':
                filename = 'signs_left_hand'
            elif annot_type == 'right':
                filename = 'signs_right_hand'
            elif annot_type == 'subtitles':
                filename = 'subtitles'
            else:
                continue

            video_annotations = []
            source_annotations = video.annotations[annot_type]

            if source_annotations is None:
                continue
            if annot_type == 'subtitles' and len(source_annotations) < 1:
                continue

            for start, end, value in source_annotations:
                video_annotations.append({
                    'start': start,
                    'end': end,
                    'value': value,
                })
            annotations[filename][video_id] = video_annotations

    for filename in annotations:
        with open(f"{dest_folder}/{filename}.json", 'w') as file:
            json.dump(annotations[filename], file, indent=2)
    print("Done.")
