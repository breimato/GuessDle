from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0046_proximity_first_attempt_score"),
    ]

    operations = [
        migrations.AddField(
            model_name="playsession",
            name="proximity_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="playsession",
            name="proximity_timed_out",
            field=models.BooleanField(default=False),
        ),
    ]
