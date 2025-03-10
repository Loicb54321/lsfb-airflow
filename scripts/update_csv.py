import os
import glob
import xml.etree.ElementTree as ET
import csv
from convert_video_files import parse_elan, parse_media_files
from dotenv import load_dotenv
load_dotenv()

LOCAL_SERVER = os.getenv("LOCAL_SERVER")

input_folder = os.path.join(LOCAL_SERVER, "ELAN_OUT")
instances_csv = os.path.join(LOCAL_SERVER, "isol/instances.csv")
subtitles_csv = os.path.join(LOCAL_SERVER, "cont/subtitles.csv")

"""Process all ELAN files in the given folder and save results to a CSV file."""
elan_files = glob.glob(os.path.join(input_folder, "*.eaf"))
new_words = []
new_subtitles = []

for elan_file in elan_files:
    annotations, media_mapping, subtitles = parse_elan(elan_file)
    media_mapping = {key: os.path.join(input_folder, "/".join(value.split("/")[-1:])) for key, value in media_mapping.items()}
    print(f"🔍 Found {len(annotations)} annotations.", flush=True)
    print(f"🔍 Found {len(subtitles)} subtitles.", flush=True)
    print("🎥 Media mapping:", media_mapping, flush=True)

    for ann in annotations:
        participant = ann.get("participant")
        if participant not in media_mapping:
            print(f"⚠️ No media file found for participant {participant} for annotation '{ann['word']}'. Skipping.", flush=True)
            continue
        video_file = media_mapping[participant]
        print(f"📹 Video file for participant {participant}: {video_file}", flush=True)
        if not os.path.isabs(video_file):
            elan_dir = os.path.dirname(os.path.join(input_folder, elan_file))
            video_file = os.path.normpath(os.path.join(elan_dir, video_file))
        base_video_name = os.path.basename(video_file).split(".")[0]   
        output_name = f"{base_video_name}_{ann['start']}_{ann['end']}"
        new_words.append ([output_name, ann["word"], participant, str(ann["start"]), str(ann["end"])])

    for sub in subtitles:
        participant = sub.get("participant")
        if participant not in media_mapping:
            print(f"⚠️ No media file found for participant {participant} for subtitle '{sub['word']}'. Skipping.", flush=True)
            continue
        video_file = media_mapping[participant]
        print(f"📹 Video file for participant {participant}: {video_file}", flush=True)
        if not os.path.isabs(video_file):
            elan_dir = os.path.dirname(os.path.join(input_folder, elan_file))
            video_file = os.path.normpath(os.path.join(elan_dir, video_file))
        base_video_name = os.path.basename(video_file).split(".")[0]   
        output_name = f"{base_video_name}_{sub['start']}_{sub['end']}"
        new_subtitles.append ([output_name, sub["word"], participant, str(sub["start"]), str(sub["end"])])


with open(instances_csv, mode="w", newline="", encoding="utf-8") as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["id", "sign", "signer", "start", "end"])
    for row in new_words:
        csv_writer.writerow(row)

with open(subtitles_csv, mode="w", newline="", encoding="utf-8") as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["id", "translation", "signer", "start", "end"])
    for row in new_subtitles:
        print(row, flush=True)
        csv_writer.writerow(row)

print(f"CSV file saved: {instances_csv}")
print(f"✅ Total subtitles written: {len(new_subtitles)}", flush=True)
