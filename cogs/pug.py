import asyncio
import logging

# from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands

log = logging.getLogger(__name__)

# Set up the timeout logic for the bot
TIMEOUT_DURATION = 3*60*60  # 3 hours

class ButtonOnCooldown(commands.CommandError):
    pass
def key(interaction: discord.Interaction):
    return interaction.channel_id

ping_cd = commands.CooldownMapping.from_cooldown(1, 600, key) # 10 minutes

class MoreButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ping Queue", style=discord.ButtonStyle.red, emoji="\U0001f514")
    async def ping_queue_button(self, interaction, button):
        cog = interaction.client.get_cog("Pug")
        if not cog:
            await interaction.response.send_message("Matcha is still warming up....", ephemeral=True)
            return
        
        queue = cog.get_state(interaction.channel_id)

        if not queue['players']:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return

        if not any(role.permissions.administrator for role in interaction.user.roles) and interaction.user.id not in queue['players']:
            await interaction.response.send_message("Only queued players may :bell: **Ping Queue**.", ephemeral=True)
            return

        # Minimum of six players required to ping the queue
        if not any(role.permissions.administrator for role in interaction.user.roles) and len(queue['players']) < 6:
            await interaction.response.send_message(
                "## :exclamation:**Not Enough Players**\n"
                "- Aim for more players (e.g. 5v5) before you :bell: **Ping Queue**.\n"
                "- You may :bell: **Ping Queue** earlier and play smaller teams (e.g. 3v3 or 4v4), but **check with the queue first :handshake:**.",
                ephemeral=True)
            return

        retry_after = ping_cd.update_rate_limit(interaction)
        if retry_after:
            minutes = int(retry_after // 60)
            await interaction.response.send_message(f":bell: **Ping Queue** is on cooldown. Try again in {minutes} minutes. :hourglass_flowing_sand:", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        for user_id in queue['players'][:10]:
            player = interaction.guild.get_member(user_id) or await interaction.guild.fetch_member(user_id)

            try:
                await player.send(f"{interaction.user.mention} has pinged everyone in the queue! :bell:\n"
                                f"> <#{interaction.channel_id}>\n\n"
                                "Gather in VC and make teams! :sound:",
                                allowed_mentions=discord.AllowedMentions(users=False))
            except discord.Forbidden:
                pass

        await interaction.followup.send(f"**{interaction.user.mention} has pinged everyone in the queue! :bell:**",
                                        allowed_mentions=discord.AllowedMentions(users=True))

    @discord.ui.button(label="Map Vote", style=discord.ButtonStyle.blurple, emoji="\U0001f5fa")
    async def map_vote_button(self, interaction, button):
        await interaction.response.send_message(":tools: Planned (tentative)", ephemeral=True)

    @discord.ui.button(label="Scramble", style=discord.ButtonStyle.blurple, emoji="\U0001f500")
    async def scramble_button(self, interaction, button):
        await interaction.response.send_message(":tools: Planned (tentative)", ephemeral=True)

# Main set of buttons, for joining/leaving queue and guide
class MainButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.green, emoji="\U0000270b", custom_id='persistent_view:queue_add')
    async def join_button(self, interaction, button):
        cog = interaction.client.get_cog("Pug")
        if not cog:
            await interaction.response.send_message("Matcha is still warming up....", ephemeral=True)
            return

        added = await cog.queue_add(interaction.user.id, interaction.channel_id)
        queue = cog.get_state(interaction.channel_id)

        if not added:
            await interaction.response.send_message("You are already in the queue.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"{interaction.user.mention} (`@{interaction.user.display_name}`) has joined the queue -----> **{len(queue['players'])} player(s) in queue**\n",
            allowed_mentions=discord.AllowedMentions(users=False))

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.red, emoji="\U0001f44b", custom_id='persistent_view:queue_remove')
    async def leave_button(self, interaction, button):
        cog = interaction.client.get_cog("Pug")
        if not cog:
            await interaction.response.send_message("Matcha is still warming up....", ephemeral=True)
            return

        removed = await cog.queue_remove(interaction.user.id, interaction.channel_id)
        queue = cog.get_state(interaction.channel_id)

        if not removed:
            await interaction.response.send_message("You are not in the queue.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"{interaction.user.mention} (`@{interaction.user.display_name}`) has left the queue -----> **{len(queue['players'])} player(s) in queue**\n",
            allowed_mentions=discord.AllowedMentions(users=False))

    @discord.ui.button(label="How to Play", style=discord.ButtonStyle.blurple, emoji="\U0001f5d2", custom_id='persistent_view:how_to_play')
    async def how_to_play_button(self, interaction, button):
        how_to_play_embed = discord.Embed(
            title=":notepad_spiral: How to Play",
            description="",
            colour=0x99AAB5
            )

        how_to_play_field1 = (
            "Pick-up games (PUGs) are **competitive**. While anyone is welcome to join, **prior experience is recommended**.\n\n"
            "__:dart: **Overview**__"
            )

        how_to_play_field2 = (
            "1. First, **`/join`** the queue, but **only if you can play a full PUG** (up to 40 mins)."
        )

        how_to_play_field3 = (
            "2. Matches only start when (usually) 10 players join. **__Don't Ping Queue until then__**."
            )

        how_to_play_field4 = (
            "3. **Join VC on time** and make teams, or lose your spot (10-minute grace period)."
            )

        how_to_play_field5 = (
            "4. Share info (**enemy locations, health** etc.) with your team and work together."
            )

        how_to_play_field6 = (
            "5. **Have fun!** Remember to **`/leave`** when you're finished **so others can play too**.\n\n"
            ":scroll: Use **`/help pug`** for the full list of commands."
            )

        how_to_play_embed.add_field(name="", value=how_to_play_field1, inline=False)
        how_to_play_embed.add_field(name="", value=how_to_play_field2, inline=False)
        how_to_play_embed.add_field(name="", value=how_to_play_field3, inline=False)
        how_to_play_embed.add_field(name="", value=how_to_play_field4, inline=False)
        how_to_play_embed.add_field(name="", value=how_to_play_field5, inline=False)
        how_to_play_embed.add_field(name="", value=how_to_play_field6, inline=False)

        await interaction.response.send_message(embed=how_to_play_embed, ephemeral=True)

    @discord.ui.button(label="Actions", style=discord.ButtonStyle.grey, emoji="\U00002728", row=1, custom_id='persistent_view:actions')
    async def actions_button(self, interaction, button):
        cog = interaction.client.get_cog("Pug")
        if not cog:
            await interaction.response.send_message("Matcha is still warming up....", ephemeral=True)
            return

        more_panel = cog.build_more_panel_embed(interaction.channel_id)
        await interaction.response.send_message(embed=more_panel, view=MoreButtons(), ephemeral=True)

class Pug(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Initialize global state dictionary for pug queue
        self.queue_handler = {}
        self.timeout_tasks = {}
        self.panel_messages = {}
        self.embed_tasks = {}
        self.nickname_tasks = {}
        
        bot.add_view(MainButtons())
    
    async def timeout_clear(self, channel_id):
        try:
            await asyncio.sleep(TIMEOUT_DURATION)

            # Check if players are in queue
            queue = self.queue_handler.get(channel_id)
            if not queue or not queue['players']:
                return

            # Clear queue
            self.queue_handler.pop(channel_id, None)
            self.timeout_tasks.pop(channel_id, None)
            
            # # Refresh panel and change nickname
            await self.refresh_panel(channel_id)
            await self.change_nickname(channel_id)

            # Notify channel that queue has been cleared
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            
            await channel.send(
                f"PUG queue has been cleared of all players due to {int(TIMEOUT_DURATION // (60*60))} hours of inactivity. :pouring_liquid:")

            guild = channel.guild
            log.info(f"Clearing PUG queue in {channel}, {guild}...")

        except asyncio.CancelledError:
            pass

    # Function to reset the timeout counter
    def reset_timeout_counter(self, channel_id):
        if channel_id in self.timeout_tasks:
            self.timeout_tasks[channel_id].cancel()

        task = asyncio.create_task(self.timeout_clear(channel_id))
        self.timeout_tasks[channel_id] = task

    # Function to remove any active timeout counters in the channel
    async def clear_timeout(self, channel_id):
        if channel_id in self.timeout_tasks:
            self.timeout_tasks[channel_id].cancel()
            self.timeout_tasks.pop(channel_id, None)

    # Function to resolve interaction channel (bot must only take inputs from the channel it is being used in)
    def get_state(self, channel_id):
        if channel_id not in self.queue_handler:
            self.queue_handler[channel_id] = {"players": []}
        return self.queue_handler[channel_id]
    
    # Build PUG panel embed
    def build_main_panel_embed(self, channel_id: int):
        queue = self.get_state(channel_id)

        description=("Join the queue to play!\n\n"
                    "**Competitive rules apply**. Click **How to Play** for more info.")

        embed = discord.Embed(
            title=":tea: Brewing a PUG Queue...",
            description=description,
            colour=0x6a994e
        )

        embed.set_author(name="Matcha", url="https://github.com/Muffin-Dono/matcha")

        embed.add_field(name="", value="\u00AD", inline=False)

        if not queue['players']:
            embed.add_field(name="Player Queue", value="Queue is empty :dash:", inline=False)
        else:
            players = len(queue['players'])

            embed.add_field(
                name="Player Queue",
                value="\n".join(
                    f"{i+1}. <@{user_id}>"
                    for i, user_id in enumerate(queue['players'][:10])
                ),
                inline=True
            )

            if players > 10:
                embed.add_field(
                    name="\u200b",
                    value="\n".join(
                        f"{i+11}. <@{user_id}>"
                        for i, user_id in enumerate(queue['players'][10:20])
                    ),
                    inline=True
                )

            if players > 20:
                embed.add_field(
                    name="\u200b",
                    value="\n".join(
                        f"{i+21}. <@{user_id}>"
                        for i, user_id in enumerate(queue['players'][20:30])
                    ),
                    inline=True
                )

        embed.set_footer(text="Created by Muffin-Dono")

        return embed
    
    # Refresh PUG panel embed
    async def refresh_panel(self, channel_id: int):
        if channel_id not in self.panel_messages:
            return

        # Create necessary variables for refreshing panels
        channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        panel = self.build_main_panel_embed(channel_id)
        main_buttons = MainButtons()

        for panel_message in reversed(self.panel_messages[channel_id]):
            try:
                msg = await channel.fetch_message(panel_message)
                await msg.edit(embed=panel, view=main_buttons)
            except discord.NotFound:
                pass
    
    # Function to schedule a debounced update for the PUG panel
    def schedule_embed_update(self, channel_id):

        async def debounce_task():
            await asyncio.sleep(2)
            try:
                await self.refresh_panel(channel_id)
            finally:
                self.embed_tasks.pop(channel_id, None)
        
        if channel_id in self.embed_tasks:
            self.embed_tasks[channel_id].cancel()

        self.embed_tasks[channel_id] = asyncio.create_task(debounce_task())
    
    # Build Actions panel embed
    def build_more_panel_embed(self, channel_id: int):
        embed = discord.Embed(
            title=":sparkles: Actions Menu",
            description=(
                "**Here are some bonus options to help you set up a PUG:**\n\n"
                "**Ping Queue**\n"
                "- DM players in the queue.\n"
                "**Map Vote**\n"
                "- Start a map vote for the PUG.\n"
                "**Scramble**\n"
                "- Randomize queued players into two teams.\n"),
            colour=0xffc300
        )

        embed.set_footer(text="Created by Muffin-Dono")

        return embed
    
    # Change nickname according to the number of players in queue
    async def change_nickname(self, channel_id: int):
        queue = self.get_state(channel_id)
        players = len(queue['players'])

        channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        guild = channel.guild
        me = await guild.fetch_member(self.bot.user.id)

        if players > 0:
            nickname = f"{self.bot.user.name} ({players} in queue)"
        else:
            nickname = None

        try:
            await me.edit(nick=nickname)
        except discord.Forbidden:
            pass

    # Function to schedule a debounced update for the bot's nickname
    def schedule_nickname_update(self, channel_id):

        async def debounce_task():
            await asyncio.sleep(3)
            try:
                await self.change_nickname(channel_id)
            finally:
                self.nickname_tasks.pop(channel_id, None)
        
        if channel_id in self.nickname_tasks:
            self.nickname_tasks[channel_id].cancel()

        self.nickname_tasks[channel_id] = asyncio.create_task(debounce_task())
    
    # Function to join queue
    async def queue_add(self, user_id: int, channel_id: int):
        queue = self.get_state(channel_id)

        if user_id in queue['players']:
            return False

        queue['players'].append(user_id)

        self.reset_timeout_counter(channel_id)
        self.schedule_embed_update(channel_id)
        self.schedule_nickname_update(channel_id)
        return True

    # Function to leave queue
    async def queue_remove(self, user_id: int, channel_id: int):
        queue = self.get_state(channel_id)

        if user_id not in queue['players']:
            return False

        queue['players'].remove(user_id)

        if queue['players']:
            self.reset_timeout_counter(channel_id)
        else:
            await self.clear_timeout(channel_id)

        self.schedule_embed_update(channel_id)
        self.schedule_nickname_update(channel_id)
        
        return True

    # Command to open PUG prompt
    @app_commands.command(name="pug", description="Open the PUG panel and view the queue")
    async def pug_command(self, interaction: discord.Interaction):
        main_panel = self.build_main_panel_embed(interaction.channel_id)

        main_buttons = MainButtons()

        await interaction.response.send_message(embed=main_panel, view=main_buttons)

        panel_message = await interaction.original_response()

        if interaction.channel_id not in self.panel_messages:
            self.panel_messages[interaction.channel_id] = []

        # Store the message ID in dict
        self.panel_messages[interaction.channel_id].append(panel_message.id)

        # Only store up to 3 messages
        self.panel_messages[interaction.channel_id] = self.panel_messages[interaction.channel_id][-3:]

    # Command to join the queue
    @app_commands.command(name="join", description="Join the PUG queue")
    async def join_command(self, interaction: discord.Interaction):
        queue = self.get_state(interaction.channel_id)

        added = await self.queue_add(interaction.user.id, interaction.channel_id)
        if not added:
            await interaction.response.send_message("You are already in the queue.", ephemeral=True)
            return
        else:
            await interaction.response.send_message(
                f"{interaction.user.mention} (`@{interaction.user.display_name}`) has joined the queue -----> **{len(queue['players'])} player(s) in queue**\n",
                allowed_mentions=discord.AllowedMentions(users=False))

    # Command to leave the queue
    @app_commands.command(name="leave", description="Leave the PUG queue")
    async def leave_command(self, interaction: discord.Interaction):
        queue = self.get_state(interaction.channel_id)

        removed = await self.queue_remove(interaction.user.id, interaction.channel_id)
        if not removed:
            await interaction.response.send_message("You are not in the queue.", ephemeral=True)
            return
        else:
            await interaction.response.send_message(
                f"{interaction.user.mention} (`@{interaction.user.display_name}`) has left the queue -----> **{len(queue['players'])} player(s) in queue**\n",
                allowed_mentions=discord.AllowedMentions(users=False))

    # Command to remove a player from the queue
    @app_commands.command(name="remove", description="Remove a player from the PUG queue")
    async def remove_command(self, interaction: discord.Interaction, player: discord.Member):
        queue = self.get_state(interaction.channel_id)

        removed = await self.queue_remove(player.id, interaction.channel_id)
        if not removed:
            await interaction.response.send_message("Player is not in the queue.", allowed_mentions=None, ephemeral=True)
            return

        await interaction.response.send_message(
            f"{interaction.user.mention} has removed {player.mention} from the queue -----> **{len(queue['players'])} player(s) in queue**\n",
            allowed_mentions=discord.AllowedMentions(users=False))

        await player.send(
            f"{interaction.user.mention} (`@{interaction.user.display_name}`) has removed you from the queue. :leaves:\n"
            f"> <#{interaction.channel_id}>\n\n",
            allowed_mentions=discord.AllowedMentions(users=False))

async def setup(bot: commands.Bot):
    await bot.add_cog(Pug(bot))
