from pathlib import Path
from typing import BinaryIO

from .base import StorageService

class LocalStorageService(StorageService):

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, object_key: str) -> Path:
        path = (self.root / object_key).resolve()

        if self.root not in path.parents:
            raise ValueError("Invalid object key")

        return path

    def put(
            self,
            object_key: str,
            data: BinaryIO,
    ) -> None:
        path = self._resolve(object_key)

        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("wb") as destination:
            while chunk := data.read(1024*1024):
                destination.write(chunk)


    def open(
        self,
        object_key: str,
    ) -> BinaryIO:
        path = self._resolve(object_key)

        if not path.is_file():
            raise FileNotFoundError(object_key)

        return path.open("rb")


    def delete(
        self,
        object_key: str,
    ) -> None:
        path = self._resolve(object_key)

        if path.exists():
            path.unlink()


    def exists(
        self,
        object_key: str,
    ) -> bool:
        return self._resolve(object_key).is_file()