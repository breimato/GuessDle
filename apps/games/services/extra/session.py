from apps.accounts.services.wallet.score_service import ScoreService


def resolve_global_average(score_service: ScoreService) -> float | None:
    global_average = score_service.calculate_global_average_of_averages(exclude_user=True)
    if global_average is not None:
        return global_average
    return score_service.calculate_user_average_attempts()


def build_extra_bet_tracking_payload(extra_play, attempts_count: int) -> dict:
    score_service = ScoreService(extra_play.user, extra_play.game, mode=extra_play.mode)
    global_average = resolve_global_average(score_service)

    return {
        "points_awarded": 0,
        "bet_amount": extra_play.bet_amount,
        "net_profit": 0,
        "global_average": global_average,
        "current_attempts": attempts_count,
        "bet_won": False,
    }


def mark_extra_play_lost_if_over_average(extra_play, attempts_count: int) -> dict:
    score_service = ScoreService(extra_play.user, extra_play.game, mode=extra_play.mode)
    global_average = resolve_global_average(score_service)

    if (
        global_average is not None
        and float(attempts_count) >= float(global_average)
        and not extra_play.completed
    ):
        extra_play.completed = True
        extra_play.save(update_fields=["completed"])

    return build_extra_bet_tracking_payload(extra_play, attempts_count)
