import discord
from discord.ext import commands

from config import *
from Commands.fun_commands import setup as setup_fun, lowercase_locked
from Commands.booster_commands import setup as setup_booster
from Commands.economy_commands import setup as setup_economy
from Commands.stats_commands import setup as setup_stats
from Commands.action_commands import setup as setup_action
from Commands.admin_commands import setup as setup_admin
from Commands.antinuke_commands import setup as setup_antinuke
from Commands.setup_wizard import setup as setup_wizard
from Commands.explain_commands import setup as setup_explain
import events
import anti_nuke


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

setup_fun(bot)
setup_booster(bot)
setup_economy(bot)
setup_stats(bot, ROD_SHOP)
setup_action(bot)
setup_admin(bot)
setup_antinuke(bot)
setup_wizard(bot)
setup_explain(bot)
events.setup(bot, lowercase_locked)
anti_nuke.setup(bot)

with open("code.txt", "r") as file:
    TOKEN = file.read().strip()

bot.run(TOKEN)
