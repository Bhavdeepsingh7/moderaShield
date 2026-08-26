import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from app.moderation.ml_engine import predict


result = predict(
    "I'm going to kill you."
)

print(result)