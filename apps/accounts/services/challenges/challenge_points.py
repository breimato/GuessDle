def challenge_points_delta_for_user(challenge, user):
    if not challenge.completed:
        return None
    stake_points = float(challenge.stake_points or 0)
    if challenge.winner is None:
        return -stake_points
    if challenge.winner == user:
        return stake_points
    return -stake_points
