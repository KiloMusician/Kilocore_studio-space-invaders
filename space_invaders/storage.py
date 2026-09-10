from __future__ import annotations

import json
import os
from pathlib import Path


def default_data_path() -> Path:
    override = os.environ.get("KILO_SHMUP_DATA") or os.environ.get("SPACE_INVADERS_DATA")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".kilocore" / "space-invaders" / "data.json"


def load_high_score(path: str | Path | None = None, *, bundled_default: int = 0) -> int:
    target = Path(path) if path is not None else default_data_path()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        value = int(payload.get("HighScore", bundled_default))
        return max(0, value)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return max(0, bundled_default)


def save_high_score(score: int, path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else default_data_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(
        json.dumps({"HighScore": max(0, int(score))}, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(target)
    return target
