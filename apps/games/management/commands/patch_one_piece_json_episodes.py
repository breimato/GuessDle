import json

from django.core.management.base import BaseCommand, CommandError

from apps.games.models import Game
from apps.games.services.catalog.one_piece_episode_utils import enrich_one_piece_episode
class Command(BaseCommand):
    help = "Añade el campo episodio a cada personaje del JSON fuente de One Piece."

    def add_arguments(self, parser):
        parser.add_argument("--game-slug", default="one-piece")
        parser.add_argument(
            "--json-path",
            default="",
            help="Ruta al JSON (por defecto el json_file del juego).",
        )
        parser.add_argument(
            "--sync-db",
            action="store_true",
            help="Tras parchear el JSON, sincroniza GameItem desde admin logic.",
        )

    def handle(self, *args, **options):
        game = Game.objects.filter(slug=options["game_slug"]).first()
        if not game:
            raise CommandError(f"No existe el juego '{options['game_slug']}'.")

        json_path = options["json_path"] or (game.json_file.path if game.json_file else "")
        if not json_path:
            raise CommandError("El juego no tiene json_file ni se indicó --json-path.")

        with open(json_path, encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise CommandError("Se esperaba una lista de personajes.")

        patched = 0
        missing = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            chapter = entry.get("capítulo") or entry.get("capitulo")
            if chapter is None:
                continue
            enriched = enrich_one_piece_episode(entry)
            episode = enriched.get("episodio")
            if episode is None:
                missing.append((entry.get("nombre", "?"), int(chapter)))
                continue
            if entry.get("episodio") != episode:
                entry["episodio"] = episode
                patched += 1
            entry.pop("episodio de primera aparición", None)

        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        mapping = dict(game.field_mapping or {})
        if "episodio" not in mapping:
            mapping["episodio"] = "episodio"
            game.field_mapping = mapping
        attributes = list(game.attributes or [])
        if "episodio" not in attributes:
            attributes.append("episodio")
            game.attributes = attributes
        game.save(update_fields=["field_mapping", "attributes"])

        self.stdout.write(
            self.style.SUCCESS(
                f"JSON actualizado: {patched} personajes con episodio nuevo o corregido."
            )
        )
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    f"Sin episodio en mapa ({len(missing)}): {missing[:5]}..."
                )
            )

        if options["sync_db"]:
            from django.core.management import call_command

            call_command("backfill_one_piece_episodes", game_slug=options["game_slug"])
