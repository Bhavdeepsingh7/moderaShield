from dataclasses import dataclass


@dataclass
class ModerationResult:
    is_flagged: bool
    category: str | None
    score: float

class ModerationEngine:

    def __init__(self):
        self.blocked_terms = {
            "spam": ["buy now", "free money", "click here"],
            "violence": ["kill", "murder", "shoot"],
            "hate": ["i hate you"],
        }


    def moderate(self, content:str) -> ModerationResult:

        text = content.lower()

        for category,terms in self.blocked_terms.items():
            for term in terms:
                if term in text:
                    return ModerationResult(
                        is_flagged=True,
                        category=category,
                        score = 1.0,
                    )


        return ModerationResult(
            is_flagged=False,
            category=None,
            score=0.0,
        )


moderation_engine = ModerationEngine()