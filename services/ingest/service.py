from pathlib import Path


def validate_source(path: str) -> Path:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Source does not exist: {source}")
    if not source.is_file():
        raise ValueError(f"Source is not a file: {source}")
    return source
