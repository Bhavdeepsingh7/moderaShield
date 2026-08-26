from pathlib import Path
import json

import torch 

from huggingface_hub import hf_hub_download
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

MODEL_ID = "bhavdeepsingh/moderashield-text-moderation"

device = torch.device(
    "cuda"
 if torch.cuda.is_available() else "cpu"
 )

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID
)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_ID
)

model.to(device)
model.eval()

threshold_path = hf_hub_download(
    repo_id = MODEL_ID,
    filename = "thresholds.json",
)

label_map_path = hf_hub_download(
    repo_id = MODEL_ID,
    filename= "label_map.json"
)

with open(threshold_path) as f:
    thresholds = json.load(f)

with open(label_map_path) as f:
    label_map= json.load(f)

print("Moderation model loaded")


@torch.inference_mode()
def predict(text: str) -> dict:

    encoded = tokenizer(
        text, 
        max_length = 256,
        truncation = True,
        padding = True,
        return_tensors = "pt",
    )

    encoded = {
        key: value.to(device)
        for key, value in encoded.items()
    }

    logits = model(**encoded).logits

    probabilities = (
        torch.sigmoid(logits)
        .squeeze()
        .cpu()
        .tolist()
    )

    labels = label_map["labels"]

    scores = {}

    categories = []

    for i, label in enumerate(labels):

        score = float(probabilities[i])

        scores[label] = round(score, 4)

        if score >= thresholds[label]:
            categories.append(label)

    return{
        "is_flagged": len(categories) >0,
        "categories": categories,
        "scores": scores,
    }

