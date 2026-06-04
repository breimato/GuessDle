import hashlib
import json
import re

from django.core.exceptions import ValidationError

from apps.games.models import ArcCatalog, Game, GameItem
from apps.games.services.catalog.one_piece_arc_order import (
    dedupe_arc_records,
    normalize_arc_slug,
    sort_arc_records,
)
from apps.games.services.proximity.game_config import (
    ONE_PIECE_MEDIA_ANIME,
    ONE_PIECE_MEDIA_MANGA,
    default_filters_for_game,
    lol_release_year,
    proximity_game_kind,
)


def slugify_arc_label(label: str) -> str:
    normalized = re.sub(r"[^\w\s-]", "", label.lower())
    slug = re.sub(r"[-\s]+", "_", normalized).strip("_")
    return normalize_arc_slug(slug)


class ProximityFilterService:
    def __init__(self, game: Game):
        self.game = game

    def defaults(self) -> dict:
        config = default_filters_for_game(self.game)
        kind = proximity_game_kind(self.game)
        if kind == "one_piece" and not config.get("arcs"):
            config = {**config, "arcs": self.available_arc_slugs()}
        if kind == "lol" and not config.get("years"):
            config = {**config, "years": self.available_years()}
        return config

    def available_years(self) -> list[int]:
        years: set[int] = set()
        for item in GameItem.objects.filter(game=self.game, deleted=False):
            release_year = lol_release_year(item.data)
            if release_year is not None:
                years.add(release_year)
        return sorted(years)

    def _arc_queryset_values(self):
        return ArcCatalog.objects.filter(game=self.game, active=True).values("slug", "label", "sort_order")

    def _ordered_arc_records(self) -> list[dict]:
        records = list(self._arc_queryset_values())
        if proximity_game_kind(self.game) == "one_piece":
            return sort_arc_records(dedupe_arc_records(records))
        return sorted(records, key=lambda row: (row["sort_order"], str(row["label"]).lower()))

    def available_arc_slugs(self) -> list[str]:
        return [row["slug"] for row in self._ordered_arc_records()]

    def arc_choices(self) -> list[dict]:
        return [{"slug": row["slug"], "label": row["label"]} for row in self._ordered_arc_records()]

    def normalize(self, raw: dict | None) -> dict:
        base = self.defaults()
        if not raw:
            return base
        kind = proximity_game_kind(self.game)
        if kind == "pokemon":
            generations = raw.get("generations") or base["generations"]
            generations = sorted({int(g) for g in generations if 1 <= int(g) <= 9})
            if not generations:
                raise ValidationError("Selecciona al menos una generación.")
            return {"generations": generations}
        if kind == "lol":
            available = set(self.available_years())
            years = raw.get("years")
            if not years and (raw.get("year_min") is not None or raw.get("year_max") is not None):
                year_min = int(raw.get("year_min", min(available)))
                year_max = int(raw.get("year_max", max(available)))
                if year_min > year_max:
                    raise ValidationError("El año mínimo no puede ser mayor que el máximo.")
                years = [year for year in range(year_min, year_max + 1) if year in available]
            elif not years:
                years = base.get("years") or list(available)
            years = sorted({int(year) for year in years if int(year) in available})
            if not years:
                raise ValidationError("Selecciona al menos un año.")
            return {"years": years}
        if kind == "one_piece":
            available = set(self.available_arc_slugs())
            arcs = raw.get("arcs") or base.get("arcs") or list(available)
            arcs = [normalize_arc_slug(slug) for slug in arcs]
            arcs = [slug for slug in arcs if slug in available]
            if not arcs:
                raise ValidationError("Selecciona al menos un arco.")
            media = str(raw.get("media") or base.get("media") or ONE_PIECE_MEDIA_MANGA).strip().lower()
            if media not in {ONE_PIECE_MEDIA_MANGA, ONE_PIECE_MEDIA_ANIME}:
                raise ValidationError("Selecciona manga o anime.")
            return {"arcs": sorted(arcs), "media": media}
        return base

    def config_hash(self, config: dict) -> str:
        payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def filter_locked(self, session) -> bool:
        return (
            session.proximity_completed
            or session.proximity_timed_out
            or session.proximity_attempts.exists()
        )
