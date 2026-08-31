from abc import ABC , abstractmethod
from pathlib import Path
from typing import BinaryIO

class StorageService(ABC):

    @abstractmethod
    def put(
        self,
        object_key: str,
        data: BinaryIO,
    ) -> None:
        """Store an object"""


    @abstractmethod
    def open(
        self,
        object_key: str,
    ) -> BinaryIO:
        """Open an object for streaming reads"""


    @abstractmethod
    def delete(
        self,
        object_key:str,
    ) -> None:
        """Delete an object"""


    @abstractmethod
    def exists(
        self,
        object_key: str,
    ) -> bool:
        """Return whether an object exists"""