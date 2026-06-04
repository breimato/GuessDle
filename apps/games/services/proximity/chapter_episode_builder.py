"""Build chapter -> anime episode map from ListFist episode-to-chapter table."""
from __future__ import annotations

import json
import re
import urllib.request

from apps.games.services.proximity.chapter_episode_lookup import MAP_PATH

LISTFIST_URL = "https://listfist.com/list-of-one-piece-episode-to-chapter-conversion"

MANUAL_OVERRIDES: dict[int, int] = {
    0: 0,
    134: 81,
    574: 483,
    1126: 1156,
    1127: 1157,
    1128: 1158,
    1129: 1159,
    1130: 1160,
    1131: 1161,
    1132: 1162,
    1133: 1163,
}


def fetch_listfist_html() -> str:
    request = urllib.request.Request(LISTFIST_URL, headers={"User-Agent": "GuessDle/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8", "replace")


def parse_episode_chapters(html: str) -> dict[int, list[int]]:
    episode_chapters: dict[int, list[int]] = {}
    row_pattern = re.compile(
        r"<tr[^>]*>\s*<td[^>]*>\s*(\d+)\s*</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>",
        re.S | re.I,
    )
    for episode_str, chapters_cell in row_pattern.findall(html):
        episode = int(episode_str)
        if re.search(r"\bfiller\b", chapters_cell, re.I):
            continue
        chapters = [int(num) for num in re.findall(r"\b(\d{1,4})\b", chapters_cell)]
        if chapters:
            episode_chapters[episode] = chapters
    return episode_chapters


def invert_to_chapter_episode(episode_chapters: dict[int, list[int]]) -> dict[int, int]:
    chapter_to_episode: dict[int, int] = {}
    for episode in sorted(episode_chapters):
        for chapter in episode_chapters[episode]:
            chapter_to_episode.setdefault(chapter, episode)
    return chapter_to_episode


def load_existing_map() -> dict[int, int]:
    if not MAP_PATH.exists():
        return {}
    raw = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    return {int(key): int(value) for key, value in raw.items()}


def merge_maps(*maps: dict[int, int]) -> dict[int, int]:
    merged: dict[int, int] = {}
    for source in maps:
        merged.update(source)
    for chapter, episode in MANUAL_OVERRIDES.items():
        merged[chapter] = episode
    return dict(sorted(merged.items()))


def write_map(chapter_to_episode: dict[int, int]) -> int:
    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {str(chapter): episode for chapter, episode in chapter_to_episode.items()}
    MAP_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return len(chapter_to_episode)


def build_chapter_episode_map() -> tuple[int, int]:
    html = fetch_listfist_html()
    episode_chapters = parse_episode_chapters(html)
    from_listfist = invert_to_chapter_episode(episode_chapters)
    existing = load_existing_map()
    merged = merge_maps(existing, from_listfist)
    total = write_map(merged)
    return len(episode_chapters), total
