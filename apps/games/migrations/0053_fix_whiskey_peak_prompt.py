from django.db import migrations

from apps.games.constants import ONE_PIECE_GAME_SLUG

OLD_PROMPT = "Zoro entrena con los Sombrero de Paja"
NEW_PROMPT = (
    "Zoro derrota solo a los agentes de Baroque Works mientras la tripulación duerme"
)


def fix_whiskey_peak_prompt(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    ProximityPrompt = apps.get_model("games", "ProximityPrompt")

    game = Game.objects.filter(slug=ONE_PIECE_GAME_SLUG).first()
    if game is None:
        return

    updated = ProximityPrompt.objects.filter(
        game=game,
        prompt_text=OLD_PROMPT,
        answer_value=115,
    ).update(prompt_text=NEW_PROMPT)
    if updated:
        return

    ProximityPrompt.objects.filter(
        game=game,
        answer_value=115,
        arcs__contains=["whiskey_peak"],
    ).update(prompt_text=NEW_PROMPT)


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0052_sanitize_proximity_prompt_texts"),
    ]

    operations = [
        migrations.RunPython(fix_whiskey_peak_prompt, migrations.RunPython.noop),
    ]
