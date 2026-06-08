from apps.games.services.play_session.play_context import PlayContext
from apps.games.services.play_session.play_kind import PlayKind
from apps.games.models import ExtraDailyPlay, GameAttempt
from apps.games.services.extra.extra_daily_service import ExtraDailyService
from apps.games.services.extra.payout import compute_extra_bet_payout, evaluate_extra_bet_won
from apps.games.services.extra.session import resolve_global_average
from apps.games.services.play_session.play_session_service import PlaySessionService
from apps.accounts.services.wallet.score_service import ScoreService


def resolve_outcome(game, user, play_context: PlayContext) -> dict:
    play_session = PlaySessionService.get_or_create_from_context(user, game, play_context)
    attempts_count = GameAttempt.objects.filter(session=play_session).count()
    handler = _OUTCOME_HANDLERS[play_context.kind]
    return handler(game, user, play_context, attempts_count)


def _update_daily(game, user, play_context: PlayContext, attempts_count: int) -> dict:
    if play_context.mode and play_context.mode.is_emoji:
        return _zero_points_payload(attempts_count)
    score_service = ScoreService(user, game, mode=play_context.mode)
    points_awarded = score_service.add_points_for_attempts(attempts_count)
    return {
        "points_awarded": points_awarded,
        "bet_amount": None,
        "global_average": None,
        "current_attempts": attempts_count,
        "bet_won": None,
    }


def _zero_points_payload(attempts_count: int) -> dict:
    return {
        "points_awarded": 0,
        "bet_amount": None,
        "global_average": None,
        "current_attempts": attempts_count,
        "bet_won": None,
    }


def _update_extra(game, user, play_context: PlayContext, attempts_count: int) -> dict:
    extra_play = ExtraDailyPlay.objects.get(pk=play_context.extra_play.id, user=user)
    score_service = ScoreService(user, game, mode=play_context.mode)
    has_beaten_average = evaluate_extra_bet_won(attempts_count, score_service)
    payout = compute_extra_bet_payout(extra_play.bet_amount, has_beaten_average)

    if payout.credit:
        score_service.score_obj.elo += payout.credit
        score_service.score_obj.save(update_fields=("elo",))

    if not extra_play.completed:
        extra_play.completed = True
        extra_play.save(update_fields=["completed"])

    extra_daily_service = ExtraDailyService(user, game, mode=play_context.mode)

    return {
        "points_awarded": payout.points_awarded,
        "bet_amount": extra_play.bet_amount,
        "net_profit": payout.net_profit,
        "global_average": resolve_global_average(score_service),
        "current_attempts": attempts_count,
        "bet_won": has_beaten_average,
        "max_extras_reached": extra_daily_service.max_reached(),
    }


def _update_challenge(game, user, play_context: PlayContext, attempts_count: int) -> dict:
    return {
        "points_awarded": 0,
        "bet_amount": None,
        "global_average": None,
        "current_attempts": attempts_count,
        "bet_won": None,
    }


_OUTCOME_HANDLERS = {
    PlayKind.DAILY: _update_daily,
    PlayKind.EXTRA: _update_extra,
    PlayKind.CHALLENGE: _update_challenge,
}
