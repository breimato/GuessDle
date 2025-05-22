from collections import defaultdict, deque
from django.core.management.base import BaseCommand
from django.db.models import Avg
from apps.games.models import GameResult
from apps.accounts.models import GameElo


class Command(BaseCommand):
    """
    Recalcula el Elo por juego.
    • Guarda partidas del primer jugador en una cola.
    • Cuando aparece el segundo jugador, puntúa esas partidas pendientes.
    """

    # ------------- Fórmula Elo -------------
    @staticmethod
    def _expected(r_player, r_opponent):
        return 1 / (1 + 10 ** ((r_opponent - r_player) / 400))

    def _update(self, rating, result, opp_rating, k=32):
        exp = self._expected(rating, opp_rating)
        return rating + k * (result - exp)
    # ---------------------------------------

    def handle(self, *args, **opts):
        self.stdout.write("🧨  Borrando ELOs…")
        GameElo.objects.all().delete()

        # (user_id, game_id) -> dict(elo, games)
        elos = defaultdict(lambda: {"elo": 1200.0, "games": 0})
        # game_id -> deque de partidas pendientes [(user_id, attempts, hist_avg)]
        pending = defaultdict(deque)

        results = (
            GameResult.objects
            .select_related("user", "game")
            .order_by("completed_at")
        )

        for res in results:
            key = (res.user_id, res.game_id)
            cur = elos[key]
            cur["games"] += 1                      # 👍 siempre contamos la partida

            # media histórica previa (sin esta partida)
            prev_avg = (
                GameResult.objects
                .filter(game=res.game, completed_at__lt=res.completed_at)
                .aggregate(avg=Avg("attempts"))["avg"]
            )
            if prev_avg is None:
                # Primera partida absoluta → se apila y se continúa
                pending[res.game_id].append((res.user_id, res.attempts, None))
                continue

            # ---------------- Rival actual ----------------
            other_elos = [
                data["elo"] for (u, g), data in elos.items()
                if g == res.game_id and u != res.user_id and data["games"] > 0
            ]
            if not other_elos:
                # Sigue sin rival real: apilar y continuar
                pending[res.game_id].append((res.user_id, res.attempts, prev_avg))
                continue

            opp_rating = sum(other_elos) / len(other_elos)

            # ------------ Puntuar la partida actual ------------
            result_flag = 1 if res.attempts < prev_avg else 0
            cur["elo"] = self._update(cur["elo"], result_flag, opp_rating)

            # ------------ Procesar pendientes de este juego ------------
            if pending[res.game_id]:
                new_other = [
                    data["elo"] for (u, g), data in elos.items()
                    if g == res.game_id and data["games"] > 0
                ]
                new_opp = sum(new_other) / len(new_other)

                while pending[res.game_id]:
                    uid, att, hist = pending[res.game_id].popleft()
                    k2 = (uid, res.game_id)
                    player = elos[k2]

                    # media histórica que teníamos guardada (si era None, usa prev_avg)
                    base_avg = hist if hist is not None else prev_avg
                    res_flag = 1 if att < base_avg else 0
                    player["elo"] = self._update(player["elo"], res_flag, new_opp)

        # ---------- Persistir en BD ----------
        self.stdout.write("💾 Guardando ELOs…")
        for (uid, gid), data in elos.items():
            GameElo.objects.create(
                user_id=uid,
                game_id=gid,
                elo=data["elo"],
                partidas=data["games"]
            )

        self.stdout.write(self.style.SUCCESS("✅ Recalculo completado: primeras partidas valoradas al aparecer rivales."))
