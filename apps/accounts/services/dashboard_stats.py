from collections import defaultdict
from django.db.models import Sum, Count

from apps.accounts.models import GameElo
from apps.games.models import Game, PlaySession


class DashboardStats:
    """Service to gather and calculate global and game-specific user statistics for the dashboard."""

    def __init__(self, user):
        """Initialize the dashboard stats service for a given user."""

        self.user = user

    def fetch_active_games(self):
        """Retrieve all currently active games sorted by name."""

        return Game.objects.filter(active=True).order_by("name")

    def calculate_user_statistics(self):
        """Calculate stats per game for the current user, including average attempts and total points."""

        user_sessions = self._fetch_user_sessions()
        average_attempts_mapping = self._calculate_average_attempts(user_sessions)
        game_elo_mapping = self._fetch_user_elo_mapping()

        dashboard_statistics = []
        for game in self.fetch_active_games():
            points = game_elo_mapping.get(game.id, 0)
            average_attempts = average_attempts_mapping.get(game.id, 0)

            dashboard_statistics.append(
                {
                    "name": game.name,
                    "slug": game.slug,
                    "average_attempts": average_attempts,
                    "points": points,
                }
            )

        return sorted(dashboard_statistics, key=lambda s: s["points"], reverse=True)

    def calculate_global_elo_score(self):
        """Calculate the total accumulated ELO points for the user across all games."""

        game_elo_records = GameElo.objects.filter(user=self.user)
        global_elo_score = sum(record.elo for record in game_elo_records)
        return global_elo_score

    def generate_global_ranking(self):
        """Generate the global leaderboard of users sorted by total points."""

        global_rankings_query = self._fetch_global_rankings()
        user_session_statistics_mapping = self._calculate_global_session_stats()

        ranking_rows = []
        for record in global_rankings_query:
            user_id = record["user_id"]
            games_played_count, global_attempts_average = user_session_statistics_mapping.get(user_id, (0, None))

            ranking_rows.append({
                "username": record["user__username"],
                "points": record["total_points"] or 0,
                "games_played": games_played_count,
                "average": global_attempts_average,
            })

        return sorted(ranking_rows, key=lambda x: (-x["points"], x["username"]))

    def generate_ranking_per_game(self):
        """Generate leaderboards for each individual game, showing points, games played, and average attempts."""

        session_statistics_mapping = self._calculate_per_game_session_stats()
        game_elos = GameElo.objects.select_related("user", "game")

        game_rankings = {}
        for game in self.fetch_active_games():
            game_rankings[game.slug] = []

        for game_elo in game_elos:
            if not game_elo.game.active:
                continue
            games_played_count, attempts_average = session_statistics_mapping.get(
                (game_elo.game_id, game_elo.user_id), (0, None)
            )
            game_rankings[game_elo.game.slug].append(
                {
                    "username": game_elo.user.username,
                    "points": game_elo.elo,
                    "average": attempts_average,
                    "games_played": games_played_count,
                }
            )

        for slug in game_rankings:
            game_rankings[slug] = sorted(game_rankings[slug], key=lambda x: (-x["points"], x["username"]))

        return game_rankings

    def _fetch_user_sessions(self):
        """Retrieve all play sessions for the current user annotated with attempt counts."""

        return (
            PlaySession.objects.filter(user=self.user)
            .annotate(num_attempts=Count('attempts'))
            .values('game_id', 'num_attempts')
        )

    def _calculate_average_attempts(self, user_sessions):
        """Calculate the average attempts mapping by game ID from user play sessions."""

        attempts_by_game = defaultdict(list)
        for session_item in user_sessions:
            attempts_count = session_item['num_attempts']
            if attempts_count > 0:
                attempts_by_game[session_item['game_id']].append(attempts_count)

        return {
            game_id: sum(attempts) / len(attempts)
            for game_id, attempts in attempts_by_game.items()
        }

    def _fetch_user_elo_mapping(self):
        """Retrieve a mapping of game IDs to Elo points for the current user."""

        game_elos = GameElo.objects.filter(user=self.user).values('game_id', 'elo')
        return {item['game_id']: item['elo'] for item in game_elos}

    def _fetch_global_rankings(self):
        """Fetch total points query grouped by user."""

        return GameElo.objects.values("user__username", "user_id").annotate(
            total_points=Sum("elo")
        )

    def _calculate_global_session_stats(self):
        """Calculate games played count and average attempts for all users across their sessions."""

        all_play_sessions = (
            PlaySession.objects.annotate(num_attempts=Count('attempts'))
            .values('user_id', 'num_attempts')
        )
        
        attempts_by_user = defaultdict(list)
        for session_item in all_play_sessions:
            attempts_count = session_item['num_attempts']
            if attempts_count > 0:
                attempts_by_user[session_item['user_id']].append(attempts_count)
                
        user_session_statistics_mapping = {}
        for user_id, attempts in attempts_by_user.items():
            user_session_statistics_mapping[user_id] = (len(attempts), sum(attempts) / len(attempts))
        
        return user_session_statistics_mapping

    def _calculate_per_game_session_stats(self):
        """Calculate session statistics mapped by (game_id, user_id)."""

        all_play_sessions = (
            PlaySession.objects.annotate(num_attempts=Count('attempts'))
            .values('game_id', 'user_id', 'num_attempts')
        )
        
        attempts_by_game_and_user = defaultdict(list)
        for session_item in all_play_sessions:
            attempts_count = session_item['num_attempts']
            if attempts_count > 0:
                attempts_by_game_and_user[(session_item['game_id'], session_item['user_id'])].append(attempts_count)
                
        session_statistics_mapping = {}
        for key, attempts in attempts_by_game_and_user.items():
            session_statistics_mapping[key] = (len(attempts), sum(attempts) / len(attempts))
            
        return session_statistics_mapping