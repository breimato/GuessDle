from django.db import migrations


def seed_pokemon_modes(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMode = apps.get_model("games", "GameMode")
    game = Game.objects.filter(slug="pokemon").first()
    if not game:
        return
    modes = [
        ("normal", "Normal", 0, {"generacion__lte": 3}),
        ("dificil", "Difícil", 1, {"generacion__lte": 5}),
        ("radical", "Radical", 2, {}),
    ]
    for slug, label, sort_order, item_filter in modes:
        GameMode.objects.update_or_create(
            game=game,
            slug=slug,
            defaults={
                "label": label,
                "sort_order": sort_order,
                "item_filter": item_filter,
                "active": True,
            },
        )


def unseed_pokemon_modes(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameMode = apps.get_model("games", "GameMode")
    game = Game.objects.filter(slug="pokemon").first()
    if game:
        GameMode.objects.filter(game=game).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0032_game_modes"),
    ]

    operations = [
        migrations.RunPython(seed_pokemon_modes, unseed_pokemon_modes),
    ]
