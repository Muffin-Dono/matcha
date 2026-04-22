import logging

import discord
from discord.ext import commands
from discord import app_commands

log = logging.getLogger(__name__)

def build_pug_help_embed():
    embed = discord.Embed(title="**PUG Queue Help**", color=0x6a994e)

    embed.set_author(name="Matcha", url="https://github.com/Muffin-Dono/matcha")

    embed.add_field(
        name="",
        value=(
            "**Useful Commands**\n"
            "- **`/pug`** - Open the PUG panel (options menu for queue).\n"
            "- **`/join`** - Join the PUG queue.\n"
            "- **`/leave`** - Leave the PUG queue.\n"
            "- **`/remove`** - Remove a player from the PUG queue.\n\n"
            "**PUG Panel Actions Menu**\n"
            "- **Ping Queue** - DM players in queue - usually when 10 players have joined.\n"
            "- **Map Vote** - Start a map vote for the PUG. Planned - tentative.\n"
            "- **Scramble** - Randomize queued players into two teams. Planned - tentative."),
        inline=False
    )

    embed.set_footer(text="Created by Muffin-Dono")

    return embed

def build_tourney_help_embed():
    embed = discord.Embed(title="**Tournament Map Selection Help**", color=0x6a994e)

    embed.set_author(name="Matcha", url="https://github.com/Muffin-Dono/matcha")

    embed.add_field(
        name="",
        value=(
            "- **`/clear`** - Clears any active map selection in the channel.\n"
            "- **`/schedule`** (organizers only) - Create a Discord event on the server for a match.\n\n"
            "**Selecting Maps for your Match**\n"
            "1. **`/match`** - Set the two opposing teams and start the coin toss.\n"
            "2. **`/order`** - Decide your team's pick and ban order.\n"
            "3. **`/map_ban`** - Select a map to ban from the map pool.\n"
            "4. **`/map_pick`** - Select a map to pick from the map pool. In some tournaments, you can also select from a wildcard map pool.\n"
            "5. **`/map_final`** (optional) - Randomly select the final map from the map pool of choice.\n\n"
            "**The bot can load other tournaments not listed by the `/match` command**.\n"
            "Simply input its name (e.g. \"WW25\") when using the command."),
        inline=False
    )

    embed.set_footer(text="Created by Muffin-Dono")

    return embed

# Help for tournament map selection and pug queue
class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="help", description="Get a list of commands for different features")
    @app_commands.describe(process="What process do you need help with?")
    @app_commands.choices(process=[
        app_commands.Choice(name="PUG Queue", value="pug"),
        app_commands.Choice(name="Tournament Map Selection", value="tourney")
    ])
    async def help(self, interaction: discord.Interaction, process: str):
        if process == "pug":
            embed = build_pug_help_embed()
        elif process == "tourney":
            embed = build_tourney_help_embed()
        else:
            await interaction.response.send_message("Matcha doesn't know about that...", ephemeral=True)
            return

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
