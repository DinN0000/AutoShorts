from pathlib import Path

DATA_DIR = Path("data")

DIRS = {
    "raw": DATA_DIR / "raw",
    "validated": DATA_DIR / "validated",
    "edited": DATA_DIR / "edited",
    "localized": DATA_DIR / "localized",
    "final": DATA_DIR / "final",
    "uploads": DATA_DIR / "uploads",
}


def ensure_dirs() -> None:
    for d in DIRS.values():
        d.mkdir(parents=True, exist_ok=True)


def video_dir(stage: str, video_id: str, date: str | None = None) -> Path:
    base = DIRS[stage]
    if date:
        base = base / date
    path = base / video_id
    path.mkdir(parents=True, exist_ok=True)
    return path
