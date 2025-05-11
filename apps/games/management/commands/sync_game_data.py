import requests
from django.core.management.base import BaseCommand, CommandError
from apps.games.models import Game, GameItem


def deep_get(d, path, default=None):
    """Permite acceder a campos anidados como 'fruit.name' o 'crew.roman_name'."""
    keys = path.split(".")
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
        else:
            return default
    return d if d is not None else default


class Command(BaseCommand):
    help = "Sincroniza los GameItems desde la API del juego usando el mapeo definido en admin"

    def add_arguments(self, parser):
        parser.add_argument('slug', type=str, help="Slug del juego (ej: one-piece)")

    def handle(self, *args, **options):
        slug = options['slug']
        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            raise CommandError(f"No existe un juego con el slug '{slug}'")

        if not game.data_source_url:
            raise CommandError("Este juego no tiene definida una URL de API para sincronizar datos.")

        self.stdout.write(self.style.NOTICE(f"🔄 Sincronizando '{game.name}' desde {game.data_source_url}"))

        try:
            response = requests.get(game.data_source_url)
            response.raise_for_status()
            raw_items = response.json()
        except Exception as e:
            raise CommandError(f"Error al conectar con la API: {e}")

        created_count = 0
        updated_count = 0

        for raw in raw_items:
            parsed = {}
            for local_field, remote_field in game.field_mapping.items():
                value = deep_get(raw, remote_field, game.defaults.get(local_field))
                parsed[local_field] = value

            name = parsed.get("nombre") or parsed.get("name") or raw.get("name")
            if not name:
                continue

            item, created = GameItem.objects.update_or_create(
                game=game,
                name=name,
                defaults={'data': parsed}
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Sincronización completada: {created_count} creados, {updated_count} actualizados."
        ))
