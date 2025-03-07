import pympi
import pathlib
import glob
import os

from tqdm import tqdm

from parser_ import ElanParser


def get_lemme_from_variation(variation: str):
    # Special case : description signs
    if variation.startswith('DS:'):
        return 'DS'

    # Eliminate variants
    variation = variation.replace('*', '')
    variation = variation.replace('+', '')
    variation = variation.split('(')[0]
    variation = variation.replace('-1H', '')
    variation = variation.replace('-2H', '')

    return variation


def convert_elan_file(filepath: str, dest_folder: str):
    parser = ElanParser(old_format=True)
    parser.parse_eaf(filepath)
    if len(parser.videos) < 2:
        print(f"Could not convert ELAN file: {filepath}.")
        return
    if len(parser.errors) > 0:
        print(f"ELAN parsing errors: {filepath}.")
        print(parser.errors)
        return

    template_path = str(pathlib.Path(__file__).parent / 'template.eaf')
    eaf = pympi.Eaf(template_path)

    session_code = None
    task_code = None

    for index, video in enumerate(parser.videos):
        session_code = f'{video.session:02d}'
        task_code = f'{video.task:02d}'
        signer_letter = 'A' if index % 2 == 0 else 'B'
        video_path = f"./videos/CLSFB - {video.session:02d} ok/{video.video_filename}"
        eaf.add_linked_file(video_path, relpath=video_path, mimetype='video/mp4')

        for key in ['left', 'right']:
            annotations = video.annotations[key]
            tier_hand = 'MG' if key == 'left' else 'MD'
            tier_lemmes = f'S{signer_letter}-{tier_hand}-LEMMES'
            eaf.add_tier(tier_lemmes, ling="LSFB", part=f'S{video.signer:03d}')
            tier_variations = f'S{signer_letter}-{tier_hand}-VARIATIONS'
            eaf.add_tier(tier_variations, ling="LSFB", part=f'S{video.signer:03d}')
            if annotations is None:
                continue
            for start, end, value in annotations:
                lemme = get_lemme_from_variation(value)
                eaf.add_annotation(tier_lemmes, start, end, lemme)
                eaf.add_annotation(tier_variations, start, end, value)

        subtitle_tier = f'S{signer_letter}-TRADUCTION'
        eaf.add_tier(subtitle_tier, ling="Traduction", part=f'S{video.signer:03d}')
        subtitles = video.annotations['subtitles']
        if subtitles is not None:
            for start, end, value in subtitles:
                eaf.add_annotation(subtitle_tier, start, end, value)

    # dest_path = f"{dest_folder}/CLSFBI{session_code}"
    # os.makedirs(dest_path, exist_ok=True)
    # dest_path = dest_path + f'/CLSFBI{session_code}{task_code}.eaf'

    dest_path = os.path.join(dest_folder, f"CLSFBI{session_code}{task_code}.eaf")
    os.makedirs(dest_folder, exist_ok=True)
    eaf.to_file(dest_path)


def convert_all_elan_files(elan_folder: str, dest_folder: str, show_progress=True):
    eaf_paths = list(glob.glob(os.path.join(elan_folder, 'CLSFBI*/CLSFBI*.eaf')))
    #eaf_paths = list(glob.glob('./CLSFBI*/CLSFBI*.eaf', root_dir=elan_folder))
    print("eaf path:", eaf_paths, flush=True)
    print("elan folder path:", elan_folder, flush=True)
    print("dest path:", dest_folder, flush=True)
    progress = tqdm(eaf_paths, disable=(not show_progress))
    for eaf_path in progress:
        progress.set_postfix_str(eaf_path)
        convert_elan_file(eaf_path, dest_folder)
        # convert_elan_file(f"{elan_folder}/{eaf_path}", dest_folder)
