from django.db import migrations, models
import django.db.models.deletion


def dedupe_daily_targets(apps, schema_editor):
    DailyTarget = apps.get_model("games", "DailyTarget")
    seen = set()
    for row in DailyTarget.objects.order_by("id"):
        key = (row.game_id, row.date, row.is_team)
        if key in seen:
            row.delete()
        else:
            seen.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0031_hint_reveal_columns'),
    ]

    operations = [
        migrations.RunPython(dedupe_daily_targets, migrations.RunPython.noop),
        migrations.CreateModel(
            name='GameMode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField()),
                ('label', models.CharField(max_length=50)),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('item_filter', models.JSONField(blank=True, default=dict)),
                ('active', models.BooleanField(default=True)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modes', to='games.game')),
            ],
            options={
                'ordering': ('sort_order', 'slug'),
                'unique_together': {('game', 'slug')},
            },
        ),
        migrations.AddField(
            model_name='dailytarget',
            name='mode',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='games.gamemode'),
        ),
        migrations.AddField(
            model_name='extradailyplay',
            name='mode',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='games.gamemode'),
        ),
        migrations.AddField(
            model_name='playsession',
            name='mode',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='games.gamemode'),
        ),
        migrations.AddConstraint(
            model_name='dailytarget',
            constraint=models.UniqueConstraint(condition=models.Q(('mode__isnull', True)), fields=('game', 'date', 'is_team'), name='unique_daily_target_no_mode'),
        ),
        migrations.AddConstraint(
            model_name='dailytarget',
            constraint=models.UniqueConstraint(condition=models.Q(('mode__isnull', False)), fields=('game', 'date', 'is_team', 'mode'), name='unique_daily_target_with_mode'),
        ),
    ]
