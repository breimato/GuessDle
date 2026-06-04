from django.db.models import Q

from apps.games.models import Game, GameMode, GameModePlayType

RANKING_PLAY_TYPES = (GameModePlayType.WORDLE,)


def is_ranking_mode(mode: GameMode) -> bool:
    return mode.play_type in RANKING_PLAY_TYPES


def ranking_modes_for_game(game: Game) -> list[GameMode]:
    return list(
        game.modes.filter(active=True, play_type__in=RANKING_PLAY_TYPES).order_by(
            "sort_order", "slug"
        )
    )


def ranking_elo_filter_q(*, prefix: str = "") -> Q:
    field = f"{prefix}__" if prefix else ""
    return Q(**{f"{field}mode__isnull": True}) | Q(
        **{f"{field}mode__play_type__in": RANKING_PLAY_TYPES}
    )


def ranking_session_filter_q(*, prefix: str = "") -> Q:
    field = f"{prefix}__" if prefix else ""
    return Q(**{f"{field}mode__isnull": True}) | Q(
        **{f"{field}mode__play_type__in": RANKING_PLAY_TYPES}
    )
