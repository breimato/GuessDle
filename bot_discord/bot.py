import os
import sys

import django
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from asgiref.sync import sync_to_async

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar .env
load_dotenv()
BASE_URL = os.getenv("CSRF_TRUSTED_ORIGINS")
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
    await bot.tree.sync()
    print(f"🤖 Bot conectado como {bot.user}")
    print("Slash commands sincronizados.")


def _crear_embed_ranking(title, description, color, thumbnail_url=None):
    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    return embed


def _generar_tabla_ranking(ranking_data, is_global_ranking=False):
    description_content = "╔════╦═════════════════════════════╦═══════╗\n"
    description_content += "║ Nº ║ Usuario                     ║  ELO  ║\n"
    description_content += "╠════╬═════════════════════════════╬═══════╣\n"
    for idx, item in enumerate(ranking_data, start=1):
        idx_f = str(idx).center(4)
        if is_global_ranking:
            user_f = item['user__username'][:27].ljust(29)
            elo_f = str(int(item['avg_elo'])).center(7)
        else:
            user_f = item.user.username[:27].ljust(29)
            elo_f = str(int(item.elo)).center(7)
        description_content += f"║{idx_f}║{user_f}║{elo_f}║\n"
        if idx < len(ranking_data):
            description_content += "╠════╬═════════════════════════════╬═══════╣\n"
    description_content += "╚════╩═════════════════════════════╩═══════╝"
    return description_content


def formatear_ranking(game_slug=None):
    embed_color = discord.Color.red()

    if game_slug:
        try:
            juego = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            return _crear_embed_ranking(
                "Error",
                f"❗ No se encontró el juego '{game_slug}'",
                embed_color
            )

        game_elos = GameElo.objects.filter(game=juego).order_by("-elo")[:10]
        titulo_embed = f"🏆 Ranking de {juego.name}"
        
        thumbnail_url_final = None
        if hasattr(juego, 'icon_image') and juego.icon_image and juego.icon_image.url:
            icon_path = juego.icon_image.url
            if BASE_URL:
                if BASE_URL.endswith('/') and icon_path.startswith('/'):
                    thumbnail_url_final = BASE_URL[:-1] + icon_path
                elif not BASE_URL.endswith('/') and not icon_path.startswith('/'):
                     thumbnail_url_final = BASE_URL + '/' + icon_path
                else:
                    thumbnail_url_final = BASE_URL + icon_path
            elif icon_path.startswith(('http://', 'https://')):
                thumbnail_url_final = icon_path


        if not game_elos:
            return _crear_embed_ranking(
                titulo_embed,
                "❗ No hay jugadores registrados aún.",
                embed_color,
                thumbnail_url=thumbnail_url_final
            )

        description_content = _generar_tabla_ranking(game_elos)
        return _crear_embed_ranking(
            titulo_embed,
            f"```{description_content}```",
            embed_color,
            thumbnail_url=thumbnail_url_final
        )
    else:  # Ranking global
        game_elos = (
            GameElo.objects
            .values("user__username")
            .annotate(avg_elo=Avg("elo"))
            .order_by("-avg_elo")[:10]
        )
        titulo_embed = "🌍 Ranking Global (Media ELO)"

        if not game_elos:
            return _crear_embed_ranking(
                titulo_embed,
                "❗ No hay jugadores registrados aún.",
                embed_color
            )

        description_content = _generar_tabla_ranking(game_elos, is_global_ranking=True)
        return _crear_embed_ranking(
            titulo_embed,
            f"```{description_content}```",
            embed_color
        )


# Comando global de ranking
@bot.tree.command(name="ranking", description="Muestra el ranking global (Media ELO).")
async def ranking_global_slash(interaction: discord.Interaction):
    embed_mensaje = await sync_to_async(formatear_ranking)()
    await interaction.response.send_message(embed=embed_mensaje)


# Obtener slugs de juegos activos desde la base de datos
try:
    JUEGOS_SLUGS_Y_NOMBRES = list(Game.objects.filter(active=True).values_list('slug', 'name'))
except Exception as e:
    print(f"Error al cargar juegos para slash commands: {e}")
    JUEGOS_SLUGS_Y_NOMBRES = []

# Generar comandos de ranking específicos para cada juego
for slug, game_name in JUEGOS_SLUGS_Y_NOMBRES:
    def create_game_ranking_callback(current_slug):
        async def game_ranking_callback(interaction: discord.Interaction):
            embed_mensaje = await sync_to_async(formatear_ranking)(current_slug)
            await interaction.response.send_message(embed=embed_mensaje)
        return game_ranking_callback

    command_name = slug
    command_description = f"Muestra el ranking de {game_name}."
    
    specific_game_command = app_commands.Command(
        name=command_name,
        description=command_description,
        callback=create_game_ranking_callback(slug)
    )
    bot.tree.add_command(specific_game_command)

print(f"Registrados {len(JUEGOS_SLUGS_Y_NOMBRES)} comandos de ranking de juegos.")

# Ejecutar bot
bot.run(TOKEN)
