from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from apps.games.models import Game, DailyTarget, GameItem
import secrets

class Command(BaseCommand):
    help = "Genera los DailyTarget para todos los días del año (normal + equipo) para todos los juegos activos."

    def create_target_for_date(self, game, date, is_team):
        exists = DailyTarget.objects.filter(game=game, date=date, is_team=is_team).exists()
        tipo = "Equipo" if is_team else "Normal"

        if exists:
            self.stdout.write(f"✔️ Ya existe target ({tipo}) para {game.name} ({date})")
            return False

        items = list(GameItem.objects.filter(game=game, deleted=False))
        if not items:
            self.stdout.write(f"⚠️ {game.name} no tiene ítems para generar target ({tipo}) ({date})")
            return False

        item = secrets.choice(items)
        DailyTarget.objects.create(
            game=game,
            date=date,
            is_team=is_team,
            target=item
        )
        self.stdout.write(f"🆕 Target creado ({tipo}) para {game.name} ({date}) → {item.name}")
        return True

    def handle(self, *args, **options):
        today = timezone.localtime().date()
        end_of_year = date(today.year, 12, 31)
        total_created = 0

        for game in Game.objects.filter(active=True):
            for is_team in [False, True]:
                current_day = today
                while current_day <= end_of_year:
                    if self.create_target_for_date(game, current_day, is_team):
                        total_created += 1
                    current_day += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(f"Total DailyTargets creados: {total_created}"))
