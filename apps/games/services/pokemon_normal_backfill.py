from apps.accounts.models import Challenge, GameElo
from apps.games.models import DailyTarget, ExtraDailyPlay, Game, GameMode, PlaySession


def backfill_legacy_mode_to_normal(game_slug="pokemon", mode_slug="normal"):
    game = Game.objects.filter(slug=game_slug).first()
    if not game:
        return {"game_found": False}

    normal_mode = GameMode.objects.filter(game=game, slug=mode_slug).first()
    if not normal_mode:
        return {"game_found": True, "mode_found": False}

    summary = {
        "game_found": True,
        "mode_found": True,
        "game_elo_merged": 0,
        "game_elo_updated": 0,
        "play_sessions": 0,
        "daily_targets_updated": 0,
        "daily_targets_removed": 0,
        "extra_daily_plays": 0,
        "challenges": 0,
    }

    legacy_elo_rows = list(GameElo.objects.filter(game=game, mode__isnull=True))
    for legacy_row in legacy_elo_rows:
        normal_row = GameElo.objects.filter(
            game=game,
            mode=normal_mode,
            user=legacy_row.user,
        ).first()
        if normal_row:
            normal_row.elo += legacy_row.elo
            normal_row.partidas += legacy_row.partidas
            normal_row.save(update_fields=["elo", "partidas"])
            legacy_row.delete()
            summary["game_elo_merged"] += 1
        else:
            legacy_row.mode = normal_mode
            legacy_row.save(update_fields=["mode"])
            summary["game_elo_updated"] += 1

    summary["play_sessions"] = PlaySession.objects.filter(
        game=game,
        mode__isnull=True,
    ).update(mode=normal_mode)

    legacy_daily_targets = DailyTarget.objects.filter(game=game, mode__isnull=True)
    for legacy_target in legacy_daily_targets:
        duplicate_normal_target = DailyTarget.objects.filter(
            game=game,
            date=legacy_target.date,
            is_team=legacy_target.is_team,
            mode=normal_mode,
        ).exclude(pk=legacy_target.pk).first()
        if duplicate_normal_target:
            legacy_target.delete()
            summary["daily_targets_removed"] += 1
        else:
            legacy_target.mode = normal_mode
            legacy_target.save(update_fields=["mode"])
            summary["daily_targets_updated"] += 1

    summary["extra_daily_plays"] = ExtraDailyPlay.objects.filter(
        game=game,
        mode__isnull=True,
    ).update(mode=normal_mode)

    summary["challenges"] = Challenge.objects.filter(
        game=game,
        mode__isnull=True,
    ).update(mode=normal_mode)

    return summary


backfill_pokemon_normal_mode = backfill_legacy_mode_to_normal
