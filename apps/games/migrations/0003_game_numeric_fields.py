# Generated by Django 5.2.1 on 2025-05-11 13:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0002_gameitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='numeric_fields',
            field=models.JSONField(blank=True, default=list, help_text='Atributos que deben compararse como números'),
        ),
    ]
