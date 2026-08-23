import io
import os
import zipfile

MAX_FILES = 500
MAX_FILE_BYTES = 2_000_000
MAX_ZIP_BYTES = 20_000_000  # 20 MB max upload
MAX_TOTAL_UNCOMPRESSED = 30_000_000  # prevent zip bomb


def _is_safe_path(filename: str) -> bool:
    """Prevent Zip Slip / path traversal even though we never write to disk."""
    if filename.startswith("/") or filename.startswith("\\"):
        return False
    # normalize and check for parent traversal
    normalized = os.path.normpath(filename)
    if normalized.startswith("..") or ".." in normalized.split(os.sep):
        return False
    return True


def extract_zip_python_files(data: bytes) -> dict[str, str]:
    """Return {path: source} for every .py inside the archive. Never writes to disk."""
    if len(data) > MAX_ZIP_BYTES:
        return {}
    if len(data) == 0:
        return {}
    files: dict[str, str] = {}
    total_uncompressed = 0
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return files
    with archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.endswith(".py"):
                continue
            if "__MACOSX" in info.filename:
                continue
            if not _is_safe_path(info.filename):
                continue
            if info.file_size > MAX_FILE_BYTES:
                continue
            total_uncompressed += info.file_size
            if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
                break
            if len(files) >= MAX_FILES:
                break
            try:
                code = archive.read(info).decode("utf-8", errors="replace")
            except Exception:
                continue
            files[info.filename] = code
    return files