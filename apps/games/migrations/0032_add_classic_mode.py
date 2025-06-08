from django.db import migrations

def add_classic_mode(apps, schema_editor):
    Game = apps.get_model('games', 'Game')
    GameMode = apps.get_model('games', 'GameMode')
    for game in Game.objects.all():
        GameMode.objects.get_or_create(
            game=game,
            slug='classic',
            defaults={'name': 'Clásico', 'description': 'Modo Wordle clásico'}
        )

class Migration(migrations.Migration):

    dependencies = [
        ('games', '0031_gamemode_gameitemmodedata'),
    ]

    operations = [
        migrations.RunPython(add_classic_mode, migrations.RunPython.noop),
    ]
