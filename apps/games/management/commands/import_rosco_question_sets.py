import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.games.constants import LEAGUE_GAME_SLUG
from apps.games.models import Game, RoscoQuestion
from apps.games.services.rosco.question_import_validator import RoscoQuestionImportError
from apps.games.services.rosco.rosco_question_importer import import_rosco_questions


class Command(BaseCommand):
    help = "Importa múltiples sets de preguntas Pasapalabra desde un directorio JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--directory",
            default="data/lol/rosco_sets",
            help="Directorio con archivos set_XXX.json",
        )
        parser.add_argument(
            "--game-slug",
            default=LEAGUE_GAME_SLUG,
            help="Slug del juego destino",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Elimina preguntas existentes del juego antes de importar",
        )

    def handle(self, *args, **options):
        game = Game.objects.filter(slug=options["game_slug"]).first()
        if not game:
            raise CommandError(f"No existe el juego con slug '{options['game_slug']}'.")

        directory = Path(options["directory"])
        if not directory.is_dir():
            raise CommandError(f"No se encontró el directorio {directory}.")

        json_files = sorted(directory.glob("set_*.json"))
        if not json_files:
            raise CommandError(f"No hay archivos set_*.json en {directory}.")

        if options["replace"]:
            deleted, _ = RoscoQuestion.objects.filter(game=game).delete()
            self.stdout.write(self.style.WARNING(f"Eliminadas {deleted} preguntas previas."))

        total_created = 0
        for path in json_files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            try:
                created = import_rosco_questions(game, payload, source=str(path))
            except RoscoQuestionImportError as error:
                raise CommandError(str(error)) from error
            total_created += created
            self.stdout.write(f"  {path.name}: {created} preguntas")

        self.stdout.write(
            self.style.SUCCESS(
                f"Importadas {total_created} preguntas desde {len(json_files)} sets para {game.slug}."
            )
        )
