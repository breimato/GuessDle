from apps.games.models import GameAttempt


class SurrenderSessionEligibilityChecker:
    @staticmethod
    def ensure_eligible(play_session):
        if play_session.surrendered:
            raise ValueError("Ya te has rendido en esta partida.")

        has_correct_attempt = GameAttempt.objects.filter(
            session=play_session,
            is_correct=True,
        ).exists()
        if has_correct_attempt:
            raise ValueError("Ya has ganado esta partida.")
