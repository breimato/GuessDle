from django.db import migrations

from apps.games.constants import DAILY_WORDLE_MODE_LABEL, is_pokemon_game


def standardize_daily_mode_labels(apps, schema_editor):
    GameMode = apps.get_model("games", "GameMode")

    for mode in GameMode.objects.filter(
        slug="normal",
        play_type="wordle",
    ).select_related("game"):
        if is_pokemon_game(mode.game.slug):
            continue
        if mode.label != DAILY_WORDLE_MODE_LABEL:
            mode.label = DAILY_WORDLE_MODE_LABEL
            mode.save(update_fields=["label"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0048_proximity_prompt_episode"),
    ]

    operations = [
        migrations.RunPython(standardize_daily_mode_labels, noop_reverse),
    ]
