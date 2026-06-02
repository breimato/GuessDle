from django.db import migrations


def seed_lol_modes(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMode = apps.get_model("games", "GameMode")
    GameElo = apps.get_model("accounts", "GameElo")
    PlaySession = apps.get_model("games", "PlaySession")
    DailyTarget = apps.get_model("games", "DailyTarget")
    ExtraDailyPlay = apps.get_model("games", "ExtraDailyPlay")
    Challenge = apps.get_model("accounts", "Challenge")

    game = Game.objects.filter(slug="lol").first()
    if not game:
        return

    normal_mode, _ = GameMode.objects.update_or_create(
        game=game,
        slug="normal",
        defaults={
            "label": "Diario",
            "play_type": "wordle",
            "sort_order": 0,
            "item_filter": {},
            "active": True,
        },
    )
    GameMode.objects.update_or_create(
        game=game,
        slug="pasapalabra",
        defaults={
            "label": "Pasapalabra",
            "play_type": "rosco",
            "sort_order": 1,
            "item_filter": {},
            "active": True,
        },
    )

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
        duplicate = DailyTarget.objects.filter(
            game=game,
            date=legacy_target.date,
            is_team=legacy_target.is_team,
            mode=normal_mode,
        ).exclude(pk=legacy_target.pk).first()
        if duplicate:
            legacy_target.delete()
        else:
            legacy_target.mode = normal_mode
            legacy_target.save(update_fields=["mode"])

    ExtraDailyPlay.objects.filter(game=game, mode__isnull=True).update(mode=normal_mode)
    Challenge.objects.filter(game=game, mode__isnull=True).update(mode=normal_mode)


def unseed_lol_modes(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMode = apps.get_model("games", "GameMode")
    game = Game.objects.filter(slug="lol").first()
    if game:
        GameMode.objects.filter(game=game, slug="normal").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_challenge_stake_points_and_settled"),
        ("games", "0039_rosco_pasapalabra"),
    ]

    operations = [
        migrations.RunPython(seed_lol_modes, unseed_lol_modes),
    ]
