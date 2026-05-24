"""Column hint reveal logic (every N attempts)."""

from typing import Any, Dict, List, Set

from apps.games.attempts import build_attempts
from apps.games.models import Game, GameAttempt, GameItem, PlaySession

HINT_INTERVAL = 5


def _attribute_label(attribute: str) -> str:
    """Display label for an attribute key (underscores → spaces, keep accents)."""
    return attribute.replace("_", " ")


class HintRevealService:
    """Manages earned hint slots and column reveals for a play session."""

    def __init__(self, session: PlaySession, game: Game, target: GameItem):
        self.session = session
        self.game = game
        self.target = target

    def get_hint_state(self) -> Dict[str, Any]:
        """Return current hint availability and revealed columns."""

        if not self.game.hint_reveal_columns:
            return self._empty_state()

        attempt_count = GameAttempt.objects.filter(session=self.session).count()
        revealed = list(self.session.revealed_hints or [])
        known = self._known_attributes()
        revealed_attrs = {entry["attribute"] for entry in revealed}
        slots_earned = attempt_count // HINT_INTERVAL
        slots_used = len(revealed)
        slots_pending = max(0, slots_earned - slots_used)
        eligible = self._eligible_columns(revealed_attrs, known)
        suggested = self._suggested_attribute(eligible)
        pickable = []
        if slots_pending > 0 and suggested:
            pickable = [{
                "attribute": suggested,
                "label": _attribute_label(suggested),
            }]

        return {
            "enabled": True,
            "slots_earned": slots_earned,
            "slots_used": slots_used,
            "slots_pending": slots_pending,
            "eligible_columns": pickable,
            "suggested_attribute": suggested,
            "revealed_hints": revealed,
        }

    def reveal(self, attribute: str) -> Dict[str, Any]:
        """Reveal the target value for the given attribute."""

        state = self.get_hint_state()
        if state["slots_pending"] <= 0:
            raise ValueError("No hay pistas disponibles.")
        if attribute not in self.game.hint_reveal_columns:
            raise ValueError("Columna no permitida para pistas.")
        if any(entry["attribute"] == attribute for entry in state["revealed_hints"]):
            raise ValueError("Esa columna ya fue revelada.")

        known = self._known_attributes()
        if attribute in known:
            raise ValueError("Esa columna ya la conoces por tus intentos.")

        attempt_count = GameAttempt.objects.filter(session=self.session).count()
        value = self.target.data.get(attribute) or self.game.defaults.get(attribute)
        revealed = list(self.session.revealed_hints or [])
        revealed.append({
            "attribute": attribute,
            "label": _attribute_label(attribute),
            "value": value,
            "at_attempt": attempt_count,
        })
        self.session.revealed_hints = revealed
        self.session.save(update_fields=["revealed_hints"])
        return self.get_hint_state()

    def _known_attributes(self) -> Set[str]:
        """Attributes where the player already got a correct match on a guess."""

        attempts_query = GameAttempt.objects.filter(session=self.session).order_by("attempted_at")
        guesses = [attempt.guess for attempt in attempts_query]
        if not guesses:
            return set()

        known: Set[str] = set()
        built = build_attempts(self.game, guesses, self.target)
        for attempt in built:
            for fb in attempt["feedback"]:
                if fb.get("correct"):
                    known.add(fb["attribute"])
        return known

    def _eligible_columns(
        self,
        revealed_attrs: Set[str],
        known: Set[str],
    ) -> List[Dict[str, str]]:
        excluded = revealed_attrs | known
        eligible = []
        for attribute in self.game.hint_reveal_columns:
            if attribute in excluded:
                continue
            eligible.append({
                "attribute": attribute,
                "label": _attribute_label(attribute),
            })
        return eligible

    def _suggested_attribute(self, eligible: List[Dict[str, str]]) -> str | None:
        if not eligible:
            return None
        eligible_attrs = {col["attribute"] for col in eligible}
        for attribute in self.game.hint_reveal_columns:
            if attribute in eligible_attrs:
                return attribute
        return eligible[0]["attribute"]

    def _empty_state(self) -> Dict[str, Any]:
        return {
            "enabled": False,
            "slots_earned": 0,
            "slots_used": 0,
            "slots_pending": 0,
            "eligible_columns": [],
            "suggested_attribute": None,
            "revealed_hints": [],
        }
