"""Orden canónico de arcos (manga), alineado con One Piece Wiki / Fandom."""

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parents[4] / "data" / "one_piece" / "arc_order.json"


def normalize_arc_slug(slug: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(slug or "").strip().lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


@lru_cache(maxsize=1)
def canonical_arc_slugs() -> tuple[str, ...]:
    if not _DATA_PATH.is_file():
        return ()
    payload = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    return tuple(normalize_arc_slug(item) for item in payload if str(item).strip())


def arc_sort_index(slug: str) -> int:
    order = canonical_arc_slugs()
    normalized = normalize_arc_slug(slug)
    try:
        return order.index(normalized)
    except ValueError:
        return len(order) + 1


def sort_arc_records(records: list[dict]) -> list[dict]:
    normalized_rows = [
        {**row, "slug": normalize_arc_slug(str(row.get("slug", "")))} for row in records
    ]
    return sorted(
        normalized_rows,
        key=lambda row: (arc_sort_index(row["slug"]), str(row.get("label", "")).lower()),
    )


def dedupe_arc_records(records: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for row in records:
        slug = normalize_arc_slug(str(row.get("slug", "")))
        if not slug:
            continue
        if slug not in merged:
            merged[slug] = {**row, "slug": slug}
    return list(merged.values())
