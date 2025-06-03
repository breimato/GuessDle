import json
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
    help = "Sincroniza los GameItems desde una o dos APIs, según lo definido en admin"

    def add_arguments(self, parser):
        parser.add_argument('slug', type=str, help="Slug del juego (ej: pokemon)")

    def handle(self, *args, **options):
        slug = options['slug']
        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            raise CommandError(f"No existe un juego con el slug '{slug}'")

        if not game.data_source_url:
            raise CommandError("Este juego no tiene definida una URL para sincronizar datos.")

        # 🔍 Soporta tanto string como lista de 2 URLs
        try:
            urls = json.loads(game.data_source_url)
            if not isinstance(urls, list) or len(urls) != 2:
                raise ValueError
            list_url, detail_key = urls
        except (json.JSONDecodeError, ValueError, TypeError):
            urls = None
            list_url = game.data_source_url

        self.stdout.write(self.style.NOTICE(f"🔄 Sincronizando '{game.name}' desde {list_url}"))

        try:
            response = requests.get(list_url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise CommandError(f"Error al obtener datos de la URL: {e}")

        # Si es doble API: usamos la clave para entrar a la lista, y llamamos a cada URL
        if urls:
            items = data.get(detail_key, [])
            raw_items = []
            for item in items:
                url = item.get("url")
                if not url:
                    continue
                try:
                    detail_resp = requests.get(url)
                    detail_resp.raise_for_status()
                    raw_items.append(detail_resp.json())
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f"⚠️ Error con {url}: {e}"))
        else:
            # Es un solo JSON plano o una lista directamente
            raw_items = data if isinstance(data, list) else data.get("results", [])

        created_count = 0
        updated_count = 0

        for raw in raw_items:
            parsed = {}
            for local_field, remote_field in game.field_mapping.items():
                value = deep_get(raw, remote_field, game.defaults.get(local_field))
                parsed[local_field] = value

            original_id = deep_get(raw, 'id') 
            if original_id is not None:
                parsed['id'] = original_id

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
