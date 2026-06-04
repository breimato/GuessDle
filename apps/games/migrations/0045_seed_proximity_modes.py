from django.db import migrations

LEAGUE_GAME_SLUGS = ("league-of-legends", "lol")
ONE_PIECE_SLUG = "one-piece"
POKEMON_SLUG = "pokemon"


def _resolve_league_game(Game):
    for slug in LEAGUE_GAME_SLUGS:
        game = Game.objects.filter(slug=slug).first()
        if game:
            return game
    return None


def _max_sort_order(GameMode, game):
    last = GameMode.objects.filter(game=game).order_by("-sort_order").first()
    return (last.sort_order + 1) if last else 0


def seed_proximity_modes(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMode = apps.get_model("games", "GameMode")

    proximity_defaults = {
        "label": "Proximidad",
        "play_type": "proximity",
        "item_filter": {},
        "active": True,
    }

    pokemon = Game.objects.filter(slug=POKEMON_SLUG).first()
    if pokemon:
        GameMode.objects.update_or_create(
            game=pokemon,
            slug="proximidad",
            defaults={**proximity_defaults, "sort_order": _max_sort_order(GameMode, pokemon)},
        )

    league = _resolve_league_game(Game)
    if league:
        GameMode.objects.update_or_create(
            game=league,
            slug="proximidad",
            defaults={**proximity_defaults, "sort_order": _max_sort_order(GameMode, league)},
        )

    one_piece = Game.objects.filter(slug=ONE_PIECE_SLUG).first()
    if one_piece:
        modes = [
            ("normal", "Diario", 0, {}),
            ("proximidad", "Proximidad", 1, {}),
        ]
        for slug, label, sort_order, item_filter in modes:
            play_type = "proximity" if slug == "proximidad" else "wordle"
            GameMode.objects.update_or_create(
                game=one_piece,
                slug=slug,
                defaults={
                    "label": label,
                    "sort_order": sort_order,
                    "play_type": play_type,
                    "item_filter": item_filter,
                    "active": True,
                },
            )


def unseed_proximity_modes(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMode = apps.get_model("games", "GameMode")

    for game in Game.objects.filter(slug__in=[POKEMON_SLUG, ONE_PIECE_SLUG]):
        GameMode.objects.filter(game=game, slug="proximidad").delete()

    league = _resolve_league_game(Game)
    if league:
        GameMode.objects.filter(game=league, slug="proximidad").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0044_proximity_mode"),
    ]

    operations = [
        migrations.RunPython(seed_proximity_modes, unseed_proximity_modes),
    ]
