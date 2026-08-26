from moderashield import Moderashield

# Initialize client
client = Moderashield(
    api_key="msk_y1JBJm2QmbV9kbDO0g8Sp6BBI8drTopXVp_ehUFJMWE",
    base_url="http://localhost:8000"
)

# Submit request
result = client.moderate_text(
    "I will kill you"
)

if result.is_flagged:
    print(f"Content Blocked! Triggered flags: {result.categories}")
    print(f"Toxic category score: {result.scores.get('toxic')}")
else:
    print("Content safe!")