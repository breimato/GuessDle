import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from apps.games.models import Game, GameItem

LOL_JSON_PATH = os.path.join(settings.BASE_DIR, "data", "league-of-legends.json")


class Command(BaseCommand):
    help = "Sync LoLdle champions data into the database"

    def handle(self, *args, **kwargs):
        if not os.path.exists(LOL_JSON_PATH):
            self.stderr.write(f"❌ JSON file not found at {LOL_JSON_PATH}")
            return

        with open(LOL_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        try:
            game = Game.objects.get(slug="league-of-legends")
        except Game.DoesNotExist:
            self.stderr.write("❌ Game with slug 'league-of-legends' not found. Please create it from the admin first.")
            return

        field_mapping = game.field_mapping or {}
        defaults = game.defaults or {}

        count = 0

        for champ in data:
            name = champ.get("name")
            if not name:
                continue

            structured_data = {
                label: champ.get(field, defaults.get(field))
                for field, label in field_mapping.items()
            }

            GameItem.objects.update_or_create(
                game=game,
                name=name,
                defaults={
                    "data": structured_data
                }
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {count} champions synced into game '{game.name}'"))
