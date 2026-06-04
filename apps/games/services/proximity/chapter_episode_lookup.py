"""Lookup table: manga chapter -> primary anime episode (One Piece Fandom wiki)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

MAP_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "one_piece" / "chapter_episode_map.json"
)


@lru_cache(maxsize=1)
def load_chapter_episode_map() -> dict[int, int]:
    if not MAP_PATH.exists():
        return {}
    raw = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    return {int(key): int(value) for key, value in raw.items()}


def episode_for_chapter(chapter: int) -> int | None:
    return load_chapter_episode_map().get(int(chapter))


def clear_chapter_episode_cache() -> None:
    load_chapter_episode_map.cache_clear()

