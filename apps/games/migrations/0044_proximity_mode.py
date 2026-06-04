# Generated manually for proximity mode

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("games", "0043_seed_lol_emoji_mode"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gamemode",
            name="play_type",
            field=models.CharField(
                choices=[
                    ("wordle", "Wordle"),
                    ("rosco", "Rosco"),
                    ("emoji", "Emoji"),
                    ("proximity", "Proximidad"),
                ],
                default="wordle",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="playsession",
            name="proximity_best_distance",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="playsession",
            name="proximity_completed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="playsession",
            name="proximity_filter",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="playsession",
            name="session_type",
            field=models.CharField(
                choices=[
                    ("DAILY", "Daily"),
                    ("EXTRA", "Extra"),
                    ("CHALLENGE", "Challenge"),
                    ("ROSCO", "Rosco"),
                    ("PROXIMITY", "Proximity"),
                ],
                max_length=10,
            ),
        ),
        migrations.CreateModel(
            name="ArcCatalog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField()),
                ("label", models.CharField(max_length=120)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("active", models.BooleanField(default=True)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="arc_catalog", to="games.game")),
            ],
            options={
                "ordering": ("sort_order", "label"),
                "unique_together": {("game", "slug")},
            },
        ),
        migrations.CreateModel(
            name="ProximityPrompt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prompt_text", models.TextField()),
                ("answer_value", models.PositiveIntegerField()),
                ("arcs", models.JSONField(blank=True, default=list)),
                ("kind", models.CharField(blank=True, default="event", max_length=40)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="proximity_prompts", to="games.game")),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="ProximityDailyAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("is_team", models.BooleanField(default=False)),
                ("filter_config", models.JSONField(default=dict)),
                ("answer_value", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="proximity_assignments", to="games.game")),
                ("mode", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="proximity_assignments", to="games.gamemode")),
                ("proximity_prompt", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="daily_assignments", to="games.proximityprompt")),
                ("target_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="proximity_assignments", to="games.gameitem")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="proximity_assignments", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ProximityAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guess_value", models.IntegerField()),
                ("distance", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="proximity_attempts", to="games.playsession")),
            ],
            options={
                "ordering": ("created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="proximitydailyassignment",
            constraint=models.UniqueConstraint(
                fields=("user", "game", "mode", "date", "is_team"),
                name="unique_proximity_daily_assignment",
            ),
        ),
    ]
