from django.db import migrations


def backfill_pokemon_normal_stats(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMode = apps.get_model("games", "GameMode")
    GameElo = apps.get_model("accounts", "GameElo")
    PlaySession = apps.get_model("games", "PlaySession")
    DailyTarget = apps.get_model("games", "DailyTarget")
    ExtraDailyPlay = apps.get_model("games", "ExtraDailyPlay")
    Challenge = apps.get_model("accounts", "Challenge")

    game = Game.objects.filter(slug="pokemon").first()
    if not game:
        return

    normal_mode = GameMode.objects.filter(game=game, slug="normal").first()
    if not normal_mode:
        return

    legacy_elo_rows = list(GameElo.objects.filter(game=game, mode__isnull=True))
    for legacy_row in legacy_elo_rows:
        normal_row = GameElo.objects.filter(
            game=game,
            mode=normal_mode,
            user_id=legacy_row.user_id,
        ).first()
        if normal_row:
            normal_row.elo += legacy_row.elo
            normal_row.partidas += legacy_row.partidas
            normal_row.save(update_fields=["elo", "partidas"])
            legacy_row.delete()
        else:
            legacy_row.mode = normal_mode
            legacy_row.save(update_fields=["mode"])

    PlaySession.objects.filter(game=game, mode__isnull=True).update(mode=normal_mode)

    for legacy_target in DailyTarget.objects.filter(game=game, mode__isnull=True):
        duplicate_normal_target = DailyTarget.objects.filter(
            game=game,
            date=legacy_target.date,
            is_team=legacy_target.is_team,
            mode=normal_mode,
        ).exclude(pk=legacy_target.pk).first()
        if duplicate_normal_target:
            legacy_target.delete()
        else:
            legacy_target.mode = normal_mode
            legacy_target.save(update_fields=["mode"])

    ExtraDailyPlay.objects.filter(game=game, mode__isnull=True).update(mode=normal_mode)
    Challenge.objects.filter(game=game, mode__isnull=True).update(mode=normal_mode)


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0036_gamemode_background"),
        ("accounts", "0010_notification"),
    ]

    operations = [
        migrations.RunPython(backfill_pokemon_normal_stats, migrations.RunPython.noop),
    ]
