import json
import time
import zipfile
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Descarga sprites de PokeAPI por id nacional y genera un ZIP con archivos {id}.png."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            default="pokemon_radical.json",
            help="Ruta al JSON con campo id por entrada.",
        )
        parser.add_argument(
            "--output",
            default="pokemon_images.zip",
            help="Ruta del ZIP de salida.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.05,
            help="Segundos entre peticiones a PokeAPI.",
        )

    def handle(self, *args, **options):
        json_path = Path(options["json"])
        if not json_path.is_absolute():
            json_path = Path(settings.BASE_DIR) / json_path

        output_path = Path(options["output"])
        if not output_path.is_absolute():
            output_path = Path(settings.BASE_DIR) / output_path

        delay = options["delay"]
        entries = json.loads(json_path.read_text(encoding="utf-8"))
        ids = sorted({int(row["id"]) for row in entries if row.get("id") is not None})

        staging_dir = output_path.parent / f".{output_path.stem}_staging"
        staging_dir.mkdir(parents=True, exist_ok=True)

        session = requests.Session()
        session.headers["User-Agent"] = "GuessDle/1.0 (pokemon image downloader)"

        ok = 0
        errors = []

        for index, pokemon_id in enumerate(ids, start=1):
            dest = staging_dir / f"{pokemon_id}.png"
            if dest.exists() and dest.stat().st_size > 0:
                ok += 1
                continue
            try:
                image_bytes = self._download_image(session, pokemon_id, delay)
                dest.write_bytes(image_bytes)
                ok += 1
            except Exception as exc:
                errors.append((pokemon_id, str(exc)))

            if index % 50 == 0:
                self.stdout.write(f"  {index}/{len(ids)} procesados...")

        if errors:
            report = staging_dir / "_errors.txt"
            report.write_text(
                "\n".join(f"{pid}: {msg}" for pid, msg in errors),
                encoding="utf-8",
            )

        self._build_zip(staging_dir, output_path, ids)
        self.stdout.write(self.style.SUCCESS(f"ZIP: {output_path} ({ok}/{len(ids)} imágenes)"))
        if errors:
            self.stdout.write(self.style.WARNING(f"Errores: {len(errors)} (ver _errors.txt)"))

    def _download_image(self, session, pokemon_id, delay):
        response = session.get(
            f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}",
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        time.sleep(delay)

        url = (
            data.get("sprites", {})
            .get("other", {})
            .get("official-artwork", {})
            .get("front_default")
        ) or data.get("sprites", {}).get("front_default")

        if not url:
            raise ValueError("sin URL de imagen en la respuesta")

        image_response = session.get(url, timeout=30)
        image_response.raise_for_status()
        if not image_response.content:
            raise ValueError("imagen vacía")
        return image_response.content

    def _build_zip(self, staging_dir, output_path, ids):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for pokemon_id in ids:
                file_path = staging_dir / f"{pokemon_id}.png"
                if file_path.exists():
                    archive.write(file_path, arcname=f"{pokemon_id}.png")
