from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.games.models import Game, DailyTarget, GameItem


class Command(BaseCommand):
    help = "Genera los DailyTarget de hoy y mañana para todos los juegos activos."

    def create_target_for_date(self, game, target_date):
        existing = DailyTarget.objects.filter(game=game, date=target_date).exists()
        if existing:
            self.stdout.write(f"✔️ Ya existe target para {game.name} ({target_date})")
            return False

        target_item = GameItem.objects.filter(game=game).order_by("?").first()
        if not target_item:
            self.stdout.write(f"⚠️ No hay ítems en {game.name} para generar el target.")
            return False

        DailyTarget.objects.create(game=game, date=target_date, target=target_item)
        self.stdout.write(f"🆕 Target creado para {game.name} ({target_date}) → {target_item.name}")
        return True

    def handle(self, *args, **options):
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)

        created_today = 0
        created_tomorrow = 0

        for game in Game.objects.filter(active=True):
            if self.create_target_for_date(game, today):
                created_today += 1
            if self.create_target_for_date(game, tomorrow):
                created_tomorrow += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Targets generados: hoy={created_today}, mañana={created_tomorrow}"
        ))
