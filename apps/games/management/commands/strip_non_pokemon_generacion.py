from django.core.management.base import BaseCommand

from apps.games.constants import is_pokemon_game
from apps.games.models import GameItem


class Command(BaseCommand):
    help = "Elimina data.generacion de ítems de juegos que no sean Pokémon."

    def handle(self, *args, **options):
        updated = 0
        for item in GameItem.objects.filter(deleted=False).select_related("game"):
            if is_pokemon_game(item.game.slug):
                continue
            data = dict(item.data or {})
            if "generacion" not in data:
                continue
            data.pop("generacion", None)
            item.data = data
            item.save(update_fields=["data"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Ítems limpiados: {updated}."))
