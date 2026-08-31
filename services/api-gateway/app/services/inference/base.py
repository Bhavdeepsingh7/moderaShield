from abc import ABC, abstractmethod
from typing import Any

class InferenceService(ABC):
    @abstractmethod
    def moderate(self, content: Any) -> dict:
        """Run moderation inference for a supported modality"""
        raise NotImplementedError
