import json

import pandas as pd

from lsfb_processing.annotations.utils import load_annotations


def create_instance_list(
        cont_root: str,
        isol_root: str,
        annotations: str = 'signs_both_hands',
        instance_list_filename: str = 'instances.csv',
):
    annotations = load_annotations(cont_root, annotations)

    sign_records = []  # id, sign, signer, start, end
    for video_id in annotations:
        for annot in annotations[video_id]:
            start_ms, end_ms, gloss = int(annot['start']), int(annot['end']), annot['value']
            sign_id = f'{video_id}_{start_ms}_{end_ms}'
            signer = video_id.split('_')[1]
            sign_records.append((sign_id, gloss, signer, start_ms, end_ms))

    instances = pd.DataFrame.from_records(sign_records, columns=['id', 'sign', 'signer', 'start', 'end'])
    instances.to_csv(f'{isol_root}/{instance_list_filename}', index=False)
