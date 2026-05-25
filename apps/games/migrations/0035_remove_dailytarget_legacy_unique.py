from django.db import migrations


def drop_legacy_dailytarget_unique(apps, schema_editor):
    table = "games_dailytarget"
    connection = schema_editor.connection

    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute(f"PRAGMA index_list('{table}')")
            for row in cursor.fetchall():
                index_name = row[1]
                cursor.execute(f"PRAGMA index_info('{index_name}')")
                columns = {info[2] for info in cursor.fetchall()}
                if columns == {"game_id", "date", "is_team"}:
                    cursor.execute(f'DROP INDEX IF EXISTS "{index_name}"')
        return

    DailyTarget = apps.get_model("games", "DailyTarget")
    constraint_names = schema_editor._constraint_names(
        table,
        ["game_id", "date", "is_team"],
        unique=True,
    )
    for name in constraint_names:
        if name in ("unique_daily_target_no_mode", "unique_daily_target_with_mode"):
            continue
        schema_editor.execute(
            schema_editor.sql_delete_unique
            % {
                "table": schema_editor.quote_name(table),
                "constraint": schema_editor.quote_name(name),
            }
        )


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0034_backfill_pokemon_elo"),
    ]

    operations = [
        migrations.RunPython(drop_legacy_dailytarget_unique, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name="dailytarget",
                    unique_together=set(),
                ),
            ],
            database_operations=[],
        ),
    ]
