from django.db import migrations

def assign_classic_mode(apps, schema_editor):
    Game = apps.get_model('games', 'Game')
    GameMode = apps.get_model('games', 'GameMode')
    PlaySession = apps.get_model('games', 'PlaySession')
    GameAttempt = apps.get_model('games', 'GameAttempt')

    for session in PlaySession.objects.filter(mode__isnull=True):
        classic_mode = GameMode.objects.get(game=session.game, slug='classic')
        session.mode = classic_mode
        session.save()

    # Si GameAttempt tiene mode, también lo rellenas
    for attempt in GameAttempt.objects.filter(mode__isnull=True):
        session = getattr(attempt, "session", None)
        if session is None or session.mode is None:
            continue  # Salta los intentos sin sesión válida o sin modo
        attempt.mode = session.mode
        attempt.save()


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0033_gameattempt_mode_playsession_mode'),
    ]

    operations = [
        migrations.RunPython(assign_classic_mode, migrations.RunPython.noop),
    ]
