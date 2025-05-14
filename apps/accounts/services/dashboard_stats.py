# services/dashboard_stats.py
from apps.games.models import Game, GameResult
from django.db.models import Avg, Count
from django.db import models


class DashboardStats:
    def __init__(self, user):
        self.user = user

    def available_games(self):
        return Game.objects.filter(active=True).order_by("name")

    def user_stats(self):
        return (
            GameResult.objects
            .filter(user=self.user)
            .values(nombre=models.F("game__name"))
            .annotate(media_tiempo=Avg("attempts"))
            .order_by("nombre")
        )

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
