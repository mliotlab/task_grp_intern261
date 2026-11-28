"""Safe local storage for original and annotated shelf images."""

from __future__ import annotations

import os
import re
from pathlib import Path

import cv2
import numpy as np

STORE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ANALYSIS_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ArtifactAlreadyExistsError(FileExistsError):
    """Raised when an analysis would overwrite previously stored images."""


class ImageStorage:
    def __init__(self, image_dir: Path) -> None:
        self.image_dir = image_dir.resolve()
        self._owned_artifacts: dict[Path, tuple[int, int]] = {}

    def save(
        self,
        store_id: str,
        analysis_id: str,
        original_bytes: bytes,
        annotated_image: np.ndarray,
        extension: str,
    ) -> tuple[str, str]:
        if not STORE_ID_PATTERN.fullmatch(store_id):
            raise ValueError("Invalid store_id")
        if not ANALYSIS_ID_PATTERN.fullmatch(analysis_id):
            raise ValueError("Invalid analysis_id")
        if extension not in {".jpg", ".png"}:
            raise ValueError("Unsupported image extension")

        output = cv2.imencode(extension, annotated_image)
        if not output[0]:
            raise ValueError("Could not encode annotated image")

        directory = (self.image_dir / store_id).resolve()
        if not directory.is_relative_to(self.image_dir):
            raise ValueError("Image path escapes IMAGE_DIR")
        directory.mkdir(parents=True, exist_ok=True)

        original = directory / f"{analysis_id}_original{extension}"
        annotated = directory / f"{analysis_id}_annotated{extension}"
        created: list[Path] = []
        try:
            self._exclusive_write(original, original_bytes)
            created.append(original)
            self._exclusive_write(annotated, output[1].tobytes())
            created.append(annotated)
        except Exception:
            self._remove_owned(created)
            raise

        return (
            original.relative_to(self.image_dir).as_posix(),
            annotated.relative_to(self.image_dir).as_posix(),
        )

    def remove(self, *relative_paths: str) -> None:
        for relative_path in relative_paths:
            path = (self.image_dir / relative_path).resolve()
            if path.is_relative_to(self.image_dir):
                self._remove_owned([path])

    def _exclusive_write(self, path: Path, content: bytes) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError as exc:
            raise ArtifactAlreadyExistsError(f"Image artifact already exists: {path.name}") from exc
        try:
            stat = os.fstat(descriptor)
            self._owned_artifacts[path] = (stat.st_dev, stat.st_ino)
            artifact = os.fdopen(descriptor, "wb")
            descriptor = -1
            with artifact:
                artifact.write(content)
        except Exception:
            if descriptor >= 0:
                os.close(descriptor)
            self._remove_owned([path])
            raise

    def _remove_owned(self, paths: list[Path]) -> None:
        for path in paths:
            identity = self._owned_artifacts.pop(path, None)
            if identity is None:
                continue
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            if (stat.st_dev, stat.st_ino) == identity:
                path.unlink(missing_ok=True)
