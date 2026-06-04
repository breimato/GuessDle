from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.games.models import DailyTarget, Game, GameModePlayType
from apps.games.services.catalog.item_pool_service import ItemPoolService


class Command(BaseCommand):
    help = "Genera DailyTarget para el resto del año (normal + equipo, con modos si existen)."

    def create_target_for_date(self, game, target_date, is_team, mode):
        filters = {"game": game, "date": target_date, "is_team": is_team}
        if mode is None:
            filters["mode__isnull"] = True
        else:
            filters["mode"] = mode

        if DailyTarget.objects.filter(**filters).exists():
            tipo = "Equipo" if is_team else "Normal"
            mode_label = mode.label if mode else ""
            self.stdout.write(
                f"Ya existe target ({tipo}{f' {mode_label}' if mode_label else ''}) "
                f"para {game.name} ({target_date})"
            )
            return False

        item = (
            ItemPoolService(game, mode).pick_random_with_emoji_clues()
            if mode and mode.is_emoji
            else ItemPoolService(game, mode).pick_random()
        )
        if not item:
            self.stdout.write(
                f"{game.name} sin ítems en pool "
                f"({mode.slug if mode else 'sin modo'}) ({target_date})"
            )
            return False

        DailyTarget.objects.create(
            game=game,
            date=target_date,
            is_team=is_team,
            mode=mode,
            target=item,
        )
        tipo = "Equipo" if is_team else "Normal"
        mode_label = f" [{mode.label}]" if mode else ""
        self.stdout.write(
            f"Target creado ({tipo}{mode_label}) {game.name} ({target_date}) -> {item.name}"
        )
        return True

    def modes_for_game(self, game):
        modes = list(
            game.modes.filter(
                active=True,
                play_type__in=[GameModePlayType.WORDLE, GameModePlayType.EMOJI],
            )
            .order_by("sort_order", "slug")
        )
        return modes if modes else [None]

    def handle(self, *args, **options):
        today = timezone.localtime().date()
        end_of_year = date(today.year, 12, 31)
        total_created = 0

        for game in Game.objects.filter(active=True):
            for is_team in (False, True):
                current_day = today
                while current_day <= end_of_year:
                    for mode in self.modes_for_game(game):
                        if self.create_target_for_date(game, current_day, is_team, mode):
                            total_created += 1
                    current_day += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(f"Total DailyTargets creados: {total_created}"))
