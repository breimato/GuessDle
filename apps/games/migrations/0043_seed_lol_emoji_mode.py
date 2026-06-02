from django.db import migrations

LEAGUE_GAME_SLUGS = ("league-of-legends", "lol")


def _resolve_league_game(Game):
    for slug in LEAGUE_GAME_SLUGS:
        game = Game.objects.filter(slug=slug).first()
        if game:
            return game
    return None


def seed_emoji_mode(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMode = apps.get_model("games", "GameMode")

    game = _resolve_league_game(Game)
    if not game:
        return

    GameMode.objects.update_or_create(
        game=game,
        slug="emojis",
        defaults={
            "label": "Emojis",
            "play_type": "emoji",
            "sort_order": 2,
            "item_filter": {},
            "active": True,
        },
    )


def unseed_emoji_mode(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMode = apps.get_model("games", "GameMode")
    game = _resolve_league_game(Game)
    if game:
        GameMode.objects.filter(game=game, slug="emojis").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0042_emoji_mode"),
    ]

    operations = [
        migrations.RunPython(seed_emoji_mode, unseed_emoji_mode),
    ]
