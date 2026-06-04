from apps.games.services.proximity.chapter_episode_lookup import episode_for_chapter


def episode_for_character_data(data: dict) -> int | None:
    if not data:
        return None
    raw = data.get("episodio")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    legacy = data.get("episodio de primera aparición")
    if legacy is not None:
        try:
            return int(legacy)
        except (TypeError, ValueError):
            return None
    chapter = data.get("capítulo") or data.get("capitulo")
    if chapter is None:
        return None
    return episode_for_chapter(int(chapter))


def enrich_one_piece_episode(data: dict) -> dict:
    enriched = dict(data)
    chapter = enriched.get("capítulo") or enriched.get("capitulo")
    if chapter is None:
        return enriched
    episode = episode_for_character_data(enriched)
    if episode is not None:
        enriched["episodio"] = episode
    enriched.pop("episodio de primera aparición", None)
    return enriched
