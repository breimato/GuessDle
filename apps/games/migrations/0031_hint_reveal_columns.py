from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0030_game_grouped_attributes_delete_gameresult'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='hint_reveal_columns',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Orden de preferencia para pistas de columna. Ej: ["tipo_1", "tipo_2", "generacion"]',
            ),
        ),
        migrations.AddField(
            model_name='playsession',
            name='revealed_hints',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Pistas de columna usadas: [{"attribute": "tipo_1", "value": "Fuego", "at_attempt": 5}]',
            ),
        ),
    ]
