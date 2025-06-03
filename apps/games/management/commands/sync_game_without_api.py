import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.games.models import Game, GameItem


class Command(BaseCommand):
    help = "Sincroniza GameItems desde un JSON estático, usando el mapping y los defaults definidos en admin"

    def add_arguments(self, parser):
        parser.add_argument('slug', type=str, help="Slug del juego (ej: league-of-legends)")
        parser.add_argument('json_path', type=str, help="Ruta al archivo JSON con los datos")

    def handle(self, *args, **options):
        slug = options["slug"]
        json_path = options["json_path"]

        # Resuelve la ruta completa si es relativa
        full_path = os.path.abspath(os.path.join(settings.BASE_DIR, json_path))

        if not os.path.exists(full_path):
            raise CommandError(f"❌ No se encontró el archivo JSON en: {full_path}")

        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            raise CommandError(f"❌ No existe el juego con slug '{slug}'")

        with open(full_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                raise CommandError("❌ El archivo JSON no es válido")

        field_mapping = game.field_mapping or {}
        defaults = game.defaults or {}

        count = 0
        for entry in data:
            name = entry.get("name") or entry.get("nombre") or entry.get("Nombre")
            if not name:
                continue

            structured_data = {
                local_field: entry.get(remote_field, defaults.get(local_field))
                for local_field, remote_field in field_mapping.items()
            }

            original_id = entry.get('id')
            if original_id is not None:
                structured_data['id'] = original_id

            GameItem.objects.update_or_create(
                game=game,
                name=name,
                defaults={"data": structured_data}
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ {count} items sincronizados en el juego '{game.name}'"
        ))
