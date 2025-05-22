# apps/accounts/management/commands/recalcular_elo.py

from django.core.management.base import BaseCommand
from django.db.models import Avg
from collections import defaultdict

from apps.games.models import GameResult
from apps.accounts.models import GameElo


class Command(BaseCommand):
    help = "Recalculates ELOs using historical averages per game (based on results prior to each match)."

    def expected_score(self, player_rating, opponent_rating):
        return 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))

    def update_rating(self, current_rating, result, opponent_rating, k=32):
        expected = self.expected_score(current_rating, opponent_rating)
        return current_rating + k * (result - expected)

    def handle(self, *args, **options):
        self.stdout.write("🧠 Deleting existing ELOs...")
        GameElo.objects.all().delete()

        self.stdout.write("🔁 Processing historical results with dynamic averages...")
        results = (
            GameResult.objects
            .select_related("user", "game")
            .order_by("completed_at")
        )

        elos = defaultdict(lambda: {"elo": 1200.0, "games": 0})

        for res in results:
            key = (res.user_id, res.game_id)
            current = elos[key]

            # 💡 Calculamos la media histórica hasta ese punto
            past_results = GameResult.objects.filter(
                game=res.game,
                completed_at__lt=res.completed_at
            )

            historical_avg = past_results.aggregate(avg=Avg("attempts"))["avg"] or 0

            # Si no hay historial previo, lo dejamos sin actualizar
            if historical_avg == 0:
                continue

            match_result = 1 if res.attempts < historical_avg else 0

            updated_rating = self.update_rating(current["elo"], match_result, historical_avg)

            current["elo"] = updated_rating
            current["games"] += 1

        self.stdout.write("💾 Saving updated ELOs...")

        for (user_id, game_id), data in elos.items():
            GameElo.objects.create(
                user_id=user_id,
                game_id=game_id,
                elo=data["elo"],
                partidas=data["games"]
            )

        self.stdout.write(self.style.SUCCESS("✅ ELO recalculated using historical averages."))
