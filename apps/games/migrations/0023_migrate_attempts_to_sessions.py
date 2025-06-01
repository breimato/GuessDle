from django.db import migrations, models
from django.db import transaction
from django.utils import timezone


def forwards(apps, schema_editor):
    PlaySession      = apps.get_model('games', 'PlaySession')
    GameAttempt      = apps.get_model('games', 'GameAttempt')
    DailyTarget      = apps.get_model('games', 'DailyTarget')
    ExtraDailyPlay   = apps.get_model('games', 'ExtraDailyPlay')
    Challenge        = apps.get_model('accounts', 'Challenge')

    session_cache = {}  # (user_id, game_id, tipo, ref_id) -> session_id

    with transaction.atomic():
        for attempt in (
            GameAttempt.objects
            .select_related('user', 'game', 'daily_target', 'extra_play', 'challenge')
            .iterator(chunk_size=1000)
        ):
            # 1️⃣ Determinar tipo y referencia
            if attempt.daily_target_id:
                tipo = 'DAILY'
                ref  = attempt.daily_target_id
            elif attempt.extra_play_id:
                tipo = 'EXTRA'
                ref  = attempt.extra_play_id
            elif attempt.challenge_id:
                tipo = 'CHALLENGE'
                ref  = attempt.challenge_id
            else:
                continue  # órfano — decidir qué hacer (log, borrar, etc.)

            key = (attempt.user_id, attempt.game_id, tipo, ref)

            # 2️⃣ Crear o reutilizar la PlaySession
            if key not in session_cache:
                session = PlaySession.objects.create(
                    user_id      = attempt.user_id,
                    game_id      = attempt.game_id,
                    session_type = tipo,
                    reference_id = ref,
                    completed_at = attempt.attempted_at or timezone.now()
                )
                session_cache[key] = session.id

            # 3️⃣ Vincular el intento
            attempt.session_id = session_cache[key]
            attempt.save(update_fields=['session'])


def reverse(apps, schema_editor):
    GameAttempt = apps.get_model('games', 'GameAttempt')
    GameAttempt.objects.update(session=None)


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0022_gameattempt_session'),
    ]

    operations = [
        migrations.RunPython(forwards, reverse),
    ]
