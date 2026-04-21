import asyncio
import copy
import importlib
import logging
import pkgutil
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

# Configure cogs directory
BASE_DIR = Path(__file__).resolve().parent
TOURNAMENTS_DIR = BASE_DIR / "tournaments"

sys.path.append(str(BASE_DIR))

# Import the tournament modules and sort by start date
tournaments = []

for _, name, _ in pkgutil.iter_modules([str(TOURNAMENTS_DIR)]):
    tournament = importlib.import_module(f"tournaments.{name}")

    tournament._start_date = datetime.strptime(
        tournament.INFO["start_date"], '%Y-%m-%d'
    )
    tournament._name = name.lower()
    tournament._full_name = tournament.INFO["full_name"].lower()

    tournaments.append(tournament)

tournaments.sort(key=lambda t: t._start_date, reverse=True)

# Initialize global state dictionary for map selection
state_handler = {}
timeout_tasks = {}

# Set up the timeout logic for the bot
TIMEOUT_DURATION = 72*60*60  # 72 hours
TIMEOUT_NOTICE = 12*60*60 # 12 hours

async def timeout_clear(bot: commands.Bot, channel_id):
    try:
        notice_delay = TIMEOUT_DURATION - TIMEOUT_NOTICE

        await asyncio.sleep(notice_delay)

        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)

        await channel.send(
            f":warning: Map selection will be cleared in {int(TIMEOUT_NOTICE // (60*60))} hours if there is no further activity.")

        await asyncio.sleep(TIMEOUT_NOTICE)

        # Clear map selection
        state_handler.pop(channel_id, None)
        timeout_tasks.pop(channel_id, None)

        await channel.send(
            f"Map selection has timed out after {int(TIMEOUT_DURATION // (60*60))} hours of inactivity and has been cleared. :pouring_liquid:")

        guild = channel.guild
        log.info(f"Clearing map selection in {channel}, {guild}...")

    except asyncio.CancelledError:
        pass

# Function to reset the timeout counter
def reset_timeout_counter(bot: commands.Bot, channel_id):
    if channel_id in timeout_tasks:
        timeout_tasks[channel_id].cancel()

    task = asyncio.create_task(timeout_clear(bot, channel_id))
    timeout_tasks[channel_id] = task

# Function to remove any active timeout counters in the channel
async def clear_timeout(channel_id):
    if channel_id in timeout_tasks:
        timeout_tasks[channel_id].cancel()
        timeout_tasks.pop(channel_id, None)

# Function to resolve map name (checks version and aliases)
def resolve_map_name(map_name, MAPS):
    for name, map_info in MAPS.items():
        if map_name.lower() == name.lower():
            return name
        for version in map_info['version']:
            if map_name.lower() == version.lower():
                return name
        for alias in map_info['aliases']:
            if map_name.lower() == alias.lower():
                return name
    return None

# Check if a user has the required perms to override team role restrictions
def user_can_override(member):
    return (
        any(role.permissions.administrator for role in member.roles)
        or any(role.name == "Organizer" for role in member.roles))

# Function to resolve input team name and return correct team name
def resolve_team_name(team_name, TEAMS):
    if not team_name:
        return None
    if team_name == "Mixed Team":
        return "Mixed Team"
    for name, team_info in TEAMS.items():
        if team_name.lower() == team_info["tag"].lower():
            return name
        if team_name.lower() == name.lower() or team_name.lower() == team_info["role"].lower():
            return name
    return None

# Function to get role name from team name
def get_team_role(interaction: discord.Interaction, team_name: str, TEAMS) -> str | None:
    for name, info in TEAMS.items():
        if name.lower() == team_name.lower():
            for role in interaction.guild.roles:
                if role.name.lower() == info["role"].lower():
                    return role.name
    return None

def get_team_mention(interaction, team_name, TEAMS):
    team_role = discord.utils.get(interaction.guild.roles, name=get_team_role(interaction, team_name, TEAMS))
    return team_role.mention if team_role else team_name

# Function to check if user belongs to a team
def user_is_on_team(interaction: discord.Interaction, member: discord.Member, team_name, TEAMS):
    if team_name in ["Mixed Team", "Mixed Team A", "Mixed Team B"]:
        return True

    team_role = get_team_role(interaction, team_name, TEAMS)

    if any(role.name == team_role for role in member.roles):
        return True

    team_role_id = TEAMS[team_name]["id"]
    if any(role.id == team_role_id for role in member.roles):
        return True

    return False

# Function to build and send the embed with the match details
async def send_summary_embed(interaction: discord.Interaction, selection_state):

    MAPS = selection_state["tournament"]["maps"]
    MAP_POOLS = selection_state["tournament"]["map_pools"]
    TEAMS = selection_state["tournament"]["teams"]

    team1 = selection_state["teams"]["team1"]
    team2 = selection_state["teams"]["team2"]
    first_to_ban = selection_state["ban_order"][0]
    second_to_ban = selection_state["ban_order"][1]

    team1_bans = selection_state["bans"]["team1"]
    team2_bans = selection_state["bans"]["team2"]
    team1_picks = selection_state["picks"]["team1"]
    team2_picks = selection_state["picks"]["team2"]

    # Confirm match details in an embed
    embed = discord.Embed(
        title=f"{get_team_role(interaction, team1, TEAMS)} vs {get_team_role(interaction, team2, TEAMS)}",
        description=":white_check_mark: Match is ready to go!",
        colour=0x6a994e
        )

    # Function for formatting map picks/bans in embed fields
    def format_selections(maps, dash=False):
        return "\n".join(f"{'- ' if dash else ''}{map} `{MAPS[map]['version']}`" for map in maps)

    # Add fields to the embed for picks...
    first_map = format_selections(team1_picks) if team1 == second_to_ban else format_selections(team2_picks)
    second_map = format_selections(team2_picks) if team2 == first_to_ban else format_selections(team1_picks)
    third_map = f"{selection_state['random_map']} `{MAPS[selection_state['random_map']]['version']}`"

    embed_maps = (
        f"1. {first_map}\n"
        f"2. {second_map}\n"
        f"3. {third_map}"
        )

    if len(MAP_POOLS) > 1:
        pool_info = f" ({MAPS[selection_state['random_map']]['pool']})"
    else:
        pool_info = ""

    embed_teams = (
        f"1. {second_to_ban}\n"
        f"2. {first_to_ban}\n"
        f"3. *Random*{pool_info}"
        )

    embed.add_field(name="\u00AD", value="\u00AD", inline=False)

    embed.add_field(name="Maps", value=embed_maps, inline=True)
    embed.add_field(name="Picked by", value=embed_teams, inline=True)

    embed.add_field(name="\u00AD", value="\u00AD", inline=False)

    # ...and bans
    embed.add_field(
        name=f"{team1} Bans",
        value=format_selections(team1_bans, dash=True),
        inline=True)
    embed.add_field(
        name=f"{team2} Bans",
        value=format_selections(team2_bans, dash=True),
        inline=True)

    await asyncio.sleep(2)
    await interaction.followup.send(embed=embed)

async def schedule_match(interaction: discord.Interaction, selection_state, text):
    INFO = selection_state["tournament"]["info"]
    TEAMS = selection_state["tournament"]["teams"]

    tourney = INFO["short_name"]
    team1 = selection_state["teams"]["team1"]
    team2 = selection_state["teams"]["team2"]
    start = selection_state["scheduled_event"]["start"]
    duration = selection_state["scheduled_event"]["duration"]

    ent_type = discord.EntityType.external
    priv_level = discord.PrivacyLevel.guild_only

    scheduled_match = await interaction.guild.create_scheduled_event(
        entity_type=ent_type,
        privacy_level=priv_level,
        location=INFO["stream_url"],
        name=f"{tourney}: {team1} vs {team2}",
        start_time=start,
        end_time=start + timedelta(minutes=duration),
        description=text)
    
    start_ts = start.timestamp()

    team1_role = discord.utils.get(interaction.guild.roles, name=get_team_role(interaction, team1, TEAMS))
    team2_role = discord.utils.get(interaction.guild.roles, name=get_team_role(interaction, team2, TEAMS))

    team1_mention = team1_role.mention if team1_role else team1
    team2_mention = team2_role.mention if team2_role else team2
    
    await interaction.response.send_message(f"## {team1_mention} vs {team2_mention}\n"
                                            f"**Matcha has scheduled a match** - <t:{int(start_ts)}:R>!\n\n"
                                            f"{scheduled_match.url}",
                                            )

class EventDescription(discord.ui.Modal):
    def __init__(self, channel_id):
        super().__init__(title="Scheduling an event for a match")

        selection_state = state_handler.get(channel_id)

        if not selection_state:
            return log.info("State not found (modal)")

        bracket_url = selection_state["tournament"]["info"]["bracket_url"]
        vods_url = selection_state["tournament"]["info"]["vods_url"]

        default_description = (
            "## __STAGE - GROUP__ [if applicable]\n"
            "### ROUND x\n"
            "[additional text here]\n\n"
            f"Bracket: {bracket_url}\n"
            f"VODs: {vods_url}"
        )
    
        self.add_description = discord.ui.Label(
            text="Write a description for your event",
            component=discord.ui.TextInput(style=discord.TextStyle.long, default=default_description)
        )

        self.add_item(self.add_description)
    
    async def on_submit(self, interaction: discord.Interaction):
        selection_state = state_handler.get(interaction.channel_id)

        if not selection_state:
            return log.info("State not found (on submit)")

        await schedule_match(interaction, selection_state, self.add_description.component.value)
        
        if selection_state["random_map"]:
                state_handler.pop(interaction.channel_id, None)
                await clear_timeout(interaction.channel_id)
        else:
            # Restarts the timeout counter when a command is used on time
            reset_timeout_counter(interaction.client, interaction.channel_id)

class Tourney(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Command to clear the selection state
    @app_commands.command(name="clear", description="Clears the map selection state")
    async def clear_command(self, interaction: discord.Interaction):
        selection_state = state_handler.get(interaction.channel_id)

        if not selection_state:
            await interaction.response.send_message("Map selection is already clear.", ephemeral=True)
            return

        TEAMS = selection_state["tournament"]["teams"]

        team1 = selection_state["teams"]["team1"]
        team2 = selection_state["teams"]["team2"]

        if team1 and team2 and not (user_can_override(interaction.user)
                or user_is_on_team(interaction, interaction.user, team1, TEAMS)
                or user_is_on_team(interaction, interaction.user, team2, TEAMS)):
            await interaction.response.send_message(
                f"Only **{team1}**, **{team2}**, or an Organizer can clear this map selection.", ephemeral=True)
            return

        state_handler.pop(interaction.channel_id, None)
        await clear_timeout(interaction.channel_id)
        await interaction.response.send_message(
            "Map selection has been cleared. Use **`/match`** to start again.")

    # Command to start map selection, with team assignment and coin toss
    @app_commands.command(name="match", description="Set the tournament and opposing teams for a match")
    @discord.app_commands.describe(pool="Name of map pool you want to select from", team1="Name of team 1", team2="Name of team 2")
    async def match_command(self, interaction: discord.Interaction, pool: str, team1: str, team2: str):
        # Check if map selection is already active in this channel
        if interaction.channel_id in state_handler:
            await interaction.response.send_message(
                "A map selection is already active in this channel! Use **`/clear`** to restart.", ephemeral=True)
            return

        # Dynamically import dictionary of map pool based on user input
        tournament = next(
            (tournament for tournament in tournaments
            if pool.lower() in (tournament._name, tournament._full_name)),
            None)
        
        if not tournament:
            await interaction.response.send_message(
                f"Could not find tournament: {pool}.", ephemeral=True)
            return

        INFO = tournament.INFO
        MAPS = tournament.MAPS
        TEAMS = tournament.TEAMS

        resolved_team1 = resolve_team_name(team1, TEAMS)
        resolved_team2 = resolve_team_name(team2, TEAMS)

        # Check if a user is in one of the opposing teams
        if not user_can_override(interaction.user) and not (
            user_is_on_team(interaction, interaction.user, resolved_team1, TEAMS)
            or user_is_on_team(interaction, interaction.user, resolved_team2, TEAMS)
            or "Mixed Team" in {resolved_team1, resolved_team2}
        ):
            await interaction.response.send_message(
                'You must belong to one of the selected teams. Otherwise, pick "Mixed Team".', ephemeral=True)
            return

        if not resolved_team1 or not resolved_team2:
            await interaction.response.send_message(
                "Team names are not recognized.", ephemeral=True)
            return

        if resolved_team1 == resolved_team2:
            await interaction.response.send_message(
                "Mirror matches are not supported", ephemeral=True)
            return

        # Initialize selection state with assigned teams
        state_handler[interaction.channel_id] = {
            "tournament": {"info": INFO, "maps": MAPS, "teams": TEAMS, "map_pools": INFO["map_pools"]},
            "teams": {"team1": resolved_team1, "team2": resolved_team2},
            "coin_toss_winner": None,
            "ban_order": None,
            "bans": {"team1": [], "team2": []},
            "picks": {"team1": [], "team2": []},
            "remaining_maps": copy.deepcopy(MAPS),
            "final_map_pool": {"team1": None, "team2": None},
            "random_map": None,
            "scheduled_event": {"start": None, "duration": None}
            }

        log.info(f"Created state for channel: {interaction.channel_id}")

        selection_state = state_handler[interaction.channel_id]

        # Announce coin toss winner
        selection_state["coin_toss_winner"] = random.choice([resolved_team1, resolved_team2])

        coin_toss_winner = selection_state["coin_toss_winner"]

        team1_mention = get_team_mention(interaction, resolved_team1, TEAMS)
        team2_mention = get_team_mention(interaction, resolved_team2, TEAMS)
        coin_toss_winner_mention = get_team_mention(interaction, coin_toss_winner, TEAMS)

        await interaction.response.send_message(
            f"## {team1_mention} vs {team2_mention}\n"
            f":map: Map selection started! The tournament is **{pool}**.\n\n"
            "Tossing a coin to see which team will set the ban/pick order... :game_die:",
            allowed_mentions=discord.AllowedMentions(roles=False))
        
        coin_toss_emoji = random.choice([":coin:", ":older_man:", ":church:"])

        await asyncio.sleep(2)
        await interaction.followup.send(
            f"{coin_toss_emoji} **{coin_toss_winner_mention}** wins the coin toss!\n\n"
            ":exclamation: Choose whether your team bans first or second using **`/order`**.\n",
            allowed_mentions=discord.AllowedMentions(roles=False))

        server_role_names_lower = {role.name.lower() for role in interaction.guild.roles}

        missing_roles = [
            info["role"] for name, info in TEAMS.items()
            if info["role"].lower() not in server_role_names_lower
        ]

        if missing_roles:
            await interaction.followup.send(
                ":warning: **WARNING: The following team roles are missing from your server:**\n- "
                + "\n- ".join(missing_roles))

        # Restarts the timeout counter when a command is used on time
        reset_timeout_counter(interaction.client, interaction.channel_id)

    # Show user choice of tournaments
    @match_command.autocomplete('pool')
    async def match_pool_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:

        options = [tournament.INFO["full_name"] for tournament in tournaments][:2]

        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt.lower()
        ]

    # Show user choice of teams
    @match_command.autocomplete('team1')
    async def match_team1_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:
        pool_name = interaction.namespace.pool.lower()
        
        tournament = next(
            (tournament for tournament in tournaments if tournament._full_name == pool_name),
            None
        )

        if not tournament:
            return []

        options = list(tournament.TEAMS.keys()) + ["Mixed Team"]

        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt.lower()
        ]

    @match_command.autocomplete('team2')
    async def match_team2_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:
        pool_name = interaction.namespace.pool.lower()
        
        tournament = next(
            (tournament for tournament in tournaments if tournament._full_name == pool_name),
            None
        )

        if not tournament:
            return []

        options = list(tournament.TEAMS.keys()) + ["Mixed Team"]

        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt.lower()
        ]

    # Command for the coin toss winner to pick the ban order
    @app_commands.command(name='order', description='Choose whether your team bans first or second')
    @discord.app_commands.describe(choice="Ban first and pick second OR ban second and pick first", override="Organizers can override this phase")
    async def order_command(self, interaction: discord.Interaction, choice: str, override: str = "No"):
        selection_state = state_handler.get(interaction.channel_id)

        if not selection_state:
            await interaction.response.send_message(
                "Please use `/match` first to start map selection.", ephemeral=True)
            return

        TEAMS = selection_state["tournament"]["teams"]

        team1 = selection_state["teams"]["team1"]
        team2 = selection_state["teams"]["team2"]
        coin_toss_winner = selection_state["coin_toss_winner"]

        if coin_toss_winner is None:
            await interaction.response.send_message(
                "No coin toss winner! Please use **`/match`** first to select teams.", ephemeral=True)
            return

        if selection_state["ban_order"]:
            await interaction.response.send_message(
                "The ban order has already been decided!", ephemeral=True)
            return

        # Check if user is part of the team that won the coin toss
        if not user_is_on_team(interaction, interaction.user, coin_toss_winner, TEAMS) and override == "No":
            await interaction.response.send_message(
                f"Only a member of **{selection_state['coin_toss_winner']}** can decide the ban/pick order.",
                ephemeral=True)
            return

        if choice not in ["BAN first in banning phase, PICK second in picking phase", "BAN second in banning phase, PICK first in picking phase"]:
            await interaction.response.send_message(
                "Please choose one of the given options.", ephemeral=True)
            return

        if not user_can_override(interaction.user) and override == "Yes":
            await interaction.response.send_message(
                "Only organizers can override this phase!", ephemeral=True)
            return

        if coin_toss_winner == team1:
            selection_state["ban_order"] = [team1, team2] if choice == "BAN first in banning phase, PICK second in picking phase" else [team2, team1]
        else:
            selection_state["ban_order"] = [team2, team1] if choice == "BAN first in banning phase, PICK second in picking phase" else [team1, team2]

        coin_toss_winner_mention = get_team_mention(interaction, coin_toss_winner, TEAMS)

        first_to_ban = selection_state["ban_order"][0]
        first_to_ban_mention = get_team_mention(interaction, first_to_ban, TEAMS)
        
        await interaction.response.send_message(
            f"{coin_toss_winner_mention} has chosen to {choice.lower()}.\n\n"
            f":exclamation: **{first_to_ban_mention}**, please ban a map using **`/map_ban`**.",
            allowed_mentions=discord.AllowedMentions(roles=False))

        # Restarts the timeout counter when a command is used on time
        reset_timeout_counter(interaction.client, interaction.channel_id)

    # Show user the two options (First or Second)
    @order_command.autocomplete('choice')
    async def order_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:

        options = ["BAN first in banning phase, PICK second in picking phase", "BAN second in banning phase, PICK first in picking phase"]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

    # Show user the two options (Yes or No)
    @order_command.autocomplete('override')
    async def order_override_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:

        options = ["Yes","No"]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

    # Command for banning maps
    @app_commands.command(name='map_ban', description='Ban a map')
    @discord.app_commands.describe(map="Select a map to ban", override="Organizers can override this phase")
    async def map_ban_command(self, interaction: discord.Interaction, map: str, override: str = "No"):
        selection_state = state_handler.get(interaction.channel_id)

        if not selection_state:
            await interaction.response.send_message(
                "Please use `/match` first to start map selection.", ephemeral=True)
            return

        INFO = selection_state["tournament"]["info"]
        MAPS = selection_state["tournament"]["maps"]
        TEAMS = selection_state["tournament"]["teams"]

        team1 = selection_state["teams"]["team1"]
        team2 = selection_state["teams"]["team2"]

        # Validate the ban order
        if not selection_state["ban_order"]:
            await interaction.response.send_message(
                "The ban order hasn't been decided yet! Use **`/order`** to decide the ban order.", ephemeral=True)
            return

        first_to_ban = selection_state["ban_order"][0]
        second_to_ban = selection_state["ban_order"][1]

        team1_bans = selection_state["bans"]["team1"]
        team2_bans = selection_state["bans"]["team2"]

        # Determine the banning team
        banning_team = None

        if not team1_bans and not team2_bans:
            banning_team = first_to_ban

        # Checks if the correct team has banned first and resets the ban phase if not
        elif (not team1_bans and team2_bans and team1 == first_to_ban) or (team1_bans and not team2_bans and team2 == first_to_ban):
            selection_state["bans"] = {"team1": [], "team2": []}
            selection_state["remaining_maps"] = copy.deepcopy(MAPS)
            await interaction.response.send_message(
                "Illegal selection state detected. Resetting ban phase.\n\n"
                f"**{selection_state['ban_order'][0]}**, please ban a map using **`/map_ban`**.")
            return

        elif (team1_bans and not team2_bans) or (not team1_bans and team2_bans):
            banning_team = second_to_ban

        if banning_team is None:
            await interaction.response.send_message(
                "You cannot ban any more maps.", ephemeral=True)
            return
        
        banning_team_mention = get_team_mention(interaction, banning_team, TEAMS)

        # Allow only the current team to ban
        if not user_is_on_team(interaction, interaction.user, banning_team, TEAMS) and override == "No":
            await interaction.response.send_message(
                f"Only {banning_team_mention} can ban right now.", ephemeral=True, allowed_mentions=discord.AllowedMentions(roles=False))
            return

        if not user_can_override(interaction.user) and override == "Yes":
            await interaction.response.send_message(
                "Only organizers can override this phase!", ephemeral=True)
            return

        banning_team_key = "team1" if banning_team == team1 else "team2"

        if len(selection_state["bans"][banning_team_key]) >= INFO["max_bans"]:
            await interaction.response.send_message(
                f"{banning_team_mention} has already banned a map!", ephemeral=True, allowed_mentions=discord.AllowedMentions(roles=False))
            return

        standard_maps = [map_key for map_key, map_info in selection_state["remaining_maps"].items() if map_info["pool"] == "Standard"]
        banned_map = resolve_map_name(map, selection_state["remaining_maps"])

        if banned_map not in standard_maps:
            await interaction.response.send_message(
                "Please choose a remaining map from the Standard map pool:\n" + "\n".join([f"- {map}" for map in standard_maps]))
            return

        selection_state["bans"][f"{banning_team_key}"].append(banned_map)
        selection_state["remaining_maps"].pop(banned_map)

        if not all(selection_state["bans"].values()):
            next_team = second_to_ban if banning_team == first_to_ban else first_to_ban
            next_team_mention = get_team_mention(interaction, next_team, TEAMS)

            await interaction.response.send_message(
                f"{banning_team_mention} has banned: **__{banned_map}__**\n\n"
                f":exclamation: **{next_team_mention}**, please ban a map using **`/map_ban`**.",
                allowed_mentions=discord.AllowedMentions(roles=False))

        elif all(selection_state["bans"].values()):
            picking_team = second_to_ban
            picking_team_mention = get_team_mention(interaction, picking_team, TEAMS)

            await interaction.response.send_message(
                f"{banning_team_mention} has banned: **__{banned_map}__**\n\n"
                "**Banning phase complete!** :ballot_box_with_check:",
                allowed_mentions=discord.AllowedMentions(roles=False))
            
            await asyncio.sleep(0.5)
            await interaction.followup.send(
                f":exclamation: **{picking_team_mention}**, please pick a map using **`/map_pick`**.",
                allowed_mentions=discord.AllowedMentions(roles=False)
            )

        # Restarts the timeout counter when a command is used on time
        reset_timeout_counter(interaction.client, interaction.channel_id)

    # Show user the choice of maps to ban
    @map_ban_command.autocomplete('map')
    async def map_ban_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:
        selection_state = state_handler.get(interaction.channel_id)

        if not selection_state:
            return []

        options = [map_key for map_key, map_info in selection_state["remaining_maps"].items() if map_info["pool"] == "Standard"]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

    # Show user the two options (Yes or No)
    @map_ban_command.autocomplete('override')
    async def map_ban_override_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:

        options = ["Yes","No"]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

    # Command for picking maps
    @app_commands.command(name="map_pick", description='Pick a map')
    @discord.app_commands.describe(map="Select a map to pick", override="Organizers can override this phase")
    async def map_pick_command(self, interaction: discord.Interaction, map: str, override: str = "No"):
        selection_state = state_handler.get(interaction.channel_id)

        if not selection_state:
            await interaction.response.send_message(
                "Please use `/match` first to start map selection.", ephemeral=True)
            return

        INFO = selection_state["tournament"]["info"]
        MAP_POOLS = selection_state["tournament"]["map_pools"]
        TEAMS = selection_state["tournament"]["teams"]

        team1 = selection_state["teams"]["team1"]
        team2 = selection_state["teams"]["team2"]

        if not all(selection_state["bans"].values()):
            await interaction.response.send_message(
                "Teams must complete the banning phase first.", ephemeral=True)
            return

        first_to_ban = selection_state["ban_order"][0]
        second_to_ban = selection_state["ban_order"][1]

        # Determine the picking team
        if not any(selection_state["picks"].values()):
            picking_team = second_to_ban
        else:
            picking_team = first_to_ban
        
        picking_team_mention = get_team_mention(interaction, picking_team, TEAMS)

        # Allow only the current team to ban
        if not user_is_on_team(interaction, interaction.user, picking_team, TEAMS) and override == "No":
            await interaction.response.send_message(
                f"Only {picking_team_mention} can pick a map right now.", ephemeral=True, allowed_mentions=discord.AllowedMentions(roles=False))
            return

        if not user_can_override(interaction.user) and override == "Yes":
            await interaction.response.send_message(
                "Only organizers can override this phase!", ephemeral=True)
            return

        team_key = "team1" if picking_team == team1 else "team2"

        if "INVOKE WILDCARD" in map:

            wildcard_maps = [map_key for map_key, map_info in selection_state["remaining_maps"].items() if map_info["pool"] == "Wildcard"]

            if not wildcard_maps:
                await interaction.response.send_message(
                    "No Wildcard maps remaining in the map pool, please enter a different map.", ephemeral=True)
                return

            else:
                picked_map = random.choice(wildcard_maps)
                added_text = "invoked the Wildcard! Their pick will be"

        else:
            picked_map = resolve_map_name(map, selection_state["remaining_maps"])
            standard_maps = [map_key for map_key, map_info in selection_state["remaining_maps"].items() if map_info["pool"] == "Standard"]
            added_text = "picked"

            if picked_map not in standard_maps:
                await interaction.response.send_message(
                    "Please choose a remaining map from the pool:\n" + "\n".join([f"- {map}" for map in standard_maps] + ["- INVOKE WILDCARD"]))
                return

        # Prevent a team from picking twice
        if len(selection_state["picks"][team_key]) >= INFO["max_picks"]:
            await interaction.response.send_message(
                f"{picking_team_mention} has already picked a map: **__{selection_state['picks'][team_key]}__**. You cannot pick again.",
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions(roles=False))
            return

        # Once map is validated, it is saved as a map pick and removed from the remaining map pool
        selection_state["picks"][team_key].append(picked_map)
        selection_state["remaining_maps"].pop(picked_map)

        if not all(selection_state["picks"].values()):
            next_team = first_to_ban if picking_team == second_to_ban else second_to_ban
            next_team_mention = get_team_mention(interaction, next_team, TEAMS)

            await interaction.response.send_message(
                f"{picking_team_mention} has {added_text}: **__{picked_map}__**\n\n"
                f":exclamation: **{next_team_mention}**, please pick a map using **`/map_pick`**.",
                allowed_mentions=discord.AllowedMentions(roles=False))

        if all(selection_state["picks"].values()):
            await interaction.response.send_message(
                f"{picking_team_mention} has {added_text}: **__{picked_map}__**\n\n"
                "**Picking phase complete! :ballot_box_with_check:**\n\n",
                allowed_mentions=discord.AllowedMentions(roles=False))
            if len(MAP_POOLS) == 1:
                final_maps = list(selection_state["remaining_maps"].keys())
                selection_state["random_map"] = random.choice(final_maps)

                await asyncio.sleep(0.5)
                await interaction.followup.send(
                    "Randomly selecting the final map...")

                await send_summary_embed(interaction, selection_state)

                if selection_state["scheduled_event"]["start"] and selection_state["scheduled_event"]["duration"]:
                    state_handler.pop(interaction.channel_id, None)
                    await clear_timeout(interaction.channel_id)
                else:
                    # Restarts the timeout counter when a command is used on time
                    reset_timeout_counter(interaction.client, interaction.channel_id)

            else:
                team1_mention = get_team_mention(interaction, team1, TEAMS)
                team2_mention = get_team_mention(interaction, team2, TEAMS)

                await interaction.followup.send(
                "The final map will be randomly selected from one of the following map pools, according to both teams' choice:\n- "
                f"{"\n- ".join(selection_state['tournament']['map_pools'])}\n\n"
                f":exclamation: **{team1_mention}** and **{team2_mention}** can finalize the map selection process by using **`/map_final`**.\n\n"
                "-# To invoke the Wildcard, both teams must agree. Otherwise, the selection will default to the Standard map pool.",
                allowed_mentions=discord.AllowedMentions(roles=False))

        # Restarts the timeout counter when a command is used on time
        reset_timeout_counter(interaction.client, interaction.channel_id)

    # Show user the choice of maps to pick
    @map_pick_command.autocomplete('map')
    async def map_pick_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:
        selection_state = state_handler.get(interaction.channel_id)

        if not selection_state:
            return []
        
        map_pools = selection_state["tournament"]["map_pools"]

        standard_maps = [map_key for map_key, map_info in selection_state["remaining_maps"].items() if map_info["pool"] == "Standard"]
        options = standard_maps + (["INVOKE WILDCARD"] if "Wildcard" in map_pools else [])
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

    # Show user the two options (Yes or No)
    @map_pick_command.autocomplete('override')
    async def map_pick_override_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:

        options = ["Yes","No"]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

    # Command for picking maps
    @app_commands.command(name="map_final", description='Choose whether the final map is from the Standard or Wildcard map pool')
    @discord.app_commands.describe(choice="Standard/Wildcard", override="Organizers can override this phase")
    async def map_final_command(self, interaction: discord.Interaction, choice: str, override: str = "No"):
        selection_state = state_handler.get(interaction.channel_id)

        if not selection_state:
            await interaction.response.send_message(
                "Please use `/match` first to start map selection.", ephemeral=True)
            return

        TEAMS = selection_state["tournament"]["teams"]

        team1 = selection_state["teams"]["team1"]
        team2 = selection_state["teams"]["team2"]
        
        if not all(selection_state["bans"].values()):
            await interaction.response.send_message(
                "Teams must complete the banning phase first.", ephemeral=True)
            return

        if not all(selection_state["picks"].values()):
            await interaction.response.send_message(
                "Teams must complete the picking phase first.", ephemeral=True)
            return

        # Allow only the opposing teams to use the command
        if not(
            user_is_on_team(interaction, interaction.user, team1, TEAMS) or
            user_is_on_team(interaction, interaction.user, team2, TEAMS)
        ) and override == "No":
            await interaction.response.send_message(
                "You must belong to one of the opposing teams.", ephemeral=True)
            return

        if not user_can_override(interaction.user) and override == "Yes":
            await interaction.response.send_message(
                "Only organizers can override this phase!", ephemeral=True)
            return

        choice = choice.capitalize()

        if choice not in ["Standard", "Wildcard"]:
            await interaction.response.send_message(
                "Please choose one of the available map pools.", ephemeral=True)
            return

        # Function to check if a map pool has any maps remaining
        def pool_has_maps(pool):
            return any(maps for maps in selection_state["remaining_maps"].values() if maps["pool"] == pool)

        # Validate the choice of map pool
        if not pool_has_maps(choice):
            await interaction.response.send_message(f"No maps left in the {choice} map pool to choose from!", ephemeral=True)
            return

        # Assign the selected choice of map pool to each team
        if user_can_override(interaction.user) and override == "Yes":
            selection_state["final_map_pool"]["team1"] = choice
            selection_state["final_map_pool"]["team2"] = choice
        else:
            choosing_team_key = "team1" if user_is_on_team(interaction, interaction.user, team1, TEAMS) else "team2"
            choosing_team = selection_state["teams"][choosing_team_key]
            choosing_team_mention = get_team_mention(interaction, choosing_team, TEAMS)

            non_choosing_team_key = "team2" if user_is_on_team(interaction, interaction.user, team1, TEAMS) else "team1"
            non_choosing_team = selection_state["teams"][non_choosing_team_key]
            non_choosing_team_mention = get_team_mention(interaction, non_choosing_team, TEAMS)

            selection_state["final_map_pool"][choosing_team_key] = choice

            if not (selection_state["final_map_pool"]["team1"] and selection_state["final_map_pool"]["team2"]):
                await interaction.response.send_message(
                    f"{choosing_team_mention} wants to play a map from the __{choice}__ map pool.\n\n"
                    f":exclamation: Waiting for **{non_choosing_team_mention}** to submit their preference using **`/map_final`**.",
                    allowed_mentions=discord.AllowedMentions(roles=False))
                return

        if selection_state["final_map_pool"]["team1"] and selection_state["final_map_pool"]["team2"]:

            agreed_pool = "Wildcard" if selection_state["final_map_pool"]["team1"] == selection_state["final_map_pool"]["team2"] == "Wildcard" else "Standard"

            # Pull the remaining maps in the selected map pool
            final_maps = [
                map_key for map_key, map_info in selection_state["remaining_maps"].items()
                if map_info["pool"] == agreed_pool
                ]

            selection_state["random_map"] = random.choice(final_maps)

            await interaction.response.send_message(
                f"The final map will be from the __{agreed_pool}__ map pool!\n\n"
                f"Randomly selecting the final map...")

            await send_summary_embed(interaction, selection_state)

        if selection_state["scheduled_event"]["start"] and selection_state["scheduled_event"]["duration"]:
                state_handler.pop(interaction.channel_id, None)
                await clear_timeout(interaction.channel_id)
        else:
            # Restarts the timeout counter when a command is used on time
            reset_timeout_counter(interaction.client, interaction.channel_id)

    # Show user the choice of maps to pick
    @map_final_command.autocomplete('choice')
    async def map_final_choice_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:
        selection_state = state_handler.get(interaction.channel_id)

        if not selection_state:
            return []

        options = selection_state["tournament"]["map_pools"]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

    # Show user the two options (Yes or No)
    @map_final_command.autocomplete('override')
    async def map_final_override_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:

        options = ["Yes","No"]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]
    
    @app_commands.command(name="schedule", description="Create a Discord event for a match")
    @discord.app_commands.describe(start="Start time of match (use @time)", description="Customize the event description or use the tournament's default template", duration="Expected duration of the event in minutes")
    async def schedule_command(self, interaction: discord.Interaction, start: app_commands.Timestamp, description: str = "Customize", duration: int = 120):
        selection_state = state_handler.get(interaction.channel_id)

        if not selection_state:
            await interaction.response.send_message(
                "Teams have not been set. Please use `/match` first to start map selection.", ephemeral=True)
            return
        
        if not user_can_override(interaction.user):
            await interaction.response.send_message(
                "Only organizers can create Discord events.", ephemeral=True)
            return
        
        if description not in ["Customize","Default"]:
            await interaction.response.send_message(
                "Please select either \"Customize\" or \"Default\".", ephemeral=True)
            return
        
        selection_state["scheduled_event"]["start"] = start
        selection_state["scheduled_event"]["duration"] = int(duration)
        
        if description == "Default":
            bracket_url = selection_state["tournament"]["info"]["bracket_url"]
            vods_url = selection_state["tournament"]["info"]["vods_url"]

            added_text = (
                f"Bracket: {bracket_url}\n"
                f"VODs: {vods_url}"
            )

            await schedule_match(interaction, selection_state, added_text)
            
            if selection_state["random_map"]:
                state_handler.pop(interaction.channel_id, None)
                await clear_timeout(interaction.channel_id)
            else:
                # Restarts the timeout counter when a command is used on time
                reset_timeout_counter(interaction.client, interaction.channel_id)
        else:
            event_modal = EventDescription(interaction.channel_id)
        
            await interaction.response.send_modal(event_modal)
    
    # Show user the two options (Yes or No)
    @schedule_command.autocomplete('description')
    async def schedule_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:

        options = ["Customize","Default"]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

async def setup(bot: commands.Bot):
    await bot.add_cog(Tourney(bot))
