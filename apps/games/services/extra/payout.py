from dataclasses import dataclass

EXTRA_BET_PROFIT_RATIO = 0.5


@dataclass(frozen=True)
class ExtraBetPayout:
    credit: float
    net_profit: float
    points_awarded: float


def evaluate_extra_bet_won(attempts_count: int, score_service) -> bool:
    global_average = score_service.calculate_global_average_of_averages(exclude_user=True)
    if global_average is not None:
        return float(attempts_count) < float(global_average)

    user_average = score_service.calculate_user_average_attempts()
    return user_average is None or float(attempts_count) < float(user_average)


def compute_extra_bet_payout(bet_amount: float, won: bool) -> ExtraBetPayout:
    if not won or bet_amount <= 0:
        return ExtraBetPayout(credit=0.0, net_profit=0.0, points_awarded=0.0)

    net_profit = bet_amount * EXTRA_BET_PROFIT_RATIO
    credit = bet_amount + net_profit
    return ExtraBetPayout(
        credit=credit,
        net_profit=net_profit,
        points_awarded=net_profit,
    )
