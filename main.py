import asyncio
import logging
import os
from logging.handlers import TimedRotatingFileHandler

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables including discord token and server ID(s)
load_dotenv()
token = os.getenv("DISCORD_TOKEN")
server = int(os.getenv("DISCORD_GUILD", 0))

# Log errors/debug info
try:
    os.mkdir("logs")
except OSError:
    pass

handler = TimedRotatingFileHandler(
    "logs/discord.log", when="midnight", interval=1, backupCount=3, encoding="utf-8"
)

handler.suffix = "%Y-%m-%d"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[handler, logging.StreamHandler()]
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class Matcha(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_bot(self):
        await self.wait_until_ready()

        # Set presence
        await self.change_presence(activity=discord.Game(name="/help | Brew your next match!"))
        
        # Reset nickname
        for guild in self.guilds:
            me = guild.me
            await me.edit(nick=None)
        
        print(f"Nickname successfully reset in: {', '.join(guild.name for guild in self.guilds)}")
        
        print("Matcha's all warmed up and ready to go!")

    async def setup_hook(self):
        for filename in os.listdir("./cogs"):
            if (
                filename.endswith(".py")
                and not filename.endswith("dev.py")
                and filename != "__init__.py"
            ):
                await self.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename}")

        asyncio.create_task(self.setup_bot())

        # guild = discord.Object(id=server)

        # # Clear command tree
        # self.tree.clear_commands(guild=guild)

        # Global sync
        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands" + (f" to guild {server}" if 'guild' in locals() else ""))

bot = Matcha()
bot.run(token)
