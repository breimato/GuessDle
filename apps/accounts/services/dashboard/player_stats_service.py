from django.contrib.auth.models import User
from django.db.models import Q, Sum

from apps.accounts.models import GameElo
from apps.accounts.services.dashboard.ranking_scope import (
    ranking_elo_filter_q,
    ranking_modes_for_game,
    ranking_session_filter_q,
)
from apps.games.models import Game, GameAttempt, GameModePlayType, PlaySession


class PlayerStatsService:
    @staticmethod
    def _includes_legacy_normal_mode(game, mode) -> bool:
        return (
            mode is not None
            and mode.slug == "normal"
            and mode.play_type == GameModePlayType.WORDLE
            and bool(ranking_modes_for_game(game))
        )

    @staticmethod
    def _elo_lookup(game, mode=None):
        lookup = {"game": game}
        if mode:
            lookup["mode"] = mode
        else:
            lookup["mode__isnull"] = True
        return lookup

    @staticmethod
    def _elo_points(user, game, mode=None) -> float:
        if PlayerStatsService._includes_legacy_normal_mode(game, mode):
            mode_row = GameElo.objects.filter(
                user=user, game=game, mode=mode
            ).first()
            legacy_row = GameElo.objects.filter(
                user=user, game=game, mode__isnull=True
            ).first()
            return (mode_row.elo if mode_row else 0) + (legacy_row.elo if legacy_row else 0)

        elo_record = GameElo.objects.filter(
            user=user, **PlayerStatsService._elo_lookup(game, mode)
        ).first()
        return elo_record.elo if elo_record else 0

    @staticmethod
    def _session_queryset(user, game, mode=None):
        queryset = PlaySession.objects.filter(user=user, game=game)
        if mode is None:
            return queryset.filter(mode__isnull=True)
        if PlayerStatsService._includes_legacy_normal_mode(game, mode):
            return queryset.filter(Q(mode=mode) | Q(mode__isnull=True))
        return queryset.filter(mode=mode)

    @staticmethod
    def _ranking_elo_user_ids(game, mode=None):
        if PlayerStatsService._includes_legacy_normal_mode(game, mode):
            return (
                GameElo.objects.filter(game=game)
                .filter(Q(mode=mode) | Q(mode__isnull=True))
                .values_list("user_id", flat=True)
                .distinct()
            )
        return GameElo.objects.filter(
            **PlayerStatsService._elo_lookup(game, mode)
        ).values_list("user_id", flat=True)

    @staticmethod
    def _winning_sessions(base_sessions):
        return base_sessions.filter(attempts__is_correct=True).distinct()

    @staticmethod
    def _surrendered_sessions(base_sessions):
        return base_sessions.filter(surrendered=True)

    @staticmethod
    def _count_finished_games(base_sessions):
        return PlayerStatsService._winning_sessions(base_sessions).count()

    @staticmethod
    def _count_ranking_attempts(base_sessions):
        winning_sessions = PlayerStatsService._winning_sessions(base_sessions)
        winning_attempts = GameAttempt.objects.filter(session__in=winning_sessions).count()

        surrendered_sessions = PlayerStatsService._surrendered_sessions(base_sessions)
        surrendered_attempts = GameAttempt.objects.filter(session__in=surrendered_sessions).count()

        return winning_attempts + surrendered_attempts

    @staticmethod
    def _calculate_ranking_average(base_sessions):
        games_finished = PlayerStatsService._count_finished_games(base_sessions)
        if games_finished == 0:
            return None

        total_ranking_attempts = PlayerStatsService._count_ranking_attempts(base_sessions)
        return total_ranking_attempts / games_finished

    @staticmethod
    def get_game_stats(user, game, mode=None) -> dict:
        points = PlayerStatsService._elo_points(user, game, mode)
        base_sessions = PlayerStatsService._session_queryset(user, game, mode)
        games_finished = PlayerStatsService._count_finished_games(base_sessions)
        average_attempts = PlayerStatsService._calculate_ranking_average(base_sessions)

        return {
            "points": points,
            "games_finished": games_finished,
            "average_attempts": average_attempts,
        }

    @staticmethod
    def build_stats_row(user, game, mode=None) -> dict:
        stats = PlayerStatsService.get_game_stats(user, game, mode=mode)
        if mode:
            return {
                "name": f"{game.name} ({mode.label})",
                "slug": game.slug,
                "mode_slug": mode.slug,
                "average_attempts": stats["average_attempts"] or 0,
                "points": stats["points"],
                "games_finished": stats["games_finished"],
            }

        return {
            "name": game.name,
            "slug": game.slug,
            "mode_slug": None,
            "average_attempts": stats["average_attempts"] or 0,
            "points": stats["points"],
            "games_finished": stats["games_finished"],
        }

    @staticmethod
    def get_user_games_stats(user) -> list[dict]:
        rows = []
        for game in Game.objects.filter(active=True).prefetch_related("modes").order_by("name"):
            modes = ranking_modes_for_game(game)
            if modes:
                for mode in modes:
                    rows.append(PlayerStatsService.build_stats_row(user, game, mode=mode))
            else:
                rows.append(PlayerStatsService.build_stats_row(user, game))

        return sorted(rows, key=lambda row: row["points"], reverse=True)

    @staticmethod
    def get_global_elo(user) -> float:
        return (
            GameElo.objects.filter(user=user, game__active=True)
            .filter(ranking_elo_filter_q())
            .aggregate(total=Sum("elo"))["total"]
            or 0
        )

    @staticmethod
    def get_global_stats(user) -> dict:
        base_sessions = PlaySession.objects.filter(user=user, game__active=True).filter(
            ranking_session_filter_q()
        )
        games_finished = PlayerStatsService._count_finished_games(base_sessions)
        average_attempts = PlayerStatsService._calculate_ranking_average(base_sessions)

        return {
            "points": PlayerStatsService.get_global_elo(user),
            "games_finished": games_finished,
            "average_attempts": average_attempts,
        }

    @staticmethod
    def build_global_ranking() -> list[dict]:
        user_ids = (
            GameElo.objects.filter(game__active=True)
            .filter(ranking_elo_filter_q())
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
        user_ids = PlayerStatsService._ranking_elo_user_ids(game, mode)
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
            modes = ranking_modes_for_game(game)
            if modes:
                rankings[game.slug] = {
                    mode.slug: PlayerStatsService._build_ranking_rows(game, mode=mode)
                    for mode in modes
                }
            else:
                rankings[game.slug] = PlayerStatsService._build_ranking_rows(game)
        return rankings

    @staticmethod
    def calculate_user_average_attempts(user, game, mode=None) -> float | None:
        stats = PlayerStatsService.get_game_stats(user, game, mode=mode)
        return stats["average_attempts"]

    @staticmethod
    def list_user_averages_for_game(game, mode=None, exclude_user=None) -> list[float]:
        play_sessions = PlaySession.objects.filter(game=game)
        if mode:
            play_sessions = play_sessions.filter(mode=mode)
        else:
            play_sessions = play_sessions.filter(mode__isnull=True)

        user_ids = play_sessions.values_list("user_id", flat=True).distinct()
        if exclude_user is not None:
            user_ids = user_ids.exclude(user_id=exclude_user.id)

        averages = []
        for user in User.objects.filter(id__in=user_ids):
            average_attempts = PlayerStatsService.calculate_user_average_attempts(
                user,
                game,
                mode=mode,
            )
            if average_attempts is None:
                continue
            averages.append(average_attempts)

        return averages
