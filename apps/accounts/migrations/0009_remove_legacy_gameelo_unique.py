from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_game_modes"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="gameelo",
            unique_together=set(),
        ),
    ]
