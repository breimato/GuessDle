from django.core.management.base import BaseCommand, CommandError

from apps.games.models import Game
from apps.games.services.catalog.one_piece_episode_utils import enrich_one_piece_episode


class Command(BaseCommand):
    help = "Rellena el campo episodio en GameItem de One Piece (desde capítulo + mapa)."

    def add_arguments(self, parser):
        parser.add_argument("--game-slug", default="one-piece")

    def handle(self, *args, **options):
        game = Game.objects.filter(slug=options["game_slug"]).first()
        if not game:
            raise CommandError(f"No existe el juego '{options['game_slug']}'.")

        updated = 0
        for item in game.items.filter(deleted=False):
            data = enrich_one_piece_episode(dict(item.data or {}))
            data.pop("generacion", None)
            if data == item.data:
                continue
            item.data = data
            item.save(update_fields=["data"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Ítems actualizados: {updated}."))
