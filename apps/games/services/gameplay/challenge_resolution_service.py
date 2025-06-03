from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.games.services.gameplay.result_updater import ResultUpdater
from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.accounts.services.score_service import ScoreService
from apps.games.models import GameAttempt

class ChallengeResolutionService:
    """
    Orquesta la resolución de un challenge: decide winner/empate,
    asigna puntos (base y bonus), y deja todo marcado como asignado.
    """
    def __init__(self, challenge, acting_user=None):
        self.challenge = challenge
        self.acting_user = acting_user or challenge.challenger

    def resolve_and_assign_points(self):
        # 1️⃣ Resolver el reto si falta (marca winner, completed)
        manager = ChallengeManager(user=self.acting_user, challenge=self.challenge)
        manager.calculate_winner()

        # 2️⃣ No hacemos nada si no está completado o ya tiene puntos asignados
        if not self.challenge.completed or self.challenge.points_assigned:
            return {"status": "already-resolved"}

        # 3️⃣ Empate: ambos reciben puntos base
        if self.challenge.winner is None:
            ResultUpdater(self.challenge.game, self.acting_user).update_for_game(challenge=self.challenge)
            self.challenge.points_assigned = True
            self.challenge.save(update_fields=["points_assigned"])
            return {
                "status": "tie",
                "users": manager.get_tied_users(),
            }

        # 4️⃣ Hay ganador: perdedor base, ganador base+bonus
        winner = self.challenge.winner
        loser = self.challenge.challenger if winner == self.challenge.opponent else self.challenge.opponent

        # Perdedor
        session_loser = PlaySessionService.get_or_create(
            loser,
            self.challenge.game,
            challenge=self.challenge
        )
        loser_tries = GameAttempt.objects.filter(session=session_loser).count()
        svc_loser = ScoreService(loser, self.challenge.game)
        svc_loser.add_points_for_attempts(loser_tries)

        # Ganador
        ResultUpdater(self.challenge.game, winner).update_for_game(challenge=self.challenge)

        self.challenge.points_assigned = True
        self.challenge.save(update_fields=["points_assigned"])

        return {
            "status": "winner",
            "winner": winner,
            "loser": loser,
        }

