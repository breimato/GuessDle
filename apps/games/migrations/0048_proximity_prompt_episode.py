from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0047_proximity_team_timer"),
    ]

    operations = [
        migrations.AddField(
            model_name="proximityprompt",
            name="answer_episode",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
