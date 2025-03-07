import os
import re
import json
import random

# Paths
DATABASE = "/opt/airflow/data/sample-lsfb/local_server/isol/videos"
SPLIT_PATH_ISOL = "/opt/airflow/data/sample-lsfb/local_server/isol/metadata/splits"
SPLIT_PATH_CONT = "/opt/airflow/data/sample-lsfb/local_server/cont/metadata/splits"

sample_size = 100

# Regex to extract signer (SXXX)
SIGNER_REGEX = re.compile(r"_S(\d{3})_")

def get_files_by_signer():
    """Group files by signer (SXXX) and count total videos per signer."""
    signer_dict = {}

    for file in os.listdir(DATABASE):
        match = SIGNER_REGEX.search(file)
        if match:
            signer = match.group(1)  # Extract SXXX
            if signer not in signer_dict:
                signer_dict[signer] = []
            signer_dict[signer].append(file)

    return signer_dict

def balanced_split():
    """Split dataset into 5 20% splits and creates training and testing ensuring ~80/20 video count split."""
    signer_dict = get_files_by_signer()

    # Sort signers by total video count (to balance properly)
    signers_sorted = sorted(signer_dict.keys(), key=lambda s: len(signer_dict[s]), reverse=True)

    # Assign signers iteratively to balance 20/20/20/20/20 total video count
    train_signers, test_signers = set(), set()
    split1_signers, split2_signers, split3_signers, split4_signers, split5_signers = set(), set(), set(), set(), set()
    split1_files, split2_files, split3_files, split4_files, split5_files = [], [], [], [], []
    train_files, test_files = [], []
    all_files = []
    sample_files = []
    total_videos = sum(len(files) for files in signer_dict.values())

    target_size = int(total_videos * 0.2)
    current_size = 0

    for signer in signers_sorted:
        if current_size + len(signer_dict[signer]) <= target_size:
            train_signers.add(signer)
            train_files.extend(signer_dict[signer])
            split1_signers.add(signer)
            split1_files.extend(signer_dict[signer])
            current_size += len(signer_dict[signer])
        elif current_size + len(signer_dict[signer]) <= 2*target_size:
            train_signers.add(signer)
            train_files.extend(signer_dict[signer])
            split2_signers.add(signer)
            split2_files.extend(signer_dict[signer])
            current_size += len(signer_dict[signer])
        elif current_size + len(signer_dict[signer]) <= 3*target_size:
            train_signers.add(signer)
            train_files.extend(signer_dict[signer])
            split3_signers.add(signer)
            split3_files.extend(signer_dict[signer])
            current_size += len(signer_dict[signer])
        elif current_size + len(signer_dict[signer]) <= 4*target_size:
            train_signers.add(signer)
            train_files.extend(signer_dict[signer])
            split4_signers.add(signer)
            split4_files.extend(signer_dict[signer])
            current_size += len(signer_dict[signer])
        else:
            test_signers.add(signer)
            test_files.extend(signer_dict[signer])
            split5_signers.add(signer)
            split5_files.extend(signer_dict[signer])
        all_files.extend(signer_dict[signer])      

    # Sample
    for i in range(min(sample_size, len(all_files))):
        sample_files.append(all_files[i])

    # Ensure no overlap
    assert not (set(train_files) & set(test_files)), "⚠️ Overlapping data detected!"

    # Save to JSON for reproducibility
    splits = {"train": train_files, "test": test_files, "fold_0": split1_files, "fold_1": split2_files, "fold_2": split3_files, "fold_3": split4_files, "fold_4": split5_files, "all": all_files, "mini_sample": sample_files}
    for split_name, split_data in splits.items():
        with open(os.path.join(SPLIT_PATH_ISOL, f'{split_name}.json'), "w") as f:
            json.dump(split_data, f, indent=4)
        base_videos = set(re.sub(r"(_\d+)+\.mp4$", ".mp4", filename) for filename in split_data)
        base_videos = sorted(base_videos)
        with open(os.path.join(SPLIT_PATH_CONT, f'{split_name}.json'), "w") as f:
            json.dump(base_videos, f, indent=4)
            

    print(f"✅ Dataset split complete! Training: {len(train_files)} videos, Testing: {len(test_files)} videos")
    print(f"🔹 Train Signers: {len(train_signers)}, Test Signers: {len(test_signers)}")

if __name__ == "__main__":
    balanced_split()
