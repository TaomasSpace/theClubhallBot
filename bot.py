import discord
from discord.ext import commands

from config import *
from commands.fun_commands import setup as setup_fun, lowercase_locked
from commands.booster_commands import setup as setup_booster
from commands.economy_commands import setup as setup_economy
from commands.stats_commands import setup as setup_stats
from commands.action_commands import setup as setup_action
from commands.admin_commands import setup as setup_admin
from commands.antinuke_commands import setup as setup_antinuke
from commands.setup_wizard import setup as setup_wizard
from commands.explain_commands import setup as setup_explain
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
setup_stats(bot, events.rod_shop)
setup_action(bot)
setup_admin(bot)
setup_antinuke(bot)
setup_wizard(bot)
setup_explain(bot)
events.setup(bot, lowercase_locked)
anti_nuke.setup(bot)

# Expose all slash commands as prefix commands
for app_cmd in bot.tree.get_commands():
    bot.add_command(app_cmd.to_command())

with open("code.txt", "r") as file:
    TOKEN = file.read().strip()

bot.run(TOKEN)
