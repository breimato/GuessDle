GENERATION_MAX_IDS = (151, 251, 386, 493, 649, 721, 809, 905, 1025)


def generation_from_national_id(national_id: int) -> int:
    if national_id <= 0:
        return 1
    for index, upper in enumerate(GENERATION_MAX_IDS, start=1):
        if national_id <= upper:
            return index
    return len(GENERATION_MAX_IDS)


def enrich_item_data(data: dict) -> dict:
    enriched = dict(data)
    item_id = enriched.get("id")
    if item_id is not None and "generacion" not in enriched:
        enriched["generacion"] = generation_from_national_id(int(item_id))
    return enriched
