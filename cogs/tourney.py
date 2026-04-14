import asyncio
import importlib
import logging
import pkgutil
import random
import sys
from datetime import datetime
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
modules_with_dates = []

for _, name, _ in pkgutil.iter_modules([str(TOURNAMENTS_DIR)]):
    module = importlib.import_module(f"{"tournaments"}.{name}")

    # Parse the date string
    full_name = module.INFO['full_name']
    start_date_str = module.INFO['start_date']
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    map_pools = module.INFO['map_pools']
    modules_with_dates.append((name, full_name, start_date, map_pools))

tournaments = sorted(modules_with_dates, key=lambda x: x[2], reverse=True)

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

        channel = await bot.fetch_channel(channel_id)
        await channel.send(
            f"Map selection will be cleared in {TIMEOUT_NOTICE/(60*60)} hour(s) if no further commands are used.")

        await asyncio.sleep(TIMEOUT_NOTICE)

        # Clear map selection
        state_handler.pop(channel_id, None)
        timeout_tasks.pop(channel_id, None)

        await channel.send(
            f"Map selection has timed out after {TIMEOUT_DURATION/(60*60)} hours of inactivity and has been cleared.")

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

# Function to resolve interaction channel (bot must only take inputs from the channel it is being used in)
def get_state(channel_id):
    if channel_id not in state_handler:
        state_handler[channel_id] = {
            "tournament": {"info": None, "map_pool": None, "team_roles": None, "map_pools": None},
            "teams": {"team1": None, "team2": None},
            "coin_toss_winner": None,
            "ban_order": None,
            "bans": {"team1": [], "team2": []},
            "picks": {"team1": [], "team2": []},
            "remaining_maps": {},
            "final_map_pool": {"team1": None, "team2": None},
            "random_map": None
        }
    return state_handler[channel_id]

# Function to resolve map name (checks map names and aliases)
def resolve_map_name(map_name, MAPS):
    for official_name, map_info in MAPS.items():
        if map_name.lower() == official_name.lower():
            return official_name
        for name in map_info['base_name']:
            if map_name.lower() == name.lower():
                return official_name
        for alias in map_info['aliases']:
            if map_name.lower() == alias.lower():
                return official_name
    return None

# Function to get base name for map
def get_base_name(map_key, MAPS):
    base_names = MAPS[map_key]['base_name']
    if base_names:
        return f"{base_names[0]}"
    return "Unknown Map"

# Check if a user has the required perms to bypass team restrictions
def has_admin_privileges(member):
    return (
        any(role.permissions.administrator for role in member.roles)
        or any(role.name == "Organizer" for role in member.roles))

# Function to resolve team name (returns full team name)
def resolve_team_name(team_name, TEAMS):
    if team_name == "Mixed Team":
        return "Mixed Team"
    for full_name, team_info in TEAMS.items():
        if team_name.lower() == team_info["tag"].lower():
            return full_name
        if team_name.lower() == full_name.lower() or team_name.lower() == team_info["name"].lower():
            return full_name
    return None

# Function to get team name without clan tag
def trim_team_name(team_name: str, TEAMS) -> str | None:
    team_info = TEAMS.get(team_name)
    return team_info["name"] if team_info else None

# Function to check if user belongs to a team
def user_is_on_team(member: discord.Member, team_name, TEAMS):
    if team_name in ["Mixed Team", "Mixed Team A", "Mixed Team B"]:
        return True

    team_name_lower = team_name.lower()
    if any(role.name.lower() == team_name_lower for role in member.roles):
        return True

    team_role_id = TEAMS[team_name]["id"]
    if any(role.id == team_role_id for role in member.roles):
        return True

# Function to build and send the embed with the match details
async def send_summary_embed(interaction: discord.Interaction, selection_state):

    MAPS = selection_state["tournament"]["maps"]
    map_pools = selection_state["tournament"]["map_pools"]
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
        title=f"{team1} vs {team2}",
        description=":white_check_mark: Match is ready to go!",
        colour=discord.Colour.from_rgb(252, 155, 40)
        )

    # Function for formatting map picks/bans in embed fields
    def format_selections(maps, dash=False):
        return "\n".join(f"{"- " if dash else ""}{get_base_name(map, MAPS)} `{map}`" for map in maps)

    # Add fields to the embed for picks...
    first_map = format_selections(team1_picks) if team1 == second_to_ban else format_selections(team2_picks)
    second_map = format_selections(team2_picks) if team2 == first_to_ban else format_selections(team1_picks)
    third_map = f"{get_base_name(selection_state["random_map"], MAPS)} `{selection_state["random_map"]}`"

    embed_maps = (
        f"1. {first_map}\n"
        f"2. {second_map}\n"
        f"3. {third_map}"
        )

    if len(map_pools) > 1:
        pool_info = f" ({MAPS[selection_state["random_map"]]["map_pool"]})"
    else:
        pool_info = ""

    embed_teams = (
        f"1. {trim_team_name(second_to_ban, TEAMS)}\n"
        f"2. {trim_team_name(first_to_ban, TEAMS)}\n"
        f"3. *Random*{pool_info}"
        )

    embed.add_field(name="\u00AD", value="\u00AD", inline=False)

    embed.add_field(name="Maps", value=embed_maps, inline=True)
    embed.add_field(name="Picked by", value=embed_teams, inline=True)

    embed.add_field(name="\u00AD", value="\u00AD", inline=False)

    # ...and bans
    embed.add_field(
        name=f"{trim_team_name(team1, TEAMS)} Bans",
        value=format_selections(team1_bans, dash=True),
        inline=True)
    embed.add_field(
        name=f"{trim_team_name(team2, TEAMS)} Bans",
        value=format_selections(team2_bans, dash=True),
        inline=True)

    await asyncio.sleep(2)
    await interaction.followup.send(embed=embed)

    state_handler.pop(interaction.channel_id, None)

class Tourney(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Command to clear the selection state
    @app_commands.command(name="clear", description="Clears the map selection state")
    async def clear_command(self, interaction: discord.Interaction):
        selection_state = get_state(interaction.channel_id)
        TEAMS = selection_state["tournament"]["teams"]

        if selection_state["teams"] and not (has_admin_privileges(interaction.user)
                or user_is_on_team(interaction.user, selection_state["teams"]["team1"], TEAMS)
                or user_is_on_team(interaction.user, selection_state["teams"]["team2"], TEAMS)):
            await interaction.response.send_message(
                f"Only **{selection_state["teams"]["team1"]}**, **{selection_state["teams"]["team2"]}**, or an Organizer can clear this map selection.", ephemeral=True)
            return

        state_handler.pop(interaction.channel_id, None)
        await clear_timeout(interaction.channel_id)
        await interaction.response.send_message(
            "Map selection has been cleared. Use **`/match`** to start again.")

    # Command to start map selection, with team assignment and coin toss
    @app_commands.command(name="match", description="Set the tournament and opposing teams for a match")
    @discord.app_commands.describe(pool="Name of map pool you want to select from", team1="Name of team 1", team2="Name of team 2")
    async def match_command(self, interaction: discord.Interaction, pool: str, team1: str, team2: str):
        selection_state = get_state(interaction.channel_id)

        # Dynamically import dictionary of map pool based on user input
        try:
            for name, full_name, _, map_pools in tournaments:
                if pool.lower() == name.lower() or pool.lower() == full_name.lower():
                    module_name = name
                    break

            tournament = importlib.import_module(f"tournaments.{module_name}")

            MAPS = tournament.MAPS
            TEAMS = tournament.TEAMS

        except ImportError:
            await interaction.response.send_message(
                f"ImportError: Could not import the map pool: {pool}.", ephemeral=True)
            return

        except AttributeError:
            await interaction.response.send_message(
                "AttributeError: Does not contain a valid map pool.", ephemeral=True)
            return

        resolved_team1 = resolve_team_name(team1, TEAMS)
        resolved_team2 = resolve_team_name(team2, TEAMS)

        # If user is not an organizer they should be in one of the opposing teams
        if not has_admin_privileges(interaction.user):
            if not (user_is_on_team(interaction.user, resolved_team1, TEAMS)
                    or user_is_on_team(interaction.user, resolved_team2, TEAMS)
                    or "Mixed Team" in {resolved_team1, resolved_team2}):
                await interaction.response.send_message(
                    "You must belong to one of the selected teams. Otherwise, pick \"Mixed Team\".", ephemeral=True)
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
        selection_state["tournament"] = {"info": tournament.INFO, "maps": tournament.MAPS, "teams": tournament.TEAMS, "map_pools": map_pools}
        selection_state["teams"] = {"team1": resolved_team1, "team2": resolved_team2}
        selection_state["coin_toss_winner"] = None
        selection_state["ban_order"] = None
        selection_state["bans"] = {"team1": [], "team2": []}
        selection_state["picks"] = {"team1": [], "team2": []}
        selection_state["remaining_maps"] = MAPS.copy()
        selection_state["final_map_pool"] = {"team1": None, "team2": None}
        selection_state["random_map"] = None

        # Announce coin toss winner
        selection_state["coin_toss_winner"] = random.choice([resolved_team1, resolved_team2])

        if resolved_team1 == resolved_team2:
            coin_toss_winner = selection_state["coin_toss_winner"]
        else:
            coin_toss_winner = trim_team_name(selection_state['coin_toss_winner'], TEAMS)

        await interaction.response.send_message(
            f"**{resolved_team1}** vs **{resolved_team2}**\n\n"
            f"Map selection started! The tournament is **{pool}**.\n\n"
            "Performing a coin toss to determine which team decides the ban order...")

        await asyncio.sleep(2)
        await interaction.followup.send(
            f"{random.choice([":coin:", ":older_man:", ":church:"])} **{coin_toss_winner}** wins the coin toss! Pick your team's ban/pick order using **`/order`**")

        server_role_ids = {role.id for role in interaction.guild.roles}
        server_role_names_lower = {role.name.lower() for role in interaction.guild.roles}

        missing_roles = [
            name for name, info in TEAMS.items()
            if info["id"] not in server_role_ids and name.lower() not in server_role_names_lower
        ]

        if missing_roles:
            await interaction.followup.send(
                "**WARNING: The following team roles are missing from your server:**\n- "
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

        options = [full_name for _, full_name, _, _ in tournaments][:2]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

    # Show user choice of teams
    @match_command.autocomplete('team1')
    async def match_team1_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:

        pool_name = interaction.namespace.pool.lower()
        module_name = next(name for name, full_name, _, _ in tournaments if pool_name == full_name.lower())
        tournament = importlib.import_module(f"tournaments.{module_name}")
        TEAMS = tournament.TEAMS

        options = list(TEAMS.keys()) + ["Mixed Team"]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

    @match_command.autocomplete('team2')
    async def match_team2_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:

        pool_name = interaction.namespace.pool.lower()
        module_name = next(name for name, full_name, _, _ in tournaments if pool_name == full_name.lower())
        tournament = importlib.import_module(f"tournaments.{module_name}")
        TEAMS = tournament.TEAMS

        options = list(TEAMS.keys()) + ["Mixed Team"]
        return [
            discord.app_commands.Choice(name=opt, value=opt)
            for opt in options if current.lower() in opt
        ]

    # Command for the coin toss winner to pick the ban order
    @app_commands.command(name='order', description='Choose whether your team bans first or second')
    @discord.app_commands.describe(choice="Ban first and pick second OR ban second and pick first", override="Organizers can override this phase")
    async def order_command(self, interaction: discord.Interaction, choice: str, override: str = "No"):
        selection_state = get_state(interaction.channel_id)
        TEAMS = selection_state["tournament"]["teams"]

        team1 = selection_state["teams"]["team1"]
        team2 = selection_state["teams"]["team2"]

        if selection_state["coin_toss_winner"] is None:
            await interaction.response.send_message(
                "No coin toss winner! Please use **`/match`** first to select teams.", ephemeral=True)
            return

        if selection_state["ban_order"]:
            await interaction.response.send_message(
                "The ban order has already been decided!", ephemeral=True)
            return

        # Check if user is part of the team that won the coin toss
        if not user_is_on_team(interaction.user, selection_state["coin_toss_winner"], TEAMS) and not has_admin_privileges(interaction.user):
            await interaction.response.send_message(
                f"Only a member of **{trim_team_name(selection_state['coin_toss_winner'], TEAMS)}** can decide the ban/pick order.",
                ephemeral=True)
            return

        if choice not in ["BAN first, PICK second", "BAN second, PICK first"]:
            await interaction.response.send_message(
                "Please choose one of the given options.", ephemeral=True)
            return

        if not has_admin_privileges(interaction.user) and override == "Yes":
            await interaction.response.send_message(
                "Only organizers can override this phase!", ephemeral=True)
            return

        if selection_state["coin_toss_winner"] == team1:
            selection_state["ban_order"] = [team1, team2] if choice == "BAN first, PICK second" else [team2, team1]
        else:
            selection_state["ban_order"] = [team2, team1] if choice == "BAN first, PICK second" else [team1, team2]

        await interaction.response.send_message(
            f"{trim_team_name(selection_state["coin_toss_winner"], TEAMS)} has chosen to {choice.lower()}.\n\n"
            f"**{trim_team_name(selection_state['ban_order'][0], TEAMS)}**, please ban a map using **`/map_ban`**.")

        # Restarts the timeout counter when a command is used on time
        reset_timeout_counter(interaction.client, interaction.channel_id)

    # Show user the two options (First or Second)
    @order_command.autocomplete('choice')
    async def order_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:

        options = ["BAN first, PICK second", "BAN second, PICK first"]
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
        selection_state = get_state(interaction.channel_id)
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
            selection_state["remaining_maps"] = MAPS.copy()
            await interaction.response.send_message(
                "Illegal selection state detected. Resetting ban phase.\n\n"
                f"**{trim_team_name(selection_state['ban_order'][0], TEAMS)}**, please ban a map using **`/map_ban`**.")
            return

        elif (team1_bans and not team2_bans) or (not team1_bans and team2_bans):
            banning_team = second_to_ban

        if banning_team is None:
            await interaction.response.send_message(
                "You cannot ban any more maps.", ephemeral=True)
            return

        # Allow only the current team to ban
        if not user_is_on_team(interaction.user, banning_team, TEAMS) and not has_admin_privileges(interaction.user):
            await interaction.response.send_message(
                f"Only {trim_team_name(banning_team, TEAMS)} can ban right now.", ephemeral=True)
            return

        if not has_admin_privileges(interaction.user) and override == "Yes":
            await interaction.response.send_message(
                "Only organizers can override this phase!", ephemeral=True)
            return

        banning_team_key = "team1" if banning_team == team1 else "team2"

        if selection_state["bans"][banning_team_key]:
            await interaction.response.send_message(
                f"{trim_team_name(banning_team, TEAMS)} has already banned a map!", ephemeral=True)
            return

        standard_maps = [map_key for map_key, map_info in selection_state["remaining_maps"].items() if map_info["map_pool"] == "Standard"]
        banned_map = resolve_map_name(map, MAPS)

        if banned_map not in standard_maps:
            await interaction.response.send_message(
                "Please choose a remaining map from the Standard map pool:\n" + "\n".join([f"- {map}" for map in standard_maps]))
            return

        selection_state["bans"][f"{banning_team_key}"].append(banned_map)
        selection_state["remaining_maps"].pop(banned_map)

        if not all(selection_state["bans"].values()):
            next_team = second_to_ban if banning_team == first_to_ban else first_to_ban
            await interaction.response.send_message(
                f"{trim_team_name(banning_team, TEAMS)} has banned: **{banned_map}**\n\n"
                f"**{trim_team_name(next_team, TEAMS)}**, please ban a map using **`/map_ban`**.")

        elif all(selection_state["bans"].values()):
            picking_team = second_to_ban
            await interaction.response.send_message(
                f"{trim_team_name(banning_team, TEAMS)} has banned: **{banned_map}**\n\n"
                ":ballot_box_with_check: Banning phase complete!\n\n"
                f"**{trim_team_name(picking_team, TEAMS)}**, please pick a map using **`/map_pick`**.")

        # Restarts the timeout counter when a command is used on time
        reset_timeout_counter(interaction.client, interaction.channel_id)

    # Show user the choice of maps to ban
    @map_ban_command.autocomplete('map')
    async def map_ban_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:
        selection_state = get_state(interaction.channel_id)

        options = [map_key for map_key, map_info in selection_state["remaining_maps"].items() if map_info["map_pool"] == "Standard"]
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
        selection_state = get_state(interaction.channel_id)
        MAPS = selection_state["tournament"]["maps"]
        map_pools = selection_state["tournament"]["map_pools"]
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

        # Allow only the current team to ban
        if not user_is_on_team(interaction.user, picking_team, TEAMS) and not has_admin_privileges(interaction.user):
            await interaction.response.send_message(
                f"Only {trim_team_name(picking_team, TEAMS)} can pick a map right now.", ephemeral=True)
            return

        if not has_admin_privileges(interaction.user) and override == "Yes":
            await interaction.response.send_message(
                "Only organizers can override this phase!", ephemeral=True)
            return

        team_key = "team1" if picking_team == team1 else "team2"

        if "INVOKE WILDCARD" in map:

            wildcard_maps = [map_key for map_key, map_info in selection_state["remaining_maps"].items() if map_info["map_pool"] == "Wildcard"]

            if not wildcard_maps:
                await interaction.response.send_message(
                    "No Wildcard maps remaining in the map pool, please enter a different map.", ephemeral=True)
                return

            else:
                picked_map = random.choice(wildcard_maps)
                added_text = "invoked the Wildcard! Their pick will be"

        else:
            picked_map = resolve_map_name(map, MAPS)
            standard_maps = [map_key for map_key, map_info in selection_state["remaining_maps"].items() if map_info["map_pool"] == "Standard"]
            added_text = "picked"

            if picked_map not in standard_maps:
                await interaction.response.send_message(
                    "Please choose a remaining map from the pool:\n" + "\n".join([f"- {map}" for map in standard_maps] + ["- INVOKE WILDCARD"]))
                return

        # Prevent a team from picking twice
        if selection_state["picks"][team_key]:
            await interaction.response.send_message(
                f"{trim_team_name(picking_team, TEAMS)} has already picked a map: **{selection_state['picks'][team_key]}**. You cannot pick again.",
                ephemeral=True)
            return

        # Once map is validated, it is saved as a map pick and removed from the remaining map pool
        selection_state["picks"][team_key].append(picked_map)
        selection_state["remaining_maps"].pop(picked_map)

        if not all(selection_state["picks"].values()):
            next_team = first_to_ban if picking_team == second_to_ban else second_to_ban
            await interaction.response.send_message(
                f"{trim_team_name(picking_team, TEAMS)} has {added_text}: **{picked_map}**\n\n"
                f"**{trim_team_name(next_team, TEAMS)}**, please pick a map using **`/map_pick`**.")

        if all(selection_state["picks"].values()):
            await interaction.response.send_message(
                f"{trim_team_name(picking_team, TEAMS)} has {added_text}: **{picked_map}**\n\n"
                ":ballot_box_with_check: Picking phase complete!\n\n")
            if len(map_pools) == 1:
                final_maps = list(selection_state["remaining_maps"].keys())
                selection_state["random_map"] = random.choice(final_maps)

                await asyncio.sleep(0.5)
                await interaction.followup.send(
                    "Randomly selecting the final map...")

                await send_summary_embed(interaction, selection_state)

            else:
                await interaction.followup.send(
                "The final map will be randomly selected from one of the following map pools, according to both teams' choice:\n- "
                f"{"\n- ".join(selection_state['map_pools'])}\n\n"
                f"**{trim_team_name(team1, TEAMS)}** and **{trim_team_name(team2, TEAMS)}** can finalize the map selection process by using **`/map_final`**.\n\n"
                "-# To invoke the Wildcard, both teams must agree. Otherwise, the selection will default to the Standard map pool.")

        # Restarts the timeout counter when a command is used on time
        reset_timeout_counter(interaction.client, interaction.channel_id)

    # Show user the choice of maps to pick
    @map_pick_command.autocomplete('map')
    async def map_pick_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:
        selection_state = get_state(interaction.channel_id)
        map_pools = selection_state["tournament"]["map_pools"]

        standard_maps = [map_key for map_key, map_info in selection_state["remaining_maps"].items() if map_info["map_pool"] == "Standard"]
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
        selection_state = get_state(interaction.channel_id)
        TEAMS = selection_state["tournament"]["teams"]

        team1 = selection_state["teams"]["team1"]
        team2 = selection_state["teams"]["team2"]

        # Allow only the opposing teams to use the command
        if not(
            has_admin_privileges(interaction.user) or
            user_is_on_team(interaction.user, team1, TEAMS) or
            user_is_on_team(interaction.user, team2, TEAMS)
        ):
            await interaction.response.send_message(
                "You must belong to one of the opposing teams.", ephemeral=True)
            return

        if not has_admin_privileges(interaction.user) and override == "Yes":
            await interaction.response.send_message(
                "Only organizers can override this phase!", ephemeral=True)
            return

        if not all(selection_state["bans"].values()):
            await interaction.response.send_message(
                "Teams must complete the banning phase first.", ephemeral=True)
            return

        if not all(selection_state["picks"].values()):
            await interaction.response.send_message(
                "Teams must complete the picking phase first.", ephemeral=True)
            return

        choice = choice.capitalize()

        if choice not in ["Standard", "Wildcard"]:
            await interaction.response.send_message(
                "Please choose one of the available map pools.", ephemeral=True)
            return

        # Function to check if a map pool has any maps remaining
        def pool_has_maps(pool):
            return any(maps for maps in selection_state["remaining_maps"].values() if maps["map_pool"] == pool)

        # Validate the choice of map pool
        if not pool_has_maps(choice):
            await interaction.response.send_message(f"No maps left in the {choice} map pool to choose from!", ephemeral=True)
            return

        # Assign the selected choice of map pool to each team
        if has_admin_privileges(interaction.user) and override == "Yes":
            selection_state["final_map_pool"]["team1"] = choice
            selection_state["final_map_pool"]["team2"] = choice
        else:
            choosing_team_key = "team1" if user_is_on_team(interaction.user, team1, TEAMS) else "team2"
            non_choosing_team_key = "team2" if user_is_on_team(interaction.user, team1, TEAMS) else "team1"
            selection_state["final_map_pool"][choosing_team_key] = choice

        if selection_state["final_map_pool"]["team1"] and selection_state["final_map_pool"]["team2"]:

            agreed_pool = "Wildcard" if selection_state["final_map_pool"]["team1"] == selection_state["final_map_pool"]["team2"] == "Wildcard" else "Standard"

            # Pull the remaining maps in the selected map pool
            final_maps = [
                map_key for map_key, map_info in selection_state["remaining_maps"].items()
                if map_info["map_pool"] == agreed_pool
                ]

            selection_state["random_map"] = random.choice(final_maps)

            await interaction.response.send_message(
                f"The final map will be from the __{agreed_pool}__ map pool!\n\n"
                f"Randomly selecting the final map...")

            await send_summary_embed(interaction, selection_state)

        else:
            await interaction.response.send_message(
                f"{trim_team_name(selection_state['teams'][choosing_team_key], TEAMS)} wants to play a map from the __{choice}__ map pool.\n\n"
                f"Waiting for **{trim_team_name(selection_state['teams'][non_choosing_team_key], TEAMS)}** to submit their preference using **`/map_final`**.")

        # Restarts the timeout counter when a command is used on time
        reset_timeout_counter(interaction.channel_id, interaction)

    # Show user the choice of maps to pick
    @map_final_command.autocomplete('choice')
    async def map_final_choice_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:
        selection_state = get_state(interaction.channel_id)


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

async def setup(bot: commands.Bot):
    await bot.add_cog(Tourney(bot))
