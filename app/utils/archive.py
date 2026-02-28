import zipfile
from pathlib import Path


class ArchiveError(Exception):
    pass


def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target = destination / member
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ArchiveError(f"Invalid zip member path traversal detected: {member}")
        zf.extractall(destination)
