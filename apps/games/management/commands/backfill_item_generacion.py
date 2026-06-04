from django.core.management.base import BaseCommand

from apps.games.models import Game, GameItem
from apps.games.services.catalog.generation_utils import enrich_item_data


class Command(BaseCommand):
    help = "Rellena data.generacion en GameItem a partir de data.id."

    def add_arguments(self, parser):
        parser.add_argument("--slug", default="pokemon")

    def handle(self, *args, **options):
        game = Game.objects.filter(slug=options["slug"]).first()
        if not game:
            self.stderr.write(f"No existe el juego '{options['slug']}'.")
            return

        updated = 0
        for item in GameItem.objects.filter(game=game, deleted=False):
            enriched = enrich_item_data(item.data or {}, game=game)
            if enriched != item.data:
                item.data = enriched
                item.save(update_fields=["data"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"{updated} ítems actualizados en {game.name}."))
