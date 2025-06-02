# apps/games/services/gameplay/challenger_manager.py

from django.shortcuts import redirect
from django.contrib import messages

from apps.accounts.services.score_service import ScoreService
from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.games.models import GameAttempt


class ChallengeManager:
    def __init__(self, request, challenge):
        self.request = request
        self.challenge = challenge
        self.user = request.user

    def accept_if_needed(self):
        """
        Si el usuario es el oponente y aún no había aceptado,
        marca como aceptado.
        """
        if not self.challenge.accepted and self.challenge.opponent == self.user:
            self.challenge.accepted = True
            self.challenge.save()

    def ensure_participant(self):
        """
        Devuelve True si el usuario es chalenger u oponente.
        """
        return self.user in (self.challenge.challenger, self.challenge.opponent)

    def assign_attempts_from_post(self):
        """
        Lee del POST el número de intentos que el usuario reporta.
        Lo guarda en el campo correspondiente (challenger_attempts u opponent_attempts).
        """
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
        """
        Si ambos participantes ya subieron sus intentos y el challenge no está completado:
        - Calcula el ganador
        - Asigna puntos al ganador
        - Marca el challenge como completado
        """
        ca = self.challenge.challenger_attempts
        oa = self.challenge.opponent_attempts

        if ca is not None and oa is not None and not self.challenge.completed:
            self._calculate_winner()
            self.challenge.completed = True
            self.challenge.save()

    def _calculate_winner(self):
        """
        Compara challenger_attempts y opponent_attempts:
         - El que tenga menos intentos, es ganador.
         - Empates no dan puntos y no marcan winner.
        """
        ca = self.challenge.challenger_attempts
        oa = self.challenge.opponent_attempts

        if ca < oa:
            winner, loser = self.challenge.challenger, self.challenge.opponent
        elif oa < ca:
            winner, loser = self.challenge.opponent, self.challenge.challenger
        else:
            # Empate: no se asigna winner ni puntos
            return

        # 1️⃣ Obtenemos la sesión CHALLENGE de cada uno
        session_winner = PlaySessionService.get_or_create(
            winner,
            self.challenge.game,
            challenge=self.challenge
        )
        # (No necesitamos la sesión del perdedor para puntos, pero la creamos por consistencia)
        PlaySessionService.get_or_create(
            loser,
            self.challenge.game,
            challenge=self.challenge
        )

        # 2️⃣ Contamos intentos en la sesión del ganador
        attempts_winner = GameAttempt.objects.filter(session=session_winner).count()

        # 3️⃣ Asignar puntos usando ScoreService
        score_winner = ScoreService(winner, self.challenge.game)
        puntos = score_winner.add_points_for_attempts(attempts_winner)

        # 4️⃣ Guardar ganador en el challenge
        self.challenge.winner = winner
        # No marcamos ningún "elo_exchanged" ya que ya no usamos ese campo
        # Pero si quieres dejar la señal, puedes asignar:
        # self.challenge.elo_exchanged = True
        # (aun cuando semantics no encajen del todo)
