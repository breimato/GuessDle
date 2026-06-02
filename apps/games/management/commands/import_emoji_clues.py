import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.games.constants import LEAGUE_GAME_SLUG
from apps.games.models import Game
from apps.games.services.emoji.clue_importer import import_emoji_clues
from apps.games.services.emoji.clue_validator import EmojiClueImportError


class Command(BaseCommand):
    help = "Importa sets de pistas emoji desde un archivo JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path",
            nargs="?",
            default="data/lol/emoji_clues.json",
            help="Ruta al archivo JSON de pistas emoji",
        )
        parser.add_argument(
            "--game-slug",
            default=LEAGUE_GAME_SLUG,
            help="Slug del juego destino",
        )

    def handle(self, *args, **options):
        game = Game.objects.filter(slug=options["game_slug"]).first()
        if not game:
            raise CommandError(f"No existe el juego con slug '{options['game_slug']}'.")

        path = Path(options["json_path"])
        if not path.exists():
            raise CommandError(f"No se encontró el archivo {path}.")

        payload = json.loads(path.read_text(encoding="utf-8"))
        try:
            upserted = import_emoji_clues(game, payload, source=str(path))
        except EmojiClueImportError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            self.style.SUCCESS(f"Importados {upserted} sets emoji para {game.slug}.")
        )
