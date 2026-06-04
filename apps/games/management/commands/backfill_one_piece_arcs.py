from django.core.management.base import BaseCommand, CommandError

from apps.games.models import Game
from apps.games.services.proximity.arc_backfill import backfill_arc_catalog


class Command(BaseCommand):
    help = "Construye ArcCatalog y arco_slug en GameItem desde datos de One Piece."

    def add_arguments(self, parser):
        parser.add_argument(
            "--game-slug",
            default="one-piece",
            help="Slug del juego One Piece",
        )

    def handle(self, *args, **options):
        game = Game.objects.filter(slug=options["game_slug"]).first()
        if not game:
            raise CommandError(f"No existe el juego '{options['game_slug']}'.")

        catalog_count, updated_items = backfill_arc_catalog(game)
        self.stdout.write(
            self.style.SUCCESS(
                f"Arcos en catálogo: {catalog_count}. Ítems actualizados: {updated_items}."
            )
        )
