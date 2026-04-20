# Matcha
Matcha is a match manager on Discord for competitive communities that handles:
- Map selection for tournament matches
- Queue management for pick-up games (PUGs)

While it was originally developed for organizing competition in the video game **NEOTOKYO°**, Matcha is now being expanded to support additional games, map pools, and tournament formats. It's aimed at titles that lack built‑in matchmaking or map‑voting support for tournament play - especially in scenarios where you want to conduct map selection ahead of a scheduled match.

---

## Tournament Map Selection

The bot is designed for Discord servers where teams and players already have roles, and where map pools may change between tournaments. The number of maps you can ban or pick, as well as the order in which you do so, may vary depending on the tournament.

> [!IMPORTANT]
> The current version of the bot assumes that each team bans one map and picks one map for each matchup.

The tournament map selection process is as follows:
1. Two opposing teams register themselves and initiate a coin toss.
2. The team that wins the coin toss will determine which team will ban first in the banning phase.
3. During the banning phase, each team bans one map.
4. During the picking phase, each team picks one map (but team order is reversed for this phase!).
5. The third map is randomly selected by the bot.
   - Optional - choose the map pool; only if more than one map pool is in the tournament.
   - From **Standard** by default, from **Wildcard** if both teams agree.

---

## PUG Queue

The PUG queue system is designed to have all the essential features available in a single embed, the **PUG Panel**. Additional bonus options are planned for the future and will be available from the "Actions" menu.

Players can currently:
- Join and leave the queue
- See who is currently queued
- Ping the queue (with cooldown) when enough players are ready
- Receive a DM notification to gather in voice and form teams
- Access bonus options by clicking the Actions button in the PUG Panel

**PUG Panel Actions Button Menu**
- **Ping Queue**
  - DM players in the queue.
- **Map Vote** - Planned (tentative)
  - Start a map vote for the PUG.
- **Scramble** - Planned (tentative)
  - Randomize queued players into two teams.

---

## Useful Commands

### Help
- **`/help pug`** Help options for PUG queue
- **`/help tourney`** Help options for tournament map selection

### Tournament Commands
- **`/clear`** Clears the bot and resets the map selection process.
- **`/match`** Begin map selection by inputting two teams and initiating a coin toss.
    - The bot can load other tournaments besides those listed by this command. Simply input its name (e.g. "WW25") when using the command.
- **`/order`** Select either "BAN first, PICK second" or "BAN second, PICK first" to decide your team's ban order.
- **`/map_ban`** Select a map to ban from the remaining <ins>Standard</ins> map pool.
- **`/map_pick`** Select a map to pick from the remaining <ins>Standard</ins> map pool or **INVOKE WILDCARD**. Invoking the wildcard will randomly select a map from the remaining <ins>Wildcard</ins> map pool.
- **`/map_final`** Select either "Standard" or "Wildcard" to randomly select the final map from either of these map pools.
- **`/schedule`** Schedule a Discord event on the server for the match. Organizers and above only.

### PUG Commands
- **`/pug`** Opens the PUG Panel.
- **`/join`** Join the PUG queue.
- **`/leave`** Leave the PUG queue.
- **`/remove`** Remove a player from the PUG queue.

---

## Hosting the Bot Yourself

To host the **Matcha** bot yourself, follow these steps:

1. **Configuration**
   - Create an `.env` file in the root directory of the project. This should include your Discord bot token (`DISCORD_TOKEN`) and your Discord guild ID (`DISCORD_GUILD`).

2. **Adding Your Own Tournaments**
   - To add your own tournament, place your tournament file in the `tournaments/` directory. Ensure that your file follows the same format as the existing files in that directory. The bot will automatically load the teams and maps from your newly added file.

3. **Define Your Tournament**:
   - **`INFO`** - Tournament name, start date, map pools etc.
   - **`MAPS`** - Map names, versions etc.
   - **`TEAMS`** - Team names, clan tags, roles etc.

4. **Manage Permissons**
   - Grant the bot these Discord permissions for full functionality:
     - **View Channels**: Allows it to update embeds with the current number of players in the PUG queue.
     - **Manage Nicknames**: Allows it to change its nickname to display the current number of players in the PUG queue.
     - **Create Events**: Allows it to create events on the server for scheduled matches.

5. **Configure Your Commands**
   - You may only want one of the two major functions of this bot. You can restrict usage of the bot's commands to specific channels, roles, and users.
   - Go to the following settings and edit the commands accordingly:
     - **Server Settings** -> **Apps** -> **Integrations** -> **Command Permissions**

6. **Run the Bot**

---

## Future Developments
- [x] Add support for queueing pick-up games
- [x] Add support for scheduling events
- [ ] Add views (buttons, dropdowns) to map selection
- [ ] Add data persistence (save data across restarts)
- [ ] Make bot format-agnostic and allow support for more types of tournaments (or even different games)
