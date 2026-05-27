from django.conf import settings

from apps.accounts.models import GameElo
from apps.accounts.services.player_stats_service import PlayerStatsService
from apps.games.models import ScoringRule


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
        user_averages = PlayerStatsService.list_user_averages_for_game(
            self.game,
            mode=self.mode,
            exclude_user=self.user if exclude_user else None,
        )
        if not user_averages:
            return None

        return sum(user_averages) / len(user_averages)

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
