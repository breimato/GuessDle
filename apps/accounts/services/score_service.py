from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q, Sum, FloatField, ExpressionWrapper
from django.db.models.functions import Cast
from apps.games.models import ScoringRule, GameAttempt, PlaySessionType, PlaySession
from apps.accounts.models import GameElo

class ScoreService:
    """Service to manage and query user points and game attempts statistics."""

    def __init__(self, user, game):
        """Initialize the score service with a user and a game."""

        self.user = user
        self.game = game
        self.score_obj, _ = GameElo.objects.get_or_create(user=user, game=game)

    def add_points_for_attempts(self, attempts_count: int) -> int:
        """Add points to the user's score based on the number of attempts and update the database."""

        points = self._calculate_points_for_attempts(attempts_count)
        self.score_obj.elo += points
        self.score_obj.partidas += 1
        self.score_obj.save(update_fields=("elo", "partidas"))
        return points

    def calculate_user_average_attempts(self) -> float | None:
        """Calculate the average number of attempts for the user in this game across completed sessions."""

        session_statistics = (
            PlaySession.objects
            .filter(user=self.user, game=self.game)
            .aggregate(
                total_tries=Count('attempts'),
                completed=Count('id', filter=Q(attempts__is_correct=True), distinct=True)
            )
        )
        completed_sessions_count = session_statistics['completed'] or 0
        if completed_sessions_count == 0:
            return None

        return (session_statistics['total_tries'] or 0) / completed_sessions_count

    def calculate_global_average_of_averages(self, exclude_user=True) -> float | None:
        """Calculate the global average of individual user averages for completed sessions in this game."""

        play_sessions = PlaySession.objects.filter(game=self.game)
        if exclude_user:
            play_sessions = play_sessions.exclude(user=self.user)

        user_averages = (
            play_sessions
            .values('user')
            .annotate(
                total_attempts=Count('attempts'),
                completed_sessions=Count('id', filter=Q(attempts__is_correct=True), distinct=True)
            )
            .filter(completed_sessions__gt=0)
            .annotate(
                user_avg=ExpressionWrapper(
                    Cast('total_attempts', FloatField()) / Cast('completed_sessions', FloatField()),
                    output_field=FloatField()
                )
            )
        )

        global_average_result = user_averages.aggregate(avg_of_avgs=Avg('user_avg'))
        return global_average_result['avg_of_avgs']

    def _calculate_points_for_attempts(self, attempts_count: int) -> int:
        """Get the point value for a specific number of attempts based on rules or fallback scoring."""

        scoring_rule = (
            ScoringRule.objects
            .filter(game=self.game, attempt_no=attempts_count)
            .first()
            or ScoringRule.objects.filter(game__isnull=True, attempt_no=attempts_count).first()
        )
        if scoring_rule:
            return scoring_rule.points

        decrement = getattr(settings, "SCORING_FALLBACK", {}).get("decrement", 10)
        floor = getattr(settings, "SCORING_FALLBACK", {}).get("floor", 0)
        fallback_points = 50 - decrement * (attempts_count - 3)
        return max(floor, fallback_points)

