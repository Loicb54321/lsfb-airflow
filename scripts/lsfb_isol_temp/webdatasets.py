import tarfile
import json
import collections
import io

import numpy as np
from tqdm import tqdm

from lsfb_dataset.datasets import LSFBIsolConfig, LSFBIsolLandmarks
from lsfb_processing.utils.tar import add_file_to_tar
from lsfb_processing.utils.folds import create_balanced_nonoverlapping_folds


def _load_instance_to_shard(
        shard_file: tarfile.TarFile,
        poses: dict[str, np.ndarray],
        label_index: int,
        signer_id: int,
        parent_id: str,
        start: int,
        end: int,
):
    instance_id = f"{parent_id}_{start}_{end}"
    for body_part, pose in poses.items():
        add_file_to_tar(f"{instance_id}.pose.{body_part}.npy", shard_file, pose)
    add_file_to_tar(f"{instance_id}.label.idx", shard_file, bytes(str(label_index), "ascii"))
    add_file_to_tar(f"{instance_id}.signer.id", shard_file, bytes(str(signer_id), "ascii"))
    metadata = dict(
        start=int(start),
        end=int(end),
        parent_id=str(parent_id),
    )
    add_file_to_tar(f"{instance_id}.metadata.json", shard_file, json.dumps(metadata).encode("utf-8"))


def build_lsfb_isol_webdataset(root: str, dest_dir: str, n_shards: int = 5, n_labels: int = 500):
    dataset = LSFBIsolLandmarks(
        LSFBIsolConfig(
            root=root,
            split="all",
            landmarks=("upper_pose", "left_hand", "right_hand", "lips"),
            n_labels=n_labels,
        )
    )
    metadata = dataset.instance_metadata.set_index("id")
    metadata['signer'] = metadata['signer'].str.replace('S', '').astype('int32')
    signer_distribution = dict(collections.Counter(metadata.loc[:, 'signer'].tolist()))
    _, signer_to_fold_mapping, _ = create_balanced_nonoverlapping_folds(signer_distribution, n_shards)

    shard_buffers = [io.BytesIO() for _ in range(n_shards)]
    shard_files = [tarfile.open(fileobj=buffer, mode="w") for buffer in shard_buffers]

    # noinspection PyTypeChecker
    progress_bar = tqdm(enumerate(dataset), total=len(dataset), unit='instance')
    for index, (poses, label) in progress_bar:
        instance_id = dataset.instances[index]
        parent_id = '_'.join(instance_id.split('_')[:-2])
        start = metadata.loc[instance_id, "start"]
        end = metadata.loc[instance_id, "end"]
        signer_id = metadata.loc[instance_id, "signer"]
        file = shard_files[signer_to_fold_mapping[signer_id]]
        _load_instance_to_shard(
            file,
            poses,
            label,
            signer_id,
            parent_id,
            start,
            end,
        )

    for index, buffer in enumerate(shard_buffers):
        buffer.seek(0)
        filename = f'shard_{index:06}.tar'
        with open(f"{dest_dir}/{filename}", 'wb') as file:
            file.write(buffer.getvalue())
        shard_files[index].close()


if __name__ == "__main__":
    build_lsfb_isol_webdataset(
        "/run/media/ppoitier/ppoitier/datasets/sign-languages/lsfb/isol",
        "/run/media/ppoitier/ppoitier/datasets/sign-languages/lsfb/isol/shards/2000",
        n_labels=2000,
    )
