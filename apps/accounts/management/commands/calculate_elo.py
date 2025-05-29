from collections import defaultdict, deque
from django.core.management.base import BaseCommand
from django.db.models import Avg
from apps.games.models import GameResult
from apps.accounts.models import GameElo, Challenge


class Command(BaseCommand):
    """
    Recalcula el Elo por juego.
    • Guarda partidas del primer jugador en una cola.
    • Cuando aparece el segundo jugador, puntúa esas partidas pendientes.
    • Ahora también se incluyen los Challenges.
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
            cur["games"] += 1

            prev_avg = (
                GameResult.objects
                .filter(game=res.game, completed_at__lt=res.completed_at)
                .aggregate(avg=Avg("attempts"))["avg"]
            )
            if prev_avg is None:
                pending[res.game_id].append((res.user_id, res.attempts, None))
                continue

            other_elos = [
                data["elo"] for (u, g), data in elos.items()
                if g == res.game_id and u != res.user_id and data["games"] > 0
            ]
            if not other_elos:
                pending[res.game_id].append((res.user_id, res.attempts, prev_avg))
                continue

            opp_rating = sum(other_elos) / len(other_elos)
            result_flag = 1 if res.attempts < prev_avg else 0
            cur["elo"] = self._update(cur["elo"], result_flag, opp_rating)

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

                    base_avg = hist if hist is not None else prev_avg
                    res_flag = 1 if att < base_avg else 0
                    player["elo"] = self._update(player["elo"], res_flag, new_opp)

        # 🔥 Añadir ELO de Challenges
        self.stdout.write("🎯 Procesando Challenges…")

        challenges = Challenge.objects.filter(
            accepted=True,
            completed=True,
            winner__isnull=False,
            challenger_attempts__isnull=False,
            opponent_attempts__isnull=False
        ).select_related('challenger', 'opponent', 'game')

        for ch in challenges:
            game_id = ch.game_id

            c_key = (ch.challenger_id, game_id)
            o_key = (ch.opponent_id, game_id)

            c_elo = elos[c_key]
            o_elo = elos[o_key]

            # Incrementar partidas
            c_elo["games"] += 1
            o_elo["games"] += 1

            r1 = c_elo["elo"]
            r2 = o_elo["elo"]

            expected_c = self._expected(r1, r2)
            expected_o = self._expected(r2, r1)

            winner_id = ch.winner_id
            result_c = 1 if ch.challenger_id == winner_id else 0
            result_o = 1 if ch.opponent_id == winner_id else 0

            c_elo["elo"] = self._update(r1, result_c, r2)
            o_elo["elo"] = self._update(r2, result_o, r1)

        # ---------- Persistir en BD ----------
        self.stdout.write("💾 Guardando ELOs…")
        for (uid, gid), data in elos.items():
            GameElo.objects.create(
                user_id=uid,
                game_id=gid,
                elo=data["elo"],
                partidas=data["games"]
            )

        self.stdout.write(self.style.SUCCESS("✅ Recalculo completado: GameResults y Challenges valorados."))
