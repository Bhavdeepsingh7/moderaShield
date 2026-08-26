from moderashield import Moderashield


client = Moderashield(api_key="ms_live_xxxxxxxxx")
result = client.moderate_text("I am going to hurt you")

print("Flagged:", result.is_flagged)
print("Categories:", result.categories)
print("Scores:", result.scores)
