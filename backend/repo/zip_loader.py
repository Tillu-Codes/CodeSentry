import io
import zipfile

MAX_FILES = 500
MAX_FILE_BYTES = 2_000_000


def extract_zip_python_files(data: bytes) -> dict[str, str]:
    """Return {path: source} for every .py inside the archive. Never writes to disk."""
    files: dict[str, str] = {}
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
            if info.file_size > MAX_FILE_BYTES:
                continue
            if len(files) >= MAX_FILES:
                break
            code = archive.read(info).decode("utf-8", errors="replace")
            files[info.filename] = code
    return files