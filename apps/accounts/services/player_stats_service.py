"""Canonical player statistics calculations for dashboard and rankings."""

from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum

from apps.accounts.models import GameElo
from apps.games.models import Game, PlaySession


class PlayerStatsService:
    """Single source of truth for ELO, games finished and average attempts."""

    @staticmethod
    def get_game_stats(user, game) -> dict:
        """Return points, games_finished and average_attempts for one user and game."""

        elo_record = GameElo.objects.filter(user=user, game=game).first()
        points = elo_record.elo if elo_record else 0

        session_stats = (
            PlaySession.objects.filter(user=user, game=game)
            .aggregate(
                total_attempts=Count("attempts"),
                games_finished=Count("id", filter=Q(attempts__is_correct=True), distinct=True),
            )
        )
        games_finished = session_stats["games_finished"] or 0
        total_attempts = session_stats["total_attempts"] or 0
        average_attempts = (
            total_attempts / games_finished if games_finished > 0 else None
        )

        return {
            "points": points,
            "games_finished": games_finished,
            "average_attempts": average_attempts,
        }

    @staticmethod
    def get_user_games_stats(user) -> list[dict]:
        """Stats per active game for the dashboard table."""

        rows = []
        for game in Game.objects.filter(active=True).order_by("name"):
            stats = PlayerStatsService.get_game_stats(user, game)
            rows.append(
                {
                    "name": game.name,
                    "slug": game.slug,
                    "average_attempts": stats["average_attempts"] or 0,
                    "points": stats["points"],
                    "games_finished": stats["games_finished"],
                }
            )
        return sorted(rows, key=lambda row: row["points"], reverse=True)

    @staticmethod
    def get_global_elo(user) -> float:
        """Total ELO across active games."""

        return (
            GameElo.objects.filter(user=user, game__active=True).aggregate(
                total=Sum("elo")
            )["total"]
            or 0
        )

    @staticmethod
    def get_global_stats(user) -> dict:
        """Global games finished and average attempts (won games only in denominator)."""

        session_stats = (
            PlaySession.objects.filter(user=user, game__active=True)
            .aggregate(
                total_attempts=Count("attempts"),
                games_finished=Count("id", filter=Q(attempts__is_correct=True), distinct=True),
            )
        )
        games_finished = session_stats["games_finished"] or 0
        total_attempts = session_stats["total_attempts"] or 0
        average_attempts = (
            total_attempts / games_finished if games_finished > 0 else None
        )

        return {
            "points": PlayerStatsService.get_global_elo(user),
            "games_finished": games_finished,
            "average_attempts": average_attempts,
        }

    @staticmethod
    def build_global_ranking() -> list[dict]:
        """Global leaderboard sorted by total ELO."""

        user_ids = (
            GameElo.objects.filter(game__active=True)
            .values_list("user_id", flat=True)
            .distinct()
        )
        rows = []
        for user in User.objects.filter(id__in=user_ids).order_by("username"):
            stats = PlayerStatsService.get_global_stats(user)
            rows.append(
                {
                    "username": user.username,
                    "points": stats["points"],
                    "games_finished": stats["games_finished"],
                    "average_attempts": stats["average_attempts"],
                }
            )
        return sorted(rows, key=lambda row: (-row["points"], row["username"]))

    @staticmethod
    def build_ranking_per_game() -> dict:
        """Leaderboard per active game slug."""

        rankings = {}
        for game in Game.objects.filter(active=True).order_by("name"):
            user_ids = GameElo.objects.filter(game=game).values_list("user_id", flat=True)
            rows = []
            for user in User.objects.filter(id__in=user_ids).order_by("username"):
                stats = PlayerStatsService.get_game_stats(user, game)
                rows.append(
                    {
                        "username": user.username,
                        "points": stats["points"],
                        "games_finished": stats["games_finished"],
                        "average_attempts": stats["average_attempts"],
                    }
                )
            rankings[game.slug] = sorted(
                rows, key=lambda row: (-row["points"], row["username"])
            )
        return rankings

    @staticmethod
    def calculate_user_average_attempts(user, game) -> float | None:
        """Average attempts per won game (used by gameplay ScoreService)."""

        stats = PlayerStatsService.get_game_stats(user, game)
        return stats["average_attempts"]
