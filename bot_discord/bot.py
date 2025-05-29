import os
import sys

import django
import discord
from discord.ext import commands
from dotenv import load_dotenv
from asgiref.sync import sync_to_async

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configurar entorno Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "GuessDle.settings")
django.setup()

# Importar modelos
from django.contrib.auth.models import User
from apps.games.models import Game
from apps.accounts.models import GameElo

from django.db.models import Avg

# Crear bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")


def formatear_ranking(game_slug=None):
    if game_slug:
        try:
            juego = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            return f"❗ No se encontró el juego '{game_slug}'"
        game_elos = GameElo.objects.filter(game=juego).order_by("-elo")[:10]
        titulo = f"🏆 Ranking de {juego.name}"

        if not game_elos:
            return "❗ No hay jugadores registrados aún."

        mensaje = f"**{titulo}**\n\n"
        mensaje += "```\n"
        mensaje += f"{'Usuario':<16} | {'ELO':<5}\n"
        mensaje += "-" * 26 + "\n"
        for idx, obj in enumerate(game_elos, start=1):
            mensaje += f"{idx:<2} {obj.user.username:<15} | {int(obj.elo):<5}\n"
        mensaje += "```"
    else:
        game_elos = (
            GameElo.objects
            .values("user__username")
            .annotate(avg_elo=Avg("elo"))
            .order_by("-avg_elo")[:10]
        )
        titulo = "🌍 Ranking Global (Media ELO)"

        if not game_elos:
            return "❗ No hay jugadores registrados aún."

        mensaje = f"**{titulo}**\n\n"
        mensaje += "```\n"
        mensaje += f"{'Usuario':<16} | {'ELO':<5}\n"
        mensaje += "-" * 26 + "\n"
        for idx, obj in enumerate(game_elos, start=1):
            mensaje += f"{idx:<2} {obj['user__username']:<15} | {int(obj['avg_elo']):<5}\n"
        mensaje += "```"

    return mensaje


# Comando global
@bot.command(name="ranking")
async def ranking_global(ctx):
    mensaje = await sync_to_async(formatear_ranking)()
    await ctx.send(mensaje)


# Generar comandos por juego
def crear_comando_ranking(slug):
    async def ranking_especifico(ctx):
        mensaje = await sync_to_async(formatear_ranking)(slug)
        await ctx.send(mensaje)

    ranking_especifico.__name__ = f"ranking_{slug.replace('-', '_')}"
    return ranking_especifico


# Lista de juegos (slugs)
JUEGOS_SLUGS = [
    "league-of-legends",
    "one-piece",
    "futbol",
    "harry-potter",
    "shingeki",
    "pokemon",
]

for slug in JUEGOS_SLUGS:
    comando = crear_comando_ranking(slug)
    bot.command(name=slug)(comando)

# Ejecutar bot
bot.run(TOKEN)
