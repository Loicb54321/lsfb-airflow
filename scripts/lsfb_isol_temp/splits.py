import os

import pandas as pd

from lsfb_processing.lsfb_cont.splits import load_split, save_split
from sklearn.model_selection import GroupKFold


def convert_split(cont_root: str, isol_root: str, split_name: str):
    isol_instances = pd.read_csv(f"{isol_root}/instances.csv")
    cont_split = load_split(cont_root, split_name)

    split_instances = []
    for cont_instance_id in cont_split:
        split_instances += isol_instances.loc[isol_instances['id'].str.startswith(cont_instance_id), 'id'].tolist()

    split_instances = list(set(split_instances))
    save_split(isol_root, split_name, split_instances)


def convert_all_splits(cont_root: str, isol_root: str):
    split_filenames = os.listdir(f"{cont_root}/metadata/splits")
    for filename in split_filenames:
        convert_split(cont_root, isol_root, filename.replace('.json', ''))


def create_folds(root: str, n_splits: int = 5):
    instances = pd.read_csv(f'{root}/instances.csv')
    groups = instances['signer'].values
    instances['fold'] = -1

    group_k_fold = GroupKFold(n_splits=n_splits)
    for index, (_, test_index) in enumerate(group_k_fold.split(instances['id'], groups=groups)):
        instances.loc[test_index, 'fold'] = index

    for fold_idx in range(n_splits):
        fold_instances = instances.query(f'fold == {fold_idx}')['id'].tolist()
        save_split(root, f'fold_{fold_idx}', fold_instances)


