from django.db import migrations


def backfill_pokemon_elo(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMode = apps.get_model("games", "GameMode")
    GameElo = apps.get_model("accounts", "GameElo")

    game = Game.objects.filter(slug="pokemon").first()
    if not game:
        return
    normal = GameMode.objects.filter(game=game, slug="normal").first()
    if not normal:
        return
    GameElo.objects.filter(game=game, mode__isnull=True).update(mode=normal)


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0033_seed_pokemon_modes"),
        ("accounts", "0008_game_modes"),
    ]

    operations = [
        migrations.RunPython(backfill_pokemon_elo, migrations.RunPython.noop),
    ]
