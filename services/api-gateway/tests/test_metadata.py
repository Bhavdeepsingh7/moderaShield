from huggingface_hub import hf_hub_download
import json

MODEL_ID = "bhavdeepsingh/moderashield-text-moderation"

threshold_path = hf_hub_download(
    repo_id=MODEL_ID,
    filename="thresholds.json",
)

label_path = hf_hub_download(
    repo_id=MODEL_ID,
    filename="label_map.json",
)

with open(threshold_path) as f:
    thresholds = json.load(f)

with open(label_path) as f:
    labels = json.load(f)

print(thresholds)
print(labels)