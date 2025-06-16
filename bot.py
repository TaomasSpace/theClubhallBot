import discord
from discord.ext import commands

from config import *
from commands.fun_commands import setup as setup_fun, lowercase_locked
from commands.booster_commands import setup as setup_booster
from commands.economy_commands import setup as setup_economy
from commands.stats_commands import setup as setup_stats
import events

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

setup_fun(bot)
setup_booster(bot)
setup_economy(bot)
setup_stats(bot, events.rod_shop)
events.setup(bot, lowercase_locked)

with open("code.txt", "r") as file:
    TOKEN = file.read().strip()

bot.run(TOKEN)
