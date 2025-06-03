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


N_COL_W = 2  # Ancho para contenido de columna Nº (ej: "10")
ELO_COL_W = 5  # Ancho para contenido de columna ELO (ej: "1200", " ELO ")
USER_HEADER_TEXT = "Usuario"
MAX_USER_W = 25  # Máximo ancho para contenido de nombre de usuario
MIN_USER_W = max(len(USER_HEADER_TEXT), 10) # Mínimo ancho para contenido de nombre de usuario


def _generar_tabla_ranking(ranking_data, is_global_ranking=False):
    if not ranking_data:
        # Esto normalmente lo maneja formatear_ranking, pero por si acaso.
        return "No hay datos de ranking para mostrar."

    usernames = [
        item['user__username'] if is_global_ranking else item.user.username
        for item in ranking_data
    ]
    
    max_data_username_len = 0
    if usernames:
        max_data_username_len = max(len(name) for name in usernames)

    # Calcular el ancho de contenido real para la columna de usuario
    user_col_content_w = max(len(USER_HEADER_TEXT), max_data_username_len)
    user_col_content_w = max(user_col_content_w, MIN_USER_W)
    user_col_content_w = min(user_col_content_w, MAX_USER_W)

    # Anchos de contenido para las otras columnas (texto dentro de las celdas)
    n_content_w = N_COL_W
    elo_content_w = ELO_COL_W

    # Longitud de las barras horizontales (═), incluyendo 1 espacio de padding a cada lado del contenido
    n_bar_len = n_content_w + 2
    user_bar_len = user_col_content_w + 2
    elo_bar_len = elo_content_w + 2

    n_bar_str = "═" * n_bar_len
    user_bar_str = "═" * user_bar_len
    elo_bar_str = "═" * elo_bar_len

    # Construir partes de la tabla
    top_border = f"╔{n_bar_str}╦{user_bar_str}╦{elo_bar_str}╗"
    header_row = f"║ {str('Nº').center(n_content_w)} ║ {USER_HEADER_TEXT.center(user_col_content_w)} ║ {str('ELO').center(elo_content_w)} ║"
    separator = f"╠{n_bar_str}╬{user_bar_str}╬{elo_bar_str}╣"
    bottom_border = f"╚{n_bar_str}╩{user_bar_str}╩{elo_bar_str}╝"

    table_rows_strings = []
    for idx, item in enumerate(ranking_data, start=1):
        idx_str = str(idx).center(n_content_w)
        
        elo_original = item['avg_elo'] if is_global_ranking else item.elo
        elo_str = str(int(elo_original)).rjust(elo_content_w) # ELO alineado a la derecha

        username_original = item['user__username'] if is_global_ranking else item.user.username
        display_username = username_original
        if len(username_original) > user_col_content_w:
            display_username = username_original[:user_col_content_w-3] + "..."
        user_str = display_username.ljust(user_col_content_w) # Usuario alineado a la izquierda

        table_rows_strings.append(f"║ {idx_str} ║ {user_str} ║ {elo_str} ║")

    # Ensamblar la tabla completa
    full_table_parts = [top_border, header_row]
    if not table_rows_strings: # Si, después de todo, no hay filas (aunque ranking_data no estuviera vacío)
        # Esto es un fallback, idealmente no debería llegar aquí si formatear_ranking funciona
        placeholder_text = "No hay jugadores".center(user_col_content_w)
        full_table_parts.append(separator)
        full_table_parts.append(f"║ {str('').center(n_content_w)} ║ {placeholder_text} ║ {str('').center(elo_content_w)} ║")

    else:
        for i, data_row_str in enumerate(table_rows_strings):
            full_table_parts.append(separator) # Separador antes de cada fila de datos
            full_table_parts.append(data_row_str)
            
    full_table_parts.append(bottom_border)
    return "\n".join(full_table_parts)


def formatear_ranking(game_slug=None):
    embed_color = discord.Color.red()

    if game_slug:
        try:
            juego = Game.objects.get(slug=game_slug)
            if juego.color:
                try:
                    hex_color = juego.color.lstrip('#')
                    rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    embed_color = discord.Color.from_rgb(rgb_color[0], rgb_color[1], rgb_color[2])
                except ValueError:
                    pass
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
        global_embed_color = discord.Color.blue()
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
                global_embed_color
            )

        description_content = _generar_tabla_ranking(game_elos, is_global_ranking=True)
        return _crear_embed_ranking(
            titulo_embed,
            f"```{description_content}```",
            global_embed_color
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
