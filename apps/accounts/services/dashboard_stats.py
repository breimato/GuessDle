from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.contrib.auth import get_user_model

from apps.accounts.models import GameElo
from apps.games.models import Game, PlaySession, GameAttempt
from django.contrib.auth import get_user_model



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
        Suma total de puntos ELO del usuario en todos los juegos.
        Devuelve 0 si no tiene partidas.
        """
        records = GameElo.objects.filter(user=self.user)
        total_elo = sum(r.elo for r in records)
        return total_elo


    def ranking_global(self):
        """
        Ranking global de usuarios con:
        - puntos (ELO total)
        - partidas (total de sesiones con al menos un intento)
        - media (media de intentos por partida real jugada)
        """
        User = get_user_model()

        users_qs = GameElo.objects.values("user__username", "user_id").annotate(
            puntos_totales=Sum("elo")
        )

        rows = []
        for record in users_qs:
            user = User.objects.get(pk=record["user_id"])
            sessions = PlaySession.objects.filter(user=user)
            # solo sesiones que tengan al menos 1 intento
            attempts_counts = [
                GameAttempt.objects.filter(session=s).count()
                for s in sessions
                if GameAttempt.objects.filter(session=s).exists()
            ]
            num_partidas = len(attempts_counts)
            media_global = sum(attempts_counts) / num_partidas if num_partidas else None

            rows.append({
                "username": record["user__username"],
                "puntos": record["puntos_totales"] or 0,
                "partidas": num_partidas,
                "media": media_global,
            })

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