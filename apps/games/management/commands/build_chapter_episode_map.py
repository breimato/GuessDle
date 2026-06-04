from django.core.management.base import BaseCommand

from apps.games.services.proximity.chapter_episode_builder import build_chapter_episode_map
from apps.games.services.proximity.chapter_episode_lookup import clear_chapter_episode_cache


class Command(BaseCommand):
    help = "Genera data/one_piece/chapter_episode_map.json desde ListFist + overrides."

    def handle(self, *args, **options):
        episodes, total = build_chapter_episode_map()
        clear_chapter_episode_cache()
        self.stdout.write(
            self.style.SUCCESS(
                f"Mapa actualizado: {total} capítulos ({episodes} episodios parseados)."
            )
        )
