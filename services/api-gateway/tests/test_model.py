from transformers import AutoModelForSequenceClassification
from transformers import AutoTokenizer

MODEL_ID = "bhavdeepsingh/moderashield-text-moderation"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)

print("Model loaded successfully.")