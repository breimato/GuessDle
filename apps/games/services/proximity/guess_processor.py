from datetime import timedelta

from django.utils import timezone

from apps.games.models import Game, GameMode, ProximityAttempt, ProximityDailyAssignment
from apps.games.services.proximity.answer_resolver import resolve_assignment_answer
from apps.games.services.proximity.filter_service import ProximityFilterService
from apps.games.services.proximity.game_config import TEAM_TIMER_SECONDS
from apps.games.services.proximity.score_service import ProximityScoreService
from apps.games.services.proximity.session_service import ProximitySessionService
from apps.games.services.proximity.timeout_service import ProximityTimeoutService
from apps.games.utils import numeric_feedback


class ProximityGuessProcessor:
    def __init__(self, game: Game, mode: GameMode, user):
        self.game = game
        self.mode = mode
        self.user = user
        self.is_team = ProximitySessionService.is_team_user(user)

    def process(self, request, assignment: ProximityDailyAssignment) -> tuple[bool, dict]:
        session = ProximitySessionService.get_or_create(
            self.user, self.game, self.mode, assignment
        )
        finished, payload = self._reject_if_finished(session)
        if finished:
            return False, payload

        if self.is_team:
            ProximitySessionService.ensure_started(session, is_team=True)
            session.refresh_from_db()
            timeout_service = ProximityTimeoutService(self.game, self.mode, self.user)
            if timeout_service.is_past_deadline(session):
                timeout_service.fail_timed_out(session)
                session.refresh_from_db()
                return False, {"error": "Se acabó el tiempo."}

        raw_guess = request.POST.get("guess", "").strip()
        if not raw_guess:
            return False, {"error": "Debes introducir un número."}
        try:
            guess_value = int(raw_guess)
        except ValueError:
            return False, {"error": "El intento debe ser un número entero."}

        answer = resolve_assignment_answer(self.game, assignment)
        distance = abs(guess_value - answer)
        ProximityAttempt.objects.create(
            session=session,
            guess_value=guess_value,
            distance=distance,
        )

        session.proximity_first_distance = distance
        session.proximity_score_locked = ProximityScoreService.points_for_distance(distance)
        session.save(update_fields=["proximity_first_distance", "proximity_score_locked"])

        points_awarded = ProximityScoreService(
            self.user, self.game, self.mode
        ).apply_completion(session)
        session.refresh_from_db()

        return True, self.build_state(session, assignment, points_awarded=points_awarded)

    def _reject_if_finished(self, session) -> tuple[bool, dict | None]:
        if session.proximity_timed_out:
            return True, {"error": "Se acabó el tiempo."}
        if session.proximity_completed:
            return True, {"error": "La partida ya ha terminado."}
        if session.proximity_attempts.exists():
            return True, {"error": "Solo tienes un intento."}
        return False, None

    def build_state(
        self,
        session,
        assignment: ProximityDailyAssignment,
        *,
        points_awarded: int = 0,
    ) -> dict:
        answer = resolve_assignment_answer(self.game, assignment)
        attempts = []
        for attempt in session.proximity_attempts.order_by("created_at"):
            feedback = numeric_feedback(attempt.guess_value, answer)
            attempts.append(
                {
                    "guess_value": attempt.guess_value,
                    "arrow": feedback["arrow"],
                    "hint": (
                        "Más alto" if feedback["hint"] == "Higher"
                        else "Más bajo" if feedback["hint"] == "Lower"
                        else "¡Exacto!"
                    ),
                    "is_correct": attempt.distance == 0,
                }
            )

        first_attempt = session.proximity_attempts.order_by("created_at").first()
        game_finished = session.proximity_completed or session.proximity_timed_out
        deadline_iso = None
        if self.is_team and session.proximity_started_at and not game_finished:
            deadline = session.proximity_started_at + timedelta(seconds=TEAM_TIMER_SECONDS)
            deadline_iso = deadline.isoformat()

        return {
            "won": bool(first_attempt and first_attempt.distance == 0),
            "can_play": not game_finished,
            "filters_locked": ProximityFilterService(self.game).filter_locked(session),
            "timed_out": session.proximity_timed_out,
            "answer_value": answer if game_finished else None,
            "score_locked": session.proximity_score_locked,
            "first_guess_value": first_attempt.guess_value if first_attempt else None,
            "attempts": attempts,
            "points_awarded": points_awarded,
            "value_unit": self._value_unit(assignment),
            "is_team_play": self.is_team,
            "deadline_iso": deadline_iso,
        }

    def _value_unit(self, assignment: ProximityDailyAssignment) -> str:
        from apps.games.services.proximity.game_config import (
            one_piece_value_unit,
            proximity_game_kind,
        )

        kind = proximity_game_kind(self.game)
        if kind == "pokemon":
            return "nº Pokédex"
        if kind == "lol":
            return "año"
        media = (assignment.filter_config or {}).get("media")
        return one_piece_value_unit(media)
