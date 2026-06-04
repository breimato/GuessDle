from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0045_seed_proximity_modes"),
    ]

    operations = [
        migrations.RenameField(
            model_name="playsession",
            old_name="proximity_best_distance",
            new_name="proximity_first_distance",
        ),
        migrations.AddField(
            model_name="playsession",
            name="proximity_score_locked",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
