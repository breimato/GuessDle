from django.db import migrations

from apps.games.constants import ONE_PIECE_GAME_SLUG

TEACH_NAME = "Marshall D. Teach"
ISLA_DRUM_ARC_SLUG = "isla_drum"
ISLA_DRUM_ARC_LABEL = "Isla Drum"


def fix_teach_arc_slug(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    GameItem = apps.get_model("games", "GameItem")
    ArcCatalog = apps.get_model("games", "ArcCatalog")

    game = Game.objects.filter(slug=ONE_PIECE_GAME_SLUG).first()
    if game is None:
        return

    teach = GameItem.objects.filter(game=game, deleted=False, name=TEACH_NAME).first()
    if teach is None:
        return

    data = dict(teach.data or {})
    data["arco_slug"] = ISLA_DRUM_ARC_SLUG
    data["arco de primera aparición"] = ISLA_DRUM_ARC_LABEL
    teach.data = data
    teach.save(update_fields=["data"])

    ArcCatalog.objects.update_or_create(
        game=game,
        slug=ISLA_DRUM_ARC_SLUG,
        defaults={
            "label": ISLA_DRUM_ARC_LABEL,
            "sort_order": 9,
            "active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0050_backfill_one_piece_normal_stats"),
    ]

    operations = [
        migrations.RunPython(fix_teach_arc_slug, migrations.RunPython.noop),
    ]
