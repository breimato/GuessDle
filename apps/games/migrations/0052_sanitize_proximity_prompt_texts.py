from django.db import migrations

from apps.games.constants import ONE_PIECE_GAME_SLUG


def sanitize_proximity_prompts_in_db(apps, schema_editor):
    from apps.games.services.proximity.prompt_text_sanitizer import (
        sanitize_proximity_prompt_text,
    )

    Game = apps.get_model("games", "Game")
    ProximityPrompt = apps.get_model("games", "ProximityPrompt")

    game = Game.objects.filter(slug=ONE_PIECE_GAME_SLUG).first()
    if game is None:
        return

    for prompt in ProximityPrompt.objects.filter(game=game):
        sanitized = sanitize_proximity_prompt_text(prompt.prompt_text)
        if sanitized != prompt.prompt_text:
            prompt.prompt_text = sanitized
            prompt.save(update_fields=["prompt_text"])


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0051_fix_teach_arc_slug"),
    ]

    operations = [
        migrations.RunPython(sanitize_proximity_prompts_in_db, migrations.RunPython.noop),
    ]
