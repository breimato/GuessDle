# Generated by Django 5.2.1 on 2025-06-01 18:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0019_extradailyplay_bet_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='extradailyplay',
            name='completed',
            field=models.BooleanField(default=False),
        ),
    ]
