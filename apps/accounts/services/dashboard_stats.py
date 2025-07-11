from django.db.models import Sum, Count, Q
from django.contrib.auth import get_user_model

from apps.accounts.models import GameElo
from apps.games.models import Game, PlaySession, GameAttempt


class DashboardStats:
    """
    Provides user and global statistics for games.
    Only computes aggregate values; does not mutate the database.
    """
    def __init__(self, user):
        self.user = user

    def available_games(self):
        """
        Returns all active games ordered by name.
        """
        return Game.objects.filter(active=True).order_by("name")

    def user_stats(self):
        """
        For each available game:
        - Average attempts across all the user's sessions (including unfinished ones).
        - Accumulated points (GameElo.elo).
        Games are sorted by points descending.
        """
        stats = []
        for game in self.available_games():
            attempts = self._get_user_attempt_counts(game)
            avg_attempts = sum(attempts) / len(attempts) if attempts else 0

            elo_entry = GameElo.objects.filter(user=self.user, game=game).first()
            points = elo_entry.elo if elo_entry else 0

            stats.append({
                "name": game.name,
                "slug": game.slug,
                "average_attempts": avg_attempts,
                "points": points,
            })

        return sorted(stats, key=lambda s: s["points"], reverse=True)

    def global_elo(self):
        """
        Returns the total ELO points the user has accumulated across all games.
        """
        records = GameElo.objects.filter(user=self.user)
        return sum(r.elo for r in records)

    def ranking_global(self):
        """
        Returns a ranking list of all users:
        - 'points': total ELO points (across all games)
        - 'games_finished': number of sessions finished (at least one correct attempt)
        - 'average_attempts': average attempts per finished session (includes all attempts, even from unfinished sessions)
        """
        User = get_user_model()
        users_qs = (
            GameElo.objects
            .filter(game__active=True)
            .values("user__username", "user_id")
            .annotate(total_points=Sum("elo"))
        )

        ranking = []
        for rec in users_qs:
            user = User.objects.get(pk=rec["user_id"])
            session_attempts = self._get_all_session_attempt_counts(user)
            sessions_finished = self._count_finished_sessions(user)
            total_attempts = sum(session_attempts)
            average_attempts = (total_attempts / sessions_finished) if sessions_finished else None

            ranking.append({
                "username": rec["user__username"],
                "points": rec["total_points"] or 0,
                "games_finished": sessions_finished,
                "average_attempts": average_attempts,
            })

        return sorted(ranking, key=lambda x: (-x["points"], x["username"]))

    def ranking_per_game(self):
        """
        For each game:
        - 'username': player name
        - 'points': GameElo.elo
        - 'games_finished': number of finished sessions (at least one correct attempt)
        - 'average_attempts': average attempts per finished session (uses all sessions with attempts, not just finished)
        """
        out = {}
        for game in self.available_games():
            rows = []
            for ge in GameElo.objects.filter(game=game).select_related("user"):
                session_attempts = self._get_session_attempt_counts(ge.user, game)
                sessions_finished = self._count_finished_sessions(ge.user, game)
                total_attempts = sum(session_attempts)
                average_attempts = (total_attempts / sessions_finished) if sessions_finished else None

                rows.append({
                    "username": ge.user.username,
                    "points": ge.elo,
                    "games_finished": sessions_finished,
                    "average_attempts": average_attempts,
                })

            out[game.slug] = sorted(rows, key=lambda x: (-x["points"], x["username"]))

        return out

    # ────────────────────────────
    # Métodos privados de soporte
    # ────────────────────────────

    def _get_user_attempt_counts(self, game):
        """
        Returns a list with the number of attempts for each session
        (for the dashboard user and for the provided game).
        Only includes sessions where at least one attempt exists.
        """
        sessions = (
            PlaySession.objects
            .filter(user=self.user, game=game)
            .annotate(num_attempts=Count("attempts"))
            .filter(num_attempts__gt=0)
        )
        return [s.num_attempts for s in sessions]

    def _get_session_attempt_counts(self, user, game):
        """
        Returns a list with the number of attempts for each session for 'user' and 'game'.
        Only includes sessions where at least one attempt exists.
        """
        sessions = (
            PlaySession.objects
            .filter(user=user, game=game)
            .annotate(num_attempts=Count("attempts"))
            .filter(num_attempts__gt=0)
        )
        return [s.num_attempts for s in sessions]

    def _get_all_session_attempt_counts(self, user):
        """
        Returns a list with the number of attempts for each session for 'user'
        in all games. Only includes sessions with at least one attempt.
        """
        sessions = (
            PlaySession.objects
            .filter(user=user)
            .annotate(num_attempts=Count("attempts"))
            .filter(num_attempts__gt=0)
        )
        return [s.num_attempts for s in sessions]

    def _count_finished_sessions(self, user, game=None):
        """
        Returns the count of sessions (for a user, optionally filtered by game)
        that have at least one correct attempt.
        """
        qs = PlaySession.objects.filter(user=user)
        if game is not None:
            qs = qs.filter(game=game)
        return (
            qs.annotate(correct_count=Count("attempts", filter=Q(attempts__is_correct=True)))
              .filter(correct_count__gt=0)
              .distinct()
              .count()
        )
