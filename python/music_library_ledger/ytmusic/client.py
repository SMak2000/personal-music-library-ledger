import json
import os
from pathlib import Path

from ytmusicapi import YTMusic


def get_ytmusic_client() -> YTMusic:
    headers_path = os.environ["YTMUSIC_HEADERS_PATH"]
    path = Path(headers_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(
            f"YTMUSIC_HEADERS_PATH not found: {path}. Provide headers json from ytmusicapi."
        )

    try:
        with path.open("r", encoding="utf-8") as handle:
            headers = json.load(handle)
        return YTMusic(headers)
    except json.JSONDecodeError:
        return YTMusic(str(path))
