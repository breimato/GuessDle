from django.db import migrations

def seed_scoring_rules(apps, schema_editor):
    ScoringRule = apps.get_model('games', 'ScoringRule')

    # Reglas de puntuación globales (game=None)
    reglas = [
        (1, 100),
        (2, 75),
        (3, 50),
        (4, 40),
        (5, 30),
        (6, 20),
        (7, 10),
    ]

    for intento, puntos in reglas:
        ScoringRule.objects.update_or_create(
            game=None,
            attempt_no=intento,
            defaults={"points": puntos},
        )

class Migration(migrations.Migration):

    dependencies = [
        ('games', '0024_remove_gameattempt_challenge_and_more'),

    ]

    operations = [
        migrations.RunPython(seed_scoring_rules, migrations.RunPython.noop),
    ]
