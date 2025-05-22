# apps/accounts/management/commands/recalcular_elo.py

from django.core.management.base import BaseCommand
from django.db.models import Avg
from collections import defaultdict

from apps.games.models import GameResult
from apps.accounts.models import GameElo


class Command(BaseCommand):
    help = "Recalculates all user ELOs retroactively based on existing GameResults."

    def expected_score(self, player_rating, opponent_rating):
        return 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))

    def update_rating(self, current_rating, result, opponent_rating, k=32):
        expected = self.expected_score(current_rating, opponent_rating)
        return current_rating + k * (result - expected)

    def handle(self, *args, **options):
        self.stdout.write("🧠 Deleting existing ELOs...")
        GameElo.objects.all().delete()

        self.stdout.write("📊 Calculating global averages per game...")
        global_averages = {
            game_id: GameResult.objects.filter(game_id=game_id).aggregate(avg=Avg("attempts"))["avg"] or 0
            for game_id in GameResult.objects.values_list("game_id", flat=True).distinct()
        }

        self.stdout.write("🔁 Processing historical results...")
        results = (
            GameResult.objects
            .select_related("user", "game")
            .order_by("completed_at")
        )

        elos = defaultdict(lambda: {"elo": 1200.0, "games": 0})

        for result in results:
            key = (result.user_id, result.game_id)
            current = elos[key]

            global_avg = global_averages[result.game_id]
            match_result = 1 if result.attempts < global_avg else 0

            updated_rating = self.update_rating(current["elo"], match_result, global_avg)

            current["elo"] = updated_rating
            current["games"] += 1

        self.stdout.write("💾 Saving recalculated ELOs...")

        for (user_id, game_id), data in elos.items():
            GameElo.objects.create(
                user_id=user_id,
                game_id=game_id,
                elo=data["elo"],
                partidas=data["games"]
            )

        self.stdout.write(self.style.SUCCESS("✅ ELO recalculation complete."))
