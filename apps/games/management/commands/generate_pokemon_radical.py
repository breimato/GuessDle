import json
import time
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.games.services.catalog.generation_utils import generation_from_national_id

TYPE_ES = {
    "normal": "Normal",
    "fire": "Fuego",
    "water": "Agua",
    "grass": "Planta",
    "electric": "Eléctrico",
    "ice": "Hielo",
    "fighting": "Lucha",
    "poison": "Veneno",
    "ground": "Tierra",
    "flying": "Volador",
    "psychic": "Psíquico",
    "bug": "Bicho",
    "rock": "Roca",
    "ghost": "Fantasma",
    "dragon": "Dragón",
    "dark": "Siniestro",
    "steel": "Acero",
    "fairy": "Hada",
}

COLOR_ES = {
    "black": "Negro",
    "blue": "Azul",
    "brown": "Marrón",
    "gray": "Gris",
    "green": "Verde",
    "pink": "Rosa",
    "purple": "Morado",
    "red": "Rojo",
    "white": "Blanco",
    "yellow": "Amarillo",
}


class Command(BaseCommand):
    help = "Genera pokemon_radical.json desde PokeAPI con las mismas claves que pokemon.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="pokemon_radical.json",
            help="Ruta del JSON de salida (relativa a BASE_DIR por defecto)",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.06,
            help="Segundos entre peticiones a PokeAPI",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"])
        if not output_path.is_absolute():
            output_path = Path(settings.BASE_DIR) / output_path

        delay = options["delay"]
        session = requests.Session()
        session.headers.update({"User-Agent": "GuessDlePokemonRadical/1.0"})

        self.stdout.write("Listando especies desde PokeAPI...")
        species_index = self._fetch_all_species(session, delay)
        self.stdout.write(f"  {len(species_index)} especies encontradas.")

        self.stdout.write("Calculando etapas evolutivas y cacheando especies...")
        species_cache, evolution_stages = self._build_species_cache_and_stages(
            session, species_index, delay
        )

        self.stdout.write("Montando entradas JSON...")
        entries = []
        errors = []

        for idx, species_id in enumerate(sorted(species_index.keys()), start=1):
            name = species_index[species_id]["name"]
            try:
                species = species_cache[species_id]
                pokemon = self._get_default_pokemon(session, species, delay)
                types = [t["type"]["name"] for t in pokemon["types"]]
                tipo1 = TYPE_ES.get(types[0], types[0].capitalize())
                tipo2 = TYPE_ES.get(types[1], "Ninguno") if len(types) > 1 else "Ninguno"
                color_en = species["color"]["name"]
                color = COLOR_ES.get(color_en, color_en.capitalize())

                entries.append(
                    {
                        "nombre": name,
                        "tipo1": tipo1,
                        "tipo2": tipo2,
                        "altura": int(pokemon["height"] * 10),
                        "peso": round(pokemon["weight"] / 10, 1),
                        "etapa de evolucion": evolution_stages.get(species_id, 1),
                        "color": color,
                        "id": species_id,
                        "generacion": generation_from_national_id(species_id),
                    }
                )
            except Exception as exc:
                errors.append((name, str(exc)))

            if idx % 50 == 0:
                self.stdout.write(f"  {idx}/{len(species_index)} procesados...")

        entries.sort(key=lambda row: row["id"])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(entries, handle, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Generado {output_path} con {len(entries)} Pokémon."
        ))
        if errors:
            self.stdout.write(self.style.WARNING(f"Errores ({len(errors)}):"))
            for name, err in errors[:20]:
                self.stdout.write(f"  - {name}: {err}")
            if len(errors) > 20:
                self.stdout.write(f"  ... y {len(errors) - 20} más.")

    def _get_json(self, session, url, delay):
        response = session.get(url, timeout=30)
        response.raise_for_status()
        time.sleep(delay)
        return response.json()

    def _fetch_all_species(self, session, delay):
        species_index = {}
        url = "https://pokeapi.co/api/v2/pokemon-species?limit=100"

        while url:
            payload = self._get_json(session, url, delay)
            for item in payload["results"]:
                species_id = int(item["url"].rstrip("/").split("/")[-1])
                species_index[species_id] = {"name": item["name"]}
            url = payload.get("next")

        return species_index

    def _build_species_cache_and_stages(self, session, species_index, delay):
        species_cache = {}
        stages = {}
        chain_cache = {}

        for species_id in sorted(species_index.keys()):
            species = self._get_json(
                session,
                f"https://pokeapi.co/api/v2/pokemon-species/{species_id}",
                delay,
            )
            species_cache[species_id] = species
            chain_url = species["evolution_chain"]["url"]
            if chain_url not in chain_cache:
                chain = self._get_json(session, chain_url, delay)
                chain_cache[chain_url] = {}
                self._walk_evolution_chain(chain["chain"], 1, chain_cache[chain_url])
            stages.update(chain_cache[chain_url])

        return species_cache, stages

    def _walk_evolution_chain(self, link, depth, stages):
        species_id = int(link["species"]["url"].rstrip("/").split("/")[-1])
        if species_id not in stages or depth < stages[species_id]:
            stages[species_id] = depth
        for child in link.get("evolves_to", []):
            self._walk_evolution_chain(child, depth + 1, stages)

    def _get_default_pokemon(self, session, species, delay):
        varieties = species.get("varieties", [])
        default = next((v for v in varieties if v["is_default"]), varieties[0])
        pokemon_url = default["pokemon"]["url"]
        return self._get_json(session, pokemon_url, delay)
