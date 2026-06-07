from django.db import migrations

from apps.games.constants import ONE_PIECE_GAME_SLUG


def backfill_one_piece_normal_stats(apps, schema_editor):
    from apps.games.services.pokemon_normal_backfill import backfill_legacy_mode_to_normal

    backfill_legacy_mode_to_normal(game_slug=ONE_PIECE_GAME_SLUG, mode_slug="normal")


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0049_standardize_daily_mode_labels"),
    ]

    operations = [
        migrations.RunPython(backfill_one_piece_normal_stats, migrations.RunPython.noop),
    ]
