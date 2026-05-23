from apps.accounts.services.player_stats_service import PlayerStatsService


class DashboardStats:
    """Facade for dashboard views; delegates to PlayerStatsService."""

    def __init__(self, user):
        self.user = user

    def fetch_active_games(self):
        from apps.games.models import Game

        return Game.objects.filter(active=True).order_by("name")

    def calculate_user_statistics(self):
        return PlayerStatsService.get_user_games_stats(self.user)

    def calculate_global_elo_score(self):
        return PlayerStatsService.get_global_elo(self.user)

    def generate_global_ranking(self):
        return PlayerStatsService.build_global_ranking()

    def generate_ranking_per_game(self):
        return PlayerStatsService.build_ranking_per_game()
