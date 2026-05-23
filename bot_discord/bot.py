"""Discord bot for displaying GuessDle game leaderboards and rankings."""

import os
import sys
import django
import discord
from django.db.models import Sum
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from asgiref.sync import sync_to_async

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
BASE_URL = os.getenv("CSRF_TRUSTED_ORIGINS")
TOKEN = os.getenv("DISCORD_TOKEN")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "GuessDle.settings")
django.setup()

from django.contrib.auth.models import User
from apps.games.models import Game
from apps.accounts.models import GameElo

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Event handler triggered when the Discord bot connection has successfully established."""

    await bot.tree.sync()
    print(f"🤖 Bot connected as {bot.user}")
    print("Slash commands synchronized.")


def _create_ranking_embed(title, description, color, thumbnail_url=None):
    """Construct a discord.Embed message formatting object."""

    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    return embed


N_COLUMN_WIDTH = 2
ELO_COLUMN_WIDTH = 5
USER_HEADER_TEXT = "User"
MAX_USER_WIDTH = 25
MIN_USER_WIDTH = max(len(USER_HEADER_TEXT), 10)


def _generate_ranking_table(ranking_data, is_global_ranking=False):
    """Generate a formatted ASCII table representing ranking data."""

    if not ranking_data:
        return "No ranking data to show."

    usernames = [
        item['user__username'] if is_global_ranking else item.user.username
        for item in ranking_data
    ]

    max_username_length = 0
    if usernames:
        max_username_length = max(len(name) for name in usernames)

    user_column_content_width = max(len(USER_HEADER_TEXT), max_username_length)
    user_column_content_width = max(user_column_content_width, MIN_USER_WIDTH)
    user_column_content_width = min(user_column_content_width, MAX_USER_WIDTH)

    n_content_width = N_COLUMN_WIDTH
    elo_content_width = ELO_COLUMN_WIDTH

    n_bar_length = n_content_width + 2
    user_bar_length = user_column_content_width + 2
    elo_bar_length = elo_content_width + 2

    n_bar_string = "═" * n_bar_length
    user_bar_string = "═" * user_bar_length
    elo_bar_string = "═" * elo_bar_length

    top_border = f"╔{n_bar_string}╦{user_bar_string}╦{elo_bar_string}╗"
    header_row = f"║ {str('Rank').center(n_content_width)} ║ {USER_HEADER_TEXT.center(user_column_content_width)} ║ {str('ELO').center(elo_content_width)} ║"
    separator = f"╠{n_bar_string}╬{user_bar_string}╬{elo_bar_string}╣"
    bottom_border = f"╚{n_bar_string}╩{user_bar_string}╩{elo_bar_string}╝"

    table_rows_strings = []
    for index, item in enumerate(ranking_data, start=1):
        index_string = str(index).center(n_content_width)

        original_elo = item['total_elo'] if is_global_ranking else item.elo
        elo_string = str(int(original_elo)).rjust(elo_content_width)

        original_username = item['user__username'] if is_global_ranking else item.user.username
        display_username = original_username
        if len(original_username) > user_column_content_width:
            display_username = original_username[:user_column_content_width-3] + "..."
        user_string = display_username.ljust(user_column_content_width)

        table_rows_strings.append(f"║ {index_string} ║ {user_string} ║ {elo_string} ║")

    full_table_parts = [top_border, header_row]
    if not table_rows_strings:
        placeholder_text = "No players".center(user_column_content_width)
        full_table_parts.append(separator)
        full_table_parts.append(f"║ {str('').center(n_content_width)} ║ {placeholder_text} ║ {str('').center(elo_content_width)} ║")
    else:
        for data_row_string in table_rows_strings:
            full_table_parts.append(separator)
            full_table_parts.append(data_row_string)

    full_table_parts.append(bottom_border)
    return "\n".join(full_table_parts)


def format_ranking(game_slug=None):
    """Format and return the ranking embed for a specific game or globally."""

    embed_color = discord.Color.red()

    if game_slug:
        try:
            game = Game.objects.get(slug=game_slug)
            if game.color:
                try:
                    hex_color = game.color.lstrip('#')
                    rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    embed_color = discord.Color.from_rgb(rgb_color[0], rgb_color[1], rgb_color[2])
                except ValueError:
                    pass
        except Game.DoesNotExist:
            return _create_ranking_embed(
                "Error",
                f"❗ Game '{game_slug}' was not found",
                embed_color
            )

        game_elos = GameElo.objects.filter(game=game).order_by("-elo")[:10]
        embed_title = f"🏆 Leaderboard for {game.name}"

        final_thumbnail_url = None
        if hasattr(game, 'icon_image') and game.icon_image and game.icon_image.url:
            icon_path = game.icon_image.url
            if BASE_URL:
                if BASE_URL.endswith('/') and icon_path.startswith('/'):
                    final_thumbnail_url = BASE_URL[:-1] + icon_path
                elif not BASE_URL.endswith('/') and not icon_path.startswith('/'):
                    final_thumbnail_url = BASE_URL + '/' + icon_path
                else:
                    final_thumbnail_url = BASE_URL + icon_path
            elif icon_path.startswith(('http://', 'https://')):
                final_thumbnail_url = icon_path

        if not game_elos:
            return _create_ranking_embed(
                embed_title,
                "❗ No players registered yet.",
                embed_color,
                thumbnail_url=final_thumbnail_url
            )

        description_content = _generate_ranking_table(game_elos)
        return _create_ranking_embed(
            embed_title,
            f"```{description_content}```",
            embed_color,
            thumbnail_url=final_thumbnail_url
        )
    else:
        global_embed_color = discord.Color.blue()
        game_elos = (
            GameElo.objects
            .values("user__username")
            .annotate(total_elo=Sum("elo"))
            .order_by("-total_elo")[:10]
        )
        embed_title = "🌍 Global Leaderboard (Total ELO)"

        if not game_elos:
            return _create_ranking_embed(
                embed_title,
                "❗ No players registered yet.",
                global_embed_color
            )

        description_content = _generate_ranking_table(game_elos, is_global_ranking=True)
        return _create_ranking_embed(
            embed_title,
            f"```{description_content}```",
            global_embed_color
        )


@bot.tree.command(name="ranking", description="Show the global leaderboard (Total ELO).")
async def handle_global_ranking_slash(interaction: discord.Interaction):
    """Slash command to display the global leaderboard ranking."""

    ranking_embed = await sync_to_async(format_ranking)()
    await interaction.response.send_message(embed=ranking_embed)


try:
    ACTIVE_GAME_SLUGS_AND_NAMES = list(Game.objects.filter(active=True).values_list('slug', 'name'))
except Exception as error:
    print(f"Error loading games for slash commands: {error}")
    ACTIVE_GAME_SLUGS_AND_NAMES = []

for slug, game_name in ACTIVE_GAME_SLUGS_AND_NAMES:
    def create_game_ranking_callback(current_slug):
        async def game_ranking_callback(interaction: discord.Interaction):
            ranking_embed = await sync_to_async(format_ranking)(current_slug)
            await interaction.response.send_message(embed=ranking_embed)
        return game_ranking_callback

    command_name = slug
    command_description = f"Show the leaderboard for {game_name}."

    specific_game_command = app_commands.Command(
        name=command_name,
        description=command_description,
        callback=create_game_ranking_callback(slug)
    )
    bot.tree.add_command(specific_game_command)

print(f"Registered {len(ACTIVE_GAME_SLUGS_AND_NAMES)} game ranking commands.")

bot.run(TOKEN)
