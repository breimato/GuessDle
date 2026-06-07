from django.templatetags.static import static

from apps.games.models import Game, GameItem, GameMode
from apps.games.services.catalog.generation_utils import GENERATION_MAX_IDS
from apps.games.services.proximity.filter_service import ProximityFilterService
from apps.games.services.proximity.game_config import (
    ONE_PIECE_MEDIA_ANIME,
    POKEMON_REGIONS,
    one_piece_value_unit,
    proximity_game_kind,
)
from apps.games.services.proximity.pool_service import ProximityPoolService

QUAGSIRE_NATIONAL_ID = 195


class ProximityPickerCatalogService:
    def __init__(self, game: Game, mode: GameMode, filter_config: dict):
        self.game = game
        self.mode = mode
        self.filter_config = filter_config
        self.pool = ProximityPoolService(game, mode, filter_config)
        self.resolver = self.pool.resolver

    def build(self) -> dict | None:
        kind = proximity_game_kind(self.game)
        if kind == "pokemon":
            return self._pokemon_catalog()
        if kind == "lol":
            return self._lol_catalog()
        if kind == "one_piece":
            return self._one_piece_catalog()
        return None

    def _resolve_quagsire_silhouette_url(self) -> str | None:
        quagsire = (
            GameItem.objects.filter(
                game=self.game,
                deleted=False,
                data__id=QUAGSIRE_NATIONAL_ID,
            )
            .first()
        )
        if quagsire is None:
            quagsire = (
                GameItem.objects.filter(game=self.game, deleted=False, name__iexact="Quagsire")
                .first()
            )
        if quagsire:
            return quagsire.get_image_url()
        return static("images/default-character.png")

    def _generation_id_bounds(self, generation: int) -> tuple[int, int]:
        generation = int(generation)
        if generation <= 1:
            return 1, GENERATION_MAX_IDS[0]
        index = min(generation, len(GENERATION_MAX_IDS)) - 1
        return GENERATION_MAX_IDS[index - 1] + 1, GENERATION_MAX_IDS[index]

    def _pokemon_catalog(self) -> dict:
        generations = sorted(
            int(generation)
            for generation in (self.filter_config.get("generations") or [1, 2, 3])
        )
        catalog_generations = []
        for generation in generations:
            min_id, max_id = self._generation_id_bounds(generation)
            pokemon = [
                {"id": national_id, "number": national_id}
                for national_id in range(min_id, max_id + 1)
            ]
            region = POKEMON_REGIONS.get(generation, f"Generación {generation}")
            catalog_generations.append(
                {
                    "id": generation,
                    "region": region,
                    "kicker": f"Gen {generation}",
                    "pokemon": pokemon,
                }
            )

        return {
            "silhouette_url": self._resolve_quagsire_silhouette_url(),
            "generations": catalog_generations,
        }

    def _lol_catalog(self) -> dict:
        years = sorted(set(self.pool._lol_selected_years()))
        icon_url = self.game.icon_image.url if self.game.icon_image else None

        return {
            "icon_url": icon_url,
            "years": [{"year": year} for year in years],
        }

    def _one_piece_catalog(self) -> dict:
        media = self.filter_config.get("media")
        value_unit = one_piece_value_unit(media)
        is_anime = media == ONE_PIECE_MEDIA_ANIME
        label_prefix = "Episodio" if is_anime else "Capítulo"
        arc_labels = {
            row["slug"]: row["label"] for row in ProximityFilterService(self.game).arc_choices()
        }
        values_by_arc: dict[str, list[int]] = {}

        for item in self.pool.item_queryset():
            answer = self.resolver.resolve_item(item)
            if answer is None:
                continue
            arc_slug = ProximityPoolService.arc_slug_from_item_data(item.data or {}) or "other"
            values_by_arc.setdefault(arc_slug, []).append(int(answer))

        for prompt in self.pool.prompt_queryset().iterator():
            answer = self.resolver.resolve_prompt(prompt)
            if answer is None:
                continue
            guess_value = int(answer)
            for arc_slug in prompt.arcs or []:
                values_by_arc.setdefault(arc_slug, []).append(guess_value)

        arc_choices = ProximityFilterService(self.game).arc_choices()
        ordered_slugs = [row["slug"] for row in arc_choices]
        seen_slugs: set[str] = set()
        groups = []

        def append_group(arc_slug: str) -> None:
            values = values_by_arc.get(arc_slug)
            if not values:
                return
            min_value = min(values)
            max_value = max(values)
            entries = [
                {
                    "name": f"{label_prefix} {number}",
                    "guess_value": number,
                    "image_url": None,
                }
                for number in range(min_value, max_value + 1)
            ]
            groups.append(
                {
                    "id": arc_slug,
                    "label": arc_labels.get(arc_slug, arc_slug.replace("_", " ").title()),
                    "entries": entries,
                }
            )
            seen_slugs.add(arc_slug)

        for arc_slug in ordered_slugs:
            append_group(arc_slug)

        remaining_slugs = sorted(
            slug for slug in values_by_arc if slug not in seen_slugs
        )
        for arc_slug in remaining_slugs:
            append_group(arc_slug)

        return {
            "groups": groups,
            "value_unit": value_unit,
            "media": media,
        }
