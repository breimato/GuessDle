from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Avg, Count, ExpressionWrapper, FloatField, Q
from django.db.models.functions import Cast

from apps.accounts.models import GameElo
from apps.accounts.services.player_stats_service import PlayerStatsService
from apps.games.models import PlaySession, ScoringRule


class ScoreService:
    def __init__(self, user, game, mode=None):
        self.user = user
        self.game = game
        self.mode = mode
        lookup = {"user": user, "game": game}
        if mode:
            lookup["mode"] = mode
        else:
            lookup["mode__isnull"] = True
        self.score_obj, _ = GameElo.objects.get_or_create(**lookup, defaults={"elo": 0})

    def add_points_for_attempts(self, attempts_count: int) -> int:
        points = self._calculate_points_for_attempts(attempts_count)
        self.score_obj.elo += points
        self.score_obj.partidas += 1
        self.score_obj.save(update_fields=("elo", "partidas"))
        return points

    def calculate_user_average_attempts(self) -> float | None:
        return PlayerStatsService.calculate_user_average_attempts(
            self.user, self.game, mode=self.mode
        )

    def calculate_global_average_of_averages(self, exclude_user=True) -> float | None:
        play_sessions = PlaySession.objects.filter(game=self.game)
        if self.mode:
            play_sessions = play_sessions.filter(mode=self.mode)
        else:
            play_sessions = play_sessions.filter(mode__isnull=True)
        if exclude_user:
            play_sessions = play_sessions.exclude(user=self.user)

        user_averages = (
            play_sessions.values("user")
            .annotate(
                total_attempts=Count("attempts"),
                completed_sessions=Count(
                    "id", filter=Q(attempts__is_correct=True), distinct=True
                ),
            )
            .filter(completed_sessions__gt=0)
            .annotate(
                user_avg=ExpressionWrapper(
                    Cast("total_attempts", FloatField())
                    / Cast("completed_sessions", FloatField()),
                    output_field=FloatField(),
                )
            )
        )
        global_average_result = user_averages.aggregate(avg_of_avgs=Avg("user_avg"))
        return global_average_result["avg_of_avgs"]

    def _calculate_points_for_attempts(self, attempts_count: int) -> int:
        scoring_rule = (
            ScoringRule.objects.filter(game=self.game, attempt_no=attempts_count).first()
            or ScoringRule.objects.filter(game__isnull=True, attempt_no=attempts_count).first()
        )
        if scoring_rule:
            return scoring_rule.points

        decrement = getattr(settings, "SCORING_FALLBACK", {}).get("decrement", 10)
        floor = getattr(settings, "SCORING_FALLBACK", {}).get("floor", 0)
        fallback_points = 50 - decrement * (attempts_count - 3)
        return max(floor, fallback_points)
