from django.shortcuts import redirect
from django.contrib import messages
from apps.accounts.services.elo import Elo


class ChallengeManager:
    def __init__(self, request, challenge):
        self.request = request
        self.challenge = challenge
        self.user = request.user

    def accept_if_needed(self):
        if not self.challenge.accepted and self.challenge.opponent == self.user:
            self.challenge.accepted = True
            self.challenge.save()

    def ensure_participant(self):
        return self.user in (self.challenge.challenger, self.challenge.opponent)

    def assign_attempts_from_post(self):
        try:
            attempts = int(self.request.POST.get("attempts"))
        except (TypeError, ValueError):
            messages.error(self.request, "Número de intentos inválido.")
            return False

        if self.user == self.challenge.challenger:
            self.challenge.challenger_attempts = attempts
        else:
            self.challenge.opponent_attempts = attempts

        self.challenge.save()
        return True

    def resolve_if_ready(self):
        if (
            self.challenge.challenger_attempts is not None and
            self.challenge.opponent_attempts is not None and
            not self.challenge.completed
        ):
            self._calculate_winner()
            self.challenge.completed = True
            self.challenge.save()

    def _calculate_winner(self):
        ca = self.challenge.challenger_attempts
        oa = self.challenge.opponent_attempts

        if ca < oa:
            winner, loser = self.challenge.challenger, self.challenge.opponent
        elif oa < ca:
            winner, loser = self.challenge.opponent, self.challenge.challenger
        else:
            return  # empate, no hay ganador

        Elo(winner, self.challenge.game).update_vs_opponent(
            result=1,
            opponent_rating=Elo(loser, self.challenge.game).elo_obj.elo
        )
        Elo(loser, self.challenge.game).update_vs_opponent(
            result=0,
            opponent_rating=Elo(winner, self.challenge.game).elo_obj.elo
        )
        self.challenge.winner = winner
        self.challenge.elo_exchanged = True
