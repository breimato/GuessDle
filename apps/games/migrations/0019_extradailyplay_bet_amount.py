# Generated by Django 5.2.1 on 2025-05-30 17:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0018_alter_gameresult_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='extradailyplay',
            name='bet_amount',
            field=models.FloatField(default=0),
        ),
    ]
