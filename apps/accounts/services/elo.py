from django.db.models import Avg
from apps.accounts.models import GameElo
from apps.games.models import GameResult


class Elo:
    def __init__(self, user, game):
        self.user = user
        self.game = game
        self.elo_obj, _ = GameElo.objects.get_or_create(user=user, game=game)

    def expected_score(self, player_rating, opponent_rating):
        return 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))

    def update(self, k: int = 32):
        user_avg = GameResult.objects.filter(
            user=self.user,
            game=self.game
        ).aggregate(avg=Avg("attempts"))["avg"]
        if user_avg is None:
            user_avg = 0

        global_avg = GameResult.objects.filter(
            game=self.game
        ).aggregate(avg=Avg("attempts"))["avg"]
        if global_avg is None:
            global_avg = 0

        result = 1 if user_avg < global_avg else 0
        expected = self.expected_score(self.elo_obj.elo, global_avg)
        new_rating = self.elo_obj.elo + k * (result - expected)

        self.elo_obj.elo = new_rating
        self.elo_obj.partidas += 1
        self.elo_obj.save()

    @staticmethod
    def global_elo_for_user(user):
        elos = GameElo.objects.filter(user=user)
        total_games = 0
        weighted_sum = 0

        for elo_entry in elos:
            weighted_sum += elo_entry.elo * elo_entry.partidas
            total_games += elo_entry.partidas

        if total_games == 0:
            return 1200

        return weighted_sum / total_games
