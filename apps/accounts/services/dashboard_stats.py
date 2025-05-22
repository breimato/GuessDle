from apps.accounts.models import GameElo
from apps.games.models import Game, GameResult
from apps.accounts.services.elo import Elo
from django.db.models import Avg, Count, F, Subquery, OuterRef, Sum, ExpressionWrapper, FloatField


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

        return sorted(stats, key=lambda s: s["elo"], reverse=True)

    def elo_global(self):
        return Elo.global_elo_for_user(self.user)

    def ranking_global(self):
        # ELO ponderado: (elo * partidas) / total_partidas
        user_elos = (
            GameElo.objects
            .values("user__username", "user_id")
            .annotate(
                weighted_sum=Sum(F("elo") * F("partidas"), output_field=FloatField()),
                total_games=Sum("partidas"),
            )
            .annotate(
                elo_global=ExpressionWrapper(
                    F("weighted_sum") / F("total_games"),
                    output_field=FloatField()
                )
            )
        )

        # Agregamos media real desde GameResult
        result_stats = (
            GameResult.objects
            .values("user__username")
            .annotate(
                media=Avg("attempts"),
                partidas=Count("id")
            )
        )

        # Convertimos a dict para merge rápido
        result_map = {r["user__username"]: r for r in result_stats}

        rows = []
        for e in user_elos:
            username = e["user__username"]

            rows.append({
                "username": username,
                "elo": e["elo_global"] or 1200,
                "media": result_map.get(username, {}).get("media", None),
                "partidas": result_map.get(username, {}).get("partidas", 0),
            })

        # Ordenamos por ELO descendente
        return sorted(rows, key=lambda x: (-x["elo"], x["username"]))

    def ranking_per_game(self):
        out = {}
        for game in self.available_games():
            out[game.slug] = (
                GameElo.objects
                .filter(game=game)
                .select_related("user")
                .annotate(
                    username=F("user__username"),
                    media=Subquery(
                        GameResult.objects
                        .filter(user=OuterRef("user"), game=OuterRef("game"))
                        .values("user")
                        .annotate(avg_attempts=Avg("attempts"))
                        .values("avg_attempts")[:1]
                    )
                )
                .values("username", "elo", "partidas", "media")
                .order_by("-elo", "user_id")
            )
        return out


