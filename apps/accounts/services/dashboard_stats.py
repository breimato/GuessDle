from apps.accounts.models import GameElo
from apps.games.models import Game, GameAttempt, PlaySession
from apps.accounts.services.score_service import ScoreService
from django.db.models import Avg, Count, F, Subquery, OuterRef, Sum, ExpressionWrapper, FloatField
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
        - Calcula la media de intentos de los daily completados por este usuario.
        - Lee los puntos acumulados (GameElo.elo).
        """
        stats = []
        User = get_user_model()

        for game in self.available_games():
            # 1️⃣ Todas las sesiones DAILY de este usuario y juego que tienen al menos un intento correcto
            daily_sessions = PlaySession.objects.filter(
                user=self.user,
                game=game,
                session_type="DAILY"
            )

            attempts_counts = []
            for session in daily_sessions:
                # Cuenta cuántos intentos tomó resolver esa sesión
                conteo = GameAttempt.objects.filter(
                    session=session,
                    is_correct=True
                ).count()
                # Si no hay intento correcto, no incluir (esa sesión no está “resuelta” aún)
                if conteo > 0:
                    attempts_counts.append(conteo)

            # 2️⃣ Media de intentos (o 0 si no ha resuelto ninguno)
            if attempts_counts:
                avg_attempts = sum(attempts_counts) / len(attempts_counts)
            else:
                avg_attempts = 0

            # 3️⃣ Leer puntos acumulados del usuario en este juego
            elo_entry = GameElo.objects.filter(user=self.user, game=game).first()
            puntos = elo_entry.elo if elo_entry else 0

            stats.append({
                "nombre": game.name,
                "slug": game.slug,
                "media_tiempo": avg_attempts,
                "puntos": puntos,
            })

        # Ordenamos por puntos en orden descendente
        return sorted(stats, key=lambda s: s["puntos"], reverse=True)

    def elo_global(self):
        """
        Promedio ponderado de puntos en TODOS los juegos.
        Return 0 si no hay partidas jugadas.
        """
        records = GameElo.objects.filter(user=self.user)
        total_partidas = sum(r.partidas for r in records)
        if total_partidas == 0:
            return 0

        weighted_sum = sum(r.elo * r.partidas for r in records)
        return weighted_sum / total_partidas

    def ranking_global(self):
        """
        Construye el ranking global de usuarios basado en puntos (“puntos_global”)
        y anexa la media de intentos en daily resueltos.
        """

        User = get_user_model()

        # 1️⃣ Calcular puntos globales para cada usuario (promedio ponderado)
        user_points_qs = (
            GameElo.objects
            .values("user__username", "user_id")
            .annotate(
                weighted_sum=Sum(F("elo") * F("partidas"), output_field=FloatField()),
                total_games=Sum("partidas"),
            )
            .annotate(
                puntos_global=ExpressionWrapper(
                    F("weighted_sum") / F("total_games"),
                    output_field=FloatField()
                )
            )
        )

        # Convertimos a lista de diccionarios para ordenarlo en Python
        rows = []
        for record in user_points_qs:
            username = record["user__username"]
            puntos_g = record["puntos_global"] or 0

            # 2️⃣ Calcular media de intentos “DAILY” de este usuario
            user_obj = User.objects.get(username=username)
            daily_sessions = PlaySession.objects.filter(
                user=user_obj,
                session_type="DAILY"
            )

            attempts_counts = []
            for session in daily_sessions:
                conteo = GameAttempt.objects.filter(
                    session=session,
                    is_correct=True
                ).count()
                if conteo > 0:
                    attempts_counts.append(conteo)

            media = (sum(attempts_counts) / len(attempts_counts)) if attempts_counts else None
            partidas = len(attempts_counts)

            rows.append({
                "username": username,
                "puntos": puntos_g,
                "media": media,
                "partidas": partidas,
            })

        # 3️⃣ Ordenar por “puntos” descendente, luego alfabético
        return sorted(rows, key=lambda x: (-x["puntos"], x["username"]))

    def ranking_per_game(self):
        """
        Para cada juego, devuelve una lista de diccionarios con:
        - username
        - puntos (GameElo.elo)
        - partidas (número de daily resueltos)
        - media (media de intentos en esos daily)
        """
        User = get_user_model()
        out = {}

        for game in self.available_games():
            rows = []
            # 1️⃣ Obtener todos los GameElo para este juego
            for ge in GameElo.objects.filter(game=game).select_related("user"):
                username = ge.user.username
                puntos = ge.elo
                # 2️⃣ Sesiones DAILY resueltas de este usuario en este juego
                daily_sessions = PlaySession.objects.filter(
                    user=ge.user,
                    game=game,
                    session_type="DAILY"
                )

                attempts_counts = []
                for session in daily_sessions:
                    conteo = GameAttempt.objects.filter(
                        session=session,
                        is_correct=True
                    ).count()
                    if conteo > 0:
                        attempts_counts.append(conteo)

                media = (sum(attempts_counts) / len(attempts_counts)) if attempts_counts else None
                partidas = len(attempts_counts)

                rows.append({
                    "username": username,
                    "puntos": puntos,
                    "media": media,
                    "partidas": partidas,
                })

            # 3️⃣ Ordenar por puntos descendente, luego por username
            out[game.slug] = sorted(rows, key=lambda x: (-x["puntos"], x["username"]))

        return out




