from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.contrib.auth import get_user_model

from apps.accounts.models import GameElo
from apps.games.models import Game, PlaySession, GameAttempt


class DashboardStats:
    def __init__(self, user):
        self.user = user

    def available_games(self):
        return Game.objects.filter(active=True).order_by("name")

    def user_stats(self):
        """
        Para cada juego disponible:
        - Calcula la media de intentos en todas las sesiones de este usuario.
        - Lee los puntos acumulados (GameElo.elo).
        No se filtra por tipo de sesión ni se exige que la partida esté completada.
        """
        stats = []
        User = get_user_model()

        for game in self.available_games():
            sessions = PlaySession.objects.filter(user=self.user, game=game)

            attempts_counts = [
                GameAttempt.objects.filter(session=s).count()
                for s in sessions
                if GameAttempt.objects.filter(session=s).exists()
            ]

            avg_attempts = sum(attempts_counts) / len(attempts_counts) if attempts_counts else 0

            elo_entry = GameElo.objects.filter(user=self.user, game=game).first()
            puntos = elo_entry.elo if elo_entry else 0

            stats.append(
                {
                    "nombre": game.name,
                    "slug": game.slug,
                    "media_intentos": avg_attempts,
                    "puntos": puntos,
                }
            )

        return sorted(stats, key=lambda s: s["puntos"], reverse=True)

    def elo_global(self):
        """
        Promedio ponderado de puntos en TODOS los juegos.
        Devuelve 0 si no hay partidas jugadas.
        """
        records = GameElo.objects.filter(user=self.user)
        total_partidas = sum(r.partidas for r in records)
        if total_partidas == 0:
            return 0

        weighted_sum = sum(r.elo * r.partidas for r in records)
        return weighted_sum / total_partidas

    def ranking_global(self):
        """
        Ranking global de usuarios basado en puntos (“puntos_global”) y media de intentos.
        No se filtra por tipo de sesión ni por si la partida fue resuelta.
        """
        User = get_user_model()

        user_points_qs = (
            GameElo.objects.values("user__username", "user_id")
            .annotate(
                weighted_sum=Sum(F("elo") * F("partidas"), output_field=FloatField()),
                total_games=Sum("partidas"),
            )
            .annotate(
                puntos_global=ExpressionWrapper(
                    F("weighted_sum") / F("total_games"), output_field=FloatField()
                )
            )
        )

        rows = []
        for record in user_points_qs:
            username = record["user__username"]
            puntos_g = record["puntos_global"] or 0

            user_obj = User.objects.get(username=username)
            sessions = PlaySession.objects.filter(user=user_obj)

            attempts_counts = [
                GameAttempt.objects.filter(session=s).count()
                for s in sessions
                if GameAttempt.objects.filter(session=s).exists()
            ]

            media = sum(attempts_counts) / len(attempts_counts) if attempts_counts else None
            partidas = len(attempts_counts)

            rows.append(
                {
                    "username": username,
                    "puntos": puntos_g,
                    "media": media,
                    "partidas": partidas,
                }
            )

        return sorted(rows, key=lambda x: (-x["puntos"], x["username"]))

    def ranking_per_game(self):
        """
        Para cada juego:
        - username
        - puntos (GameElo.elo)
        - partidas (nº de sesiones con al menos un intento)
        - media (media de intentos por sesión)
        Sin filtrado por tipo de sesión ni por finalización.
        """
        out = {}

        for game in self.available_games():
            rows = []
            for ge in GameElo.objects.filter(game=game).select_related("user"):
                sessions = PlaySession.objects.filter(user=ge.user, game=game)

                attempts_counts = [
                    GameAttempt.objects.filter(session=s).count()
                    for s in sessions
                    if GameAttempt.objects.filter(session=s).exists()
                ]

                media = sum(attempts_counts) / len(attempts_counts) if attempts_counts else None
                partidas = len(attempts_counts)

                rows.append(
                    {
                        "username": ge.user.username,
                        "puntos": ge.elo,
                        "media": media,
                        "partidas": partidas,
                    }
                )

            out[game.slug] = sorted(rows, key=lambda x: (-x["puntos"], x["username"]))

        return out