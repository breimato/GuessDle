from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0037_backfill_pokemon_normal_stats"),
    ]

    operations = [
        migrations.AddField(
            model_name="playsession",
            name="surrendered",
            field=models.BooleanField(default=False),
        ),
    ]
