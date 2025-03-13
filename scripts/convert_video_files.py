import os
import sys
import argparse
import xml.etree.ElementTree as ET
import csv
import json
from collections import Counter
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv
load_dotenv()

LOCAL_SERVER = os.getenv("LOCAL_SERVER")

# Path to the CSV files and video cont directory
# csv_path = "/opt/airflow/data/sample-lsfb/local_server/isol/instances.csv"
# sign_count_csv_path = "/opt/airflow/data/sample-lsfb/local_server/isol/sign_counts.csv"
# sorted_csv_path = "/opt/airflow/data/sample-lsfb/local_server/isol/sorted_instances.csv"
base_path = os.path.join(LOCAL_SERVER, "cont/videos") 

tier_id_filter = ["SA-MG-LEMMES", "SA-MD-LEMMES", "SB-MG-LEMMES", "SB-MD-LEMMES"]
translation_tier_id_filter = ["SA-TRADUCTION", "SB-TRADUCTION"]
skip = ["UNDECIPHERABLE", "EMPTY GLOSS"]

def parse_media_files(root):
    """Parse the <HEADER> section to extract media file mapping."""
    media_mapping = {}
    header = root.find("HEADER")
    if header is not None:
        for media_desc in header.findall("MEDIA_DESCRIPTOR"):
            media_url = media_desc.get("MEDIA_URL")
            if media_url:
                basename = os.path.basename(media_url)
                parts = basename.split("_")
                if len(parts) >= 2:
                    participant = parts[1]  
                    media_mapping[participant] = media_url
    print(f"Media mapping: {media_mapping}", flush=True)
    return media_mapping

def parse_elan(elan_file: str):
    """Parse the ELAN file and return annotations and media mapping."""
    print("Parsing ELAN file...", flush=True)  
    tree = ET.parse(elan_file)
    root = tree.getroot()
    
    time_slots = {}
    for time_slot in root.findall(".//TIME_SLOT"):
        ts_id = time_slot.get("TIME_SLOT_ID")
        ts_value = time_slot.get("TIME_VALUE")
        if ts_value is not None:
            time_slots[ts_id] = int(ts_value)
    
    annotations = []
    subtitles = []
    seen_annotations = set()  #  Track seen annotations to remove duplicates

    for tier in root.findall(".//TIER"):
        tier_id = tier.get("TIER_ID")  # Get TIER_ID
        is_subtitle = False
        if translation_tier_id_filter and tier_id in translation_tier_id_filter:
            is_subtitle = True

        elif tier_id_filter and tier_id not in tier_id_filter:
            continue  # Skip tiers not in the filter
        participant = tier.get("PARTICIPANT")
        for annotation in tier.findall(".//ALIGNABLE_ANNOTATION"):
            ts1 = annotation.get("TIME_SLOT_REF1")
            ts2 = annotation.get("TIME_SLOT_REF2")
            ann_value_elem = annotation.find("ANNOTATION_VALUE")
            if ts1 in time_slots and ts2 in time_slots and ann_value_elem is not None:
                word = ann_value_elem.text.strip()
                annotation_tuple = (participant, time_slots[ts1], time_slots[ts2], word)
                if word in skip:
                    continue               
                if annotation_tuple not in seen_annotations:  #  Remove duplicates
                    if not is_subtitle:
                        annotations.append({
                            "start": time_slots[ts1],
                            "end": time_slots[ts2],
                            "word": word,
                            "participant": participant
                        })
                        seen_annotations.add(annotation_tuple)
                    else:
                        subtitles.append({
                            "start": time_slots[ts1],
                            "end": time_slots[ts2],
                            "word": word,
                            "participant": participant
                        })
                        seen_annotations.add(annotation_tuple)

    media_mapping = parse_media_files(root)
    return annotations, media_mapping, subtitles

def extract_segment(video_file: str, start_ms: int, end_ms: int, output_file: str):
    """Extract a segment from the video using MoviePy."""
    # print(f"🔍 Extracting segment: {video_file} ({start_ms}ms to {end_ms}ms)", flush=True)
    start_sec = start_ms / 1000.0
    end_sec = end_ms / 1000.0
    if os.path.exists(output_file):  #  Skip extraction if file exists                               # peut être qu'il faudra suprimer/modifier
        print(f"⚠️ File already exists, skipping extraction: {output_file}", flush=True)
        return True
    try:
        clip = VideoFileClip(video_file).subclip(start_sec, end_sec)
        clip.write_videofile(output_file, codec="libx264", audio_codec="aac", verbose=True, logger=None)
        print(f"✅ Successfully saved: {output_file}", flush=True)
        return True
    except Exception as e:
        print(f"❌ Error extracting segment ({start_sec}s to {end_sec}s) from {video_file}: {e}", flush=True)
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--elan_file", type=str, required=True, help="Path to ELAN file")
    parser.add_argument("--output_dir", type=str, required=True, help="Output video directory")
    args = parser.parse_args()

    print(f"📂 ELAN File: {args.elan_file}")
    print(f"📁 Output Directory: {args.output_dir}")

    if not os.path.isfile(args.elan_file):
        raise FileNotFoundError(f"ELAN file does not exist: {args.elan_file}")

    os.makedirs(args.output_dir, exist_ok=True)

    annotations, media_mapping, subtitles = parse_elan(args.elan_file)
    if not annotations:
        print("⚠️ No annotations found in the ELAN file.", flush=True)
        sys.exit(1)
    # print (f'subtitles : {subtitles}', flush=True)  
    
    media_mapping = {key: os.path.join(base_path, "/".join(value.split("/")[-1:])) for key, value in media_mapping.items()}

    print(f"🔍 Found {len(annotations)} annotations.", flush=True)
    print("🎥 Media mapping:", media_mapping, flush=True)                                 

    # #  Load existing CSV entries to avoid duplicates
    # existing_entries = set()
    # if os.path.exists(csv_path):
    #     with open(csv_path, "r", newline="", encoding="utf-8") as f:
    #         reader = csv.reader(f)
    #         next(reader)  # Skip header
    #         for row in reader:
    #             existing_entries.add(tuple(row))

    # new_csv_rows = []
    
    for idx, ann in enumerate(annotations):
        participant = ann.get("participant")
        if participant not in media_mapping:
            print(f"⚠️ No media file found for participant {participant} for annotation '{ann['word']}'. Skipping.", flush=True)
            continue
        
        video_file = media_mapping[participant]
        # print(f"📹 Video file for participant {participant}: {video_file}", flush=True)
        if not os.path.isabs(video_file):
            elan_dir = os.path.dirname(os.path.abspath(args.elan_file))
            video_file = os.path.normpath(os.path.join(elan_dir, video_file))
        
        base_video_name = os.path.basename(video_file).split(".")[0]  
        
        output_filename = f"{base_video_name}_{ann['start']}_{ann['end']}.mp4"
        output_path = os.path.join(args.output_dir, output_filename)

        # new_entry = (base_video_name, ann["word"], participant, str(ann["start"]), str(ann["end"]))

        # if new_entry not in existing_entries:  #  Avoid duplicate CSV entries
        #     new_csv_rows.append(new_entry)
        #     existing_entries.add(new_entry)  # Prevent future duplicates
        # else:
        #     print(f"⚠️ Duplicate entry detected, skipping: {new_entry}", flush=True)

        extract_segment(video_file, ann["start"], ann["end"], output_path)  

    # # Append only unique rows to CSV
    # with open(csv_path, "a", newline="", encoding="utf-8") as f:
    #     writer = csv.writer(f)
    #     for row in new_csv_rows:
    #         writer.writerow(row)

    # # Read the CSV and store rows
    # with open(csv_path, "r", newline="", encoding="utf-8") as f:
    #     reader = csv.reader(f)
    #     header = next(reader)  # Read the header (if any)
    #     rows = [row for row in reader]

    # # Sort the rows by row[0] (base video name) and then by row[3] (start time)
    # sorted_rows = sorted(rows, key=lambda row: (row[0], int(row[3])))

    # # Write the sorted rows to a new CSV file
    # with open(sorted_csv_path, "w", newline="", encoding="utf-8") as f:
    #     writer = csv.writer(f)
    #     writer.writerow(header)  # Write the header
    #     writer.writerows(sorted_rows)  # Write the sorted rows

    # print(f"CSV file has been sorted and saved to {sorted_csv_path}")

    # # Count the occurrences of each sign in column 1 (row[1])
    # signs = [row[1].strip() for row in rows]  # Get the signs (strip to remove any extra spaces)
    # sign_counts = Counter(signs)

    # # Write the sign counts to a new CSV file
    # with open(sign_count_csv_path, "w", newline="", encoding="utf-8") as f:
    #     writer = csv.writer(f)
    #     writer.writerow(["sign", "Occurrences"])  # Write header
    #     for sign, count in sign_counts.most_common():  # Sort by most common (highest count first)
    #         writer.writerow([sign, count])

    # print(f"sign counts have been saved to {sign_count_csv_path}")


if __name__ == "__main__":
    main()