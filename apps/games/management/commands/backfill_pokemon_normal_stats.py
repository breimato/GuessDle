from django.core.management.base import BaseCommand

from apps.games.services.pokemon_normal_backfill import backfill_pokemon_normal_mode


class Command(BaseCommand):
    help = "Asigna las estadísticas históricas de Pokémon al modo Normal."

    def add_arguments(self, parser):
        parser.add_argument("--slug", default="pokemon")
        parser.add_argument("--mode", default="normal")

    def handle(self, *args, **options):
        summary = backfill_pokemon_normal_mode(
            game_slug=options["slug"],
            mode_slug=options["mode"],
        )

        if not summary.get("game_found"):
            self.stderr.write(f"No existe el juego '{options['slug']}'.")
            return

        if not summary.get("mode_found"):
            self.stderr.write(
                f"No existe el modo '{options['mode']}' para '{options['slug']}'."
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Backfill completado: "
                f"GameElo fusionados={summary['game_elo_merged']}, "
                f"GameElo actualizados={summary['game_elo_updated']}, "
                f"PlaySession={summary['play_sessions']}, "
                f"DailyTarget actualizados={summary['daily_targets_updated']}, "
                f"DailyTarget eliminados={summary['daily_targets_removed']}, "
                f"ExtraDailyPlay={summary['extra_daily_plays']}, "
                f"Challenge={summary['challenges']}."
            )
        )
