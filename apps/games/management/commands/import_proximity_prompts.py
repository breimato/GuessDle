import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.games.models import Game
from apps.games.services.proximity.prompt_importer import (
    ProximityPromptImportError,
    import_proximity_prompts,
)


class Command(BaseCommand):
    help = "Importa pistas de eventos para el modo proximidad (One Piece)."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path",
            nargs="?",
            default="data/one_piece/proximity_prompts.json",
            help="Ruta al JSON de eventos",
        )
        parser.add_argument(
            "--game-slug",
            default="one-piece",
            help="Slug del juego destino",
        )

    def handle(self, *args, **options):
        game = Game.objects.filter(slug=options["game_slug"]).first()
        if not game:
            raise CommandError(f"No existe el juego '{options['game_slug']}'.")

        path = Path(options["json_path"])
        if not path.exists():
            raise CommandError(f"No se encontró {path}.")

        payload = json.loads(path.read_text(encoding="utf-8"))
        try:
            count = import_proximity_prompts(game, payload, source=str(path))
        except ProximityPromptImportError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(self.style.SUCCESS(f"Importados {count} prompts para {game.slug}."))
