import json
from pathlib import Path

from django.db import migrations

from apps.games.constants import ONE_PIECE_GAME_SLUG

PROMPTS_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "one_piece" / "proximity_prompts.json"
)

PROMPT_RENAMES = [
    (
        "Nami pide ayuda a Luffy tras la derrota de Arlong",
        "Nami pide ayuda a Luffy contra Arlong",
        81,
        37,
        ["arlong_park"],
        "event",
    ),
    (
        "Luffy destruye el mapa",
        "Luffy destruye la sala de cartografía de Nami",
        93,
        43,
        ["arlong_park"],
        "event",
    ),
    (
        "Zoro jura vencer a Mihawk algún día",
        "Zoro jura no volver a perder hasta derrotar a Mihawk",
        52,
        24,
        ["baratie"],
        "event",
    ),
    (
        "Luffy salva a Vivi en el palacio real",
        "Luffy salva a Vivi cuando Crocodile la arroja del muro del palacio",
        199,
        121,
        ["arabasta"],
        "event",
    ),
    (
        "Luffy suena la campana dorada",
        "Luffy hace sonar la campana dorada al derrotar a Enel",
        298,
        193,
        ["skypiea"],
        "fin_arco",
    ),
    (
        "Enel es derrotado por el Thunderbolt de Luffy",
        "Enel es derrotado por el Gomu Gomu no Ogon Rifle de Luffy",
        298,
        192,
        ["skypiea"],
        "event",
    ),
    (
        "Law corta a Vergo y destruye la fábrica de Smile",
        "Law corta a Vergo y destruye la sala de producción SAD",
        690,
        616,
        ["punk_hazard"],
        "event",
    ),
    (
        "Jinbe se une oficialmente a los Sombrero de Paja",
        "Jinbe declara que se une a los Sombrero de Paja",
        863,
        833,
        ["whole_cake_island"],
        "event",
    ),
    (
        "Yamato decide luchar junto a Luffy contra Kaido",
        "Yamato decide aliarse con Luffy contra Kaido",
        984,
        991,
        ["wano"],
        "event",
    ),
    (
        "Luffy despierta el Haki del Rey frente a Kaido",
        "Luffy domina el Haki del Conquistador avanzado contra Kaido",
        1010,
        1027,
        ["wano"],
        "event",
    ),
    (
        "Usopp dispara a un pájaro desde la Torre de Gion",
        "Usopp quema la bandera del Gobierno Mundial con Fire Bird Star",
        398,
        278,
        ["enies_lobby"],
        "event",
    ),
    (
        "Luffy transforma a un Buster Call en goma",
        "Saturn ordena un Buster Call en Egghead",
        1104,
        1139,
        ["egghead"],
        "event",
    ),
    (
        "Luffy libera a Hancock",
        "Hancock ayuda a Luffy a infiltrarse en Impel Down",
        523,
        417,
        ["amazon_lily"],
        "event",
    ),
    (
        "Buggy y Alvida se reencuentran",
        "Buggy se reencuentra con su tripulación",
        593,
        512,
        ["post_guerra"],
        "event",
    ),
    (
        "Morgan corta la estatua",
        "Luffy destruye la estatua de Morgan",
        4,
        2,
        ["romance_dawn"],
        "event",
    ),
]


def _load_canonical_prompt_texts() -> set[str]:
    if not PROMPTS_PATH.exists():
        return set()
    payload = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    return {str(entry["prompt"]).strip() for entry in payload}


def fix_proximity_prompt_corrections(apps, schema_editor):
    Game = apps.get_model("games", "Game")
    ProximityPrompt = apps.get_model("games", "ProximityPrompt")

    game = Game.objects.filter(slug=ONE_PIECE_GAME_SLUG).first()
    if game is None:
        return

    for old_text, new_text, chapter, episode, arcs, kind in PROMPT_RENAMES:
        ProximityPrompt.objects.filter(game=game, prompt_text=old_text).update(
            prompt_text=new_text,
            answer_value=chapter,
            answer_episode=episode,
            arcs=arcs,
            kind=kind,
            active=True,
        )

    canonical_texts = _load_canonical_prompt_texts()
    if not canonical_texts:
        return

    ProximityPrompt.objects.filter(game=game).exclude(
        prompt_text__in=canonical_texts
    ).update(active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0054_silhouette_mode"),
    ]

    operations = [
        migrations.RunPython(fix_proximity_prompt_corrections, migrations.RunPython.noop),
    ]
