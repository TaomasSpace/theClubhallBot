from dotenv import load_dotenv
import os
import discord
from discord import app_commands
from discord.app_commands import cooldown
from bot_instance import bot
from Commands.boosterPearks import customRole, grantrole
from Commands.funCommands import punch, stab, good

load_dotenv(dotenv_path=".env")
token = os.getenv("bot_token")

@bot.tree.command(name="customrole", description="Create or update your booster role")
@app_commands.describe(name="Name of your role", color="Hex color like #FFAA00")
@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
async def customroleCommand(interaction: discord.Interaction, name: str, color: str):
    await customRole.customrole(interaction=interaction, name=name, color=color)

@bot.tree.command(
    name="grantrole",
    description="Give your custom role to another user",
)
@app_commands.describe(target="User to give your custom role to")
@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
async def grantroleCommand(interaction: discord.Interaction, target: discord.Member):
    await grantrole.grantrole(interaction=interaction, target=target)

@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="punch", description="Punch someone with anime style")
async def punchCommand(interaction: discord.Interaction, user: discord.Member):
    await punch.punch(interaction=interaction, user=user)

@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="stab", description="Stab someone with anime style")
async def stabCommand(interaction: discord.Interaction, user: discord.Member):
    await stab.stab(interaction=interaction, user=user)

@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="good", description="Tell someone they are a good boy/girl")
async def goodCommand(interaction: discord.Interaction, user: discord.Member):
    await good.good(interaction=interaction, user=user)

bot.run(token)
