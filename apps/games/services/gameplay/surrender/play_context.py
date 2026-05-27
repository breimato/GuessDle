from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SurrenderPlayContext:
    daily_target: Optional[object] = None
    extra_play: Optional[object] = None
    challenge: Optional[object] = None

    @classmethod
    def exactly_one(cls, *, daily_target=None, extra_play=None, challenge=None):
        active_contexts = [value for value in (daily_target, extra_play, challenge) if value]
        if len(active_contexts) != 1:
            raise ValueError("Must specify exactly one play context.")

        return cls(
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

    @property
    def target_item(self):
        if self.daily_target:
            return self.daily_target.target
        if self.extra_play:
            return self.extra_play.target
        return self.challenge.target

    def session_lookup_kwargs(self):
        return {
            "daily_target": self.daily_target,
            "extra_play": self.extra_play,
            "challenge": self.challenge,
        }
