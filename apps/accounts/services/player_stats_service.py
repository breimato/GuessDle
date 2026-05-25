from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum

from apps.accounts.models import GameElo
from apps.games.models import Game, GameAttempt, PlaySession


class PlayerStatsService:
    @staticmethod
    def _elo_lookup(game, mode=None):
        lookup = {"game": game}
        if mode:
            lookup["mode"] = mode
        else:
            lookup["mode__isnull"] = True
        return lookup

    @staticmethod
    def _session_queryset(user, game, mode=None):
        queryset = PlaySession.objects.filter(user=user, game=game)
        if mode:
            return queryset.filter(mode=mode)
        return queryset.filter(mode__isnull=True)

    @staticmethod
    def get_game_stats(user, game, mode=None) -> dict:
        elo_record = GameElo.objects.filter(
            user=user, **PlayerStatsService._elo_lookup(game, mode)
        ).first()
        points = elo_record.elo if elo_record else 0

        base_sessions = PlayerStatsService._session_queryset(user, game, mode)
        session_stats = base_sessions.aggregate(
            games_finished=Count(
                "id", filter=Q(attempts__is_correct=True), distinct=True
            ),
        )
        games_finished = session_stats["games_finished"] or 0
        if games_finished:
            total_attempts = GameAttempt.objects.filter(
                session__in=base_sessions.filter(attempts__is_correct=True)
            ).count()
        else:
            total_attempts = 0
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
        rows = []
        for game in Game.objects.filter(active=True).prefetch_related("modes").order_by("name"):
            modes = [m for m in game.modes.all() if m.active]
            if modes:
                for mode in sorted(modes, key=lambda m: (m.sort_order, m.slug)):
                    stats = PlayerStatsService.get_game_stats(user, game, mode=mode)
                    rows.append(
                        {
                            "name": f"{game.name} ({mode.label})",
                            "slug": game.slug,
                            "mode_slug": mode.slug,
                            "average_attempts": stats["average_attempts"] or 0,
                            "points": stats["points"],
                            "games_finished": stats["games_finished"],
                        }
                    )
            else:
                stats = PlayerStatsService.get_game_stats(user, game)
                rows.append(
                    {
                        "name": game.name,
                        "slug": game.slug,
                        "mode_slug": None,
                        "average_attempts": stats["average_attempts"] or 0,
                        "points": stats["points"],
                        "games_finished": stats["games_finished"],
                    }
                )
        return sorted(rows, key=lambda row: row["points"], reverse=True)

    @staticmethod
    def get_global_elo(user) -> float:
        return (
            GameElo.objects.filter(user=user, game__active=True).aggregate(
                total=Sum("elo")
            )["total"]
            or 0
        )

    @staticmethod
    def get_global_stats(user) -> dict:
        base_sessions = PlaySession.objects.filter(user=user, game__active=True)
        games_finished = base_sessions.filter(attempts__is_correct=True).distinct().count()
        if games_finished:
            total_attempts = GameAttempt.objects.filter(
                session__in=base_sessions.filter(attempts__is_correct=True)
            ).count()
        else:
            total_attempts = 0
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
    def _build_ranking_rows(game, mode=None) -> list[dict]:
        lookup = PlayerStatsService._elo_lookup(game, mode)
        user_ids = GameElo.objects.filter(**lookup).values_list("user_id", flat=True)
        rows = []
        for user in User.objects.filter(id__in=user_ids).order_by("username"):
            stats = PlayerStatsService.get_game_stats(user, game, mode=mode)
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
        rankings = {}
        for game in Game.objects.filter(active=True).prefetch_related("modes").order_by("name"):
            modes = [m for m in game.modes.all() if m.active]
            if modes:
                rankings[game.slug] = {
                    mode.slug: PlayerStatsService._build_ranking_rows(game, mode=mode)
                    for mode in sorted(modes, key=lambda m: (m.sort_order, m.slug))
                }
            else:
                rankings[game.slug] = PlayerStatsService._build_ranking_rows(game)
        return rankings

    @staticmethod
    def calculate_user_average_attempts(user, game, mode=None) -> float | None:
        stats = PlayerStatsService.get_game_stats(user, game, mode=mode)
        return stats["average_attempts"]
