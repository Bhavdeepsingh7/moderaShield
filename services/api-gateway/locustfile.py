import os
import uuid
from locust import HttpUser, task, between

API_KEY = os.environ.get("MODERASHIELD_API_KEY")

class ModeraShieldUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        if not API_KEY:
            raise RuntimeError(
                "Set MODERASHIELD_API_KEY before starting Locust."
            )

    @task
    def submit_moderation(self):
        self.client.post(
            "/api/v1/moderate/",
            json={
                "content_type": "text",
                "content": "I enjoy helping people and building useful software applications."
            },
            headers={
                "X-API-Key": API_KEY,
                "Idempotency-Key": str(uuid.uuid4()),
            },
            name="POST /api/v1/moderate/",
        )
