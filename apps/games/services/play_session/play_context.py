from dataclasses import dataclass
from typing import Optional

from apps.accounts.models import Challenge
from apps.games.services.play_session.play_kind import PlayKind
from apps.games.models import ExtraDailyPlay


@dataclass(frozen=True)
class PlayContext:
    kind: PlayKind
    daily_target: Optional[object] = None
    extra_play: Optional[ExtraDailyPlay] = None
    challenge: Optional[Challenge] = None

    @classmethod
    def exactly_one(
        cls,
        *,
        daily_target=None,
        extra_play=None,
        challenge=None,
    ) -> "PlayContext":
        if daily_target is not None:
            return cls(PlayKind.DAILY, daily_target=daily_target)
        if extra_play is not None:
            return cls(PlayKind.EXTRA, extra_play=extra_play)
        if challenge is not None:
            return cls(PlayKind.CHALLENGE, challenge=challenge)
        raise ValueError("Must specify exactly one play context.")

    @property
    def target(self):
        bindings = {
            PlayKind.DAILY: lambda: self.daily_target.target,
            PlayKind.EXTRA: lambda: self.extra_play.target,
            PlayKind.CHALLENGE: lambda: self.challenge.target,
        }
        return bindings[self.kind]()

    @property
    def target_item(self):
        return self.target

    @property
    def mode(self):
        bindings = {
            PlayKind.DAILY: lambda: self.daily_target.mode,
            PlayKind.EXTRA: lambda: self.extra_play.mode,
            PlayKind.CHALLENGE: lambda: self.challenge.mode,
        }
        return bindings[self.kind]()

    def session_lookup_kwargs(self) -> dict:
        return {
            "daily_target": self.daily_target,
            "extra_play": self.extra_play,
            "challenge": self.challenge,
        }
