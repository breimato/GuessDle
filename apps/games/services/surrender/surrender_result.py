from dataclasses import dataclass, field


@dataclass(frozen=True)
class SurrenderResult:
    target_name: str
    points_data: dict = field(default_factory=dict)
    challenge_data: dict | None = None
