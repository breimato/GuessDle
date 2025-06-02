from datetime import timedelta
from django.utils import timezone
from apps.games.models import DailyTarget, GameResult, PlaySession, PlaySessionType, GameAttempt
from apps.games.models import GameItem
import secrets


class TargetService:
    def __init__(self, game, user):
        self.game = game
        self.user = user
        self.is_team = getattr(getattr(user, "profile", None), "is_team_account", False)

    def get_target_for_today(self):
        today = timezone.localdate()
        return DailyTarget.objects.filter(
            game=self.game,
            date=today,
            is_team=self.is_team
        ).select_related("target").first()

    def get_yesterday_target(self, today_date=None):
        today_date = today_date or timezone.localdate()
        yesterday = today_date - timedelta(days=1)
        return DailyTarget.objects.filter(
            game=self.game,
            date=yesterday,
            is_team=self.is_team
        ).select_related("target").first()

    def get_current_target(self):
        return DailyTarget.get_current(self.game, self.user)
    
    def get_random_item(self):
        items = list(GameItem.objects.filter(game=self.game))
        if not items:
            raise ValueError("No hay ítems disponibles para este juego.")
        return secrets.choice(items)

    def is_daily_resolved(self):
        today = timezone.localdate()
        daily = DailyTarget.objects.filter(
            game=self.game,
            date=today,
            is_team=self.is_team
        ).select_related("target").first()

        if not daily:
            return False

        # 1️⃣ Buscar la sesión DAILY de hoy para este usuario
        session = PlaySession.objects.filter(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=daily.id
        ).first()

        if not session:
            return False

        # 2️⃣ Verificar si hay al menos un intento correcto en esa sesión
        return GameAttempt.objects.filter(
            session=session,
            is_correct=True
        ).exists()
