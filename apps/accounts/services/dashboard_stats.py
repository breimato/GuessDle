# services/dashboard_stats.py
from apps.accounts.models import GameElo
from apps.games.models import Game, GameResult
from apps.accounts.services.elo import Elo
from django.db.models import Avg, Count
from django.db import models


class DashboardStats:
    def __init__(self, user):
        self.user = user

    def available_games(self):
        return Game.objects.filter(active=True).order_by("name")

    def user_stats(self):
        stats = []
        for game in self.available_games():
            avg_data = GameResult.objects.filter(user=self.user, game=game).aggregate(avg=Avg("attempts"))
            elo_entry = GameElo.objects.filter(user=self.user, game=game).first()

            stats.append({
                "nombre": game.name,
                "slug": game.slug,
                "media_tiempo": avg_data["avg"] or 0,
                "elo": elo_entry.elo if elo_entry else 1200,
            })

        return stats

    def elo_global(self):
        return Elo.global_elo_for_user(self.user)

    def ranking_global(self):
        return (
            GameResult.objects
            .values("user__username")
            .annotate(media=Avg("attempts"), partidas=Count("id"))
            .order_by("media", "user__username")
        )

    def ranking_per_game(self):
        out = {}
        for g in self.available_games():
            out[g.slug] = (
                GameResult.objects.filter(game=g)
                .values("user__username")
                .annotate(media=Avg("attempts"), partidas=Count("id"))
                .order_by("media", "user__username")
            )
        return out

