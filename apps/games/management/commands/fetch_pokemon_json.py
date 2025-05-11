import requests
import json
import time

from django.core.management.base import BaseCommand

POKEMON_LIMIT = 386
BASE_API = "https://pokeapi.co/api/v2"
OUTPUT_FILE = "pokemon.json"


def fetch_all_pokemon(limit=POKEMON_LIMIT):
    url = f"{BASE_API}/pokemon?limit={limit}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["results"]


def fetch_pokemon_details(name_or_id):
    pokemon_url = f"{BASE_API}/pokemon/{name_or_id}"
    species_url = f"{BASE_API}/pokemon-species/{name_or_id}"

    pokemon_data = requests.get(pokemon_url).json()
    species_data = requests.get(species_url).json()

    types = [t["type"]["name"] for t in pokemon_data["types"]]
    type1 = types[0] if len(types) > 0 else None
    type2 = types[1] if len(types) > 1 else None

    return {
        "nombre": pokemon_data["name"],
        "tipo1": type1,
        "tipo2": type2,
        "altura": pokemon_data["height"],
        "peso": pokemon_data["weight"],
        "numero": pokemon_data["id"],
        "color": species_data.get("color", {}).get("name"),
        "etapa de evolucion": species_data.get("order")
    }


class Command(BaseCommand):
    help = "Descarga datos de los Pokémon hasta la Gen III y los guarda en un JSON local"

    def handle(self, *args, **options):
        self.stdout.write("🔄 Comenzando descarga de Pokémon...")
        all_pokemon = fetch_all_pokemon()
        final_data = []

        for idx, pokemon in enumerate(all_pokemon, start=1):
            try:
                self.stdout.write(f"[{idx}/{POKEMON_LIMIT}] Fetching {pokemon['name']}...")
                data = fetch_pokemon_details(pokemon["name"])
                final_data.append(data)
                time.sleep(0.5)  # Respeta la API pública
            except Exception as e:
                self.stderr.write(f"⚠️ Error con {pokemon['name']}: {e}")
                continue

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Datos guardados en '{OUTPUT_FILE}' ({len(final_data)} pokémones)"
        ))
