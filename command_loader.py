from dotenv import load_dotenv
import os
import discord
from discord import app_commands
from discord.app_commands import cooldown

from bot_instance import bot
import events
from Commands.boosterPearks import customRole, grantrole, imitate
from Commands.funCommands import (
    punch,
    stab,
    good,
    goon,
    dance,
    giveaway,
    forceLowerCase,
    addReactionRole,
    managePrison,
)
from Commands.gameCommands.adminCommands import addMoney, removeMoney, setStatpoints
from Commands.gameCommands.manageMoney import request, donate, balance
from Commands.gameCommands.manageStats import stats, allocate, buyPoints
from Commands.gameCommands.userInteractionCommands import hack

load_dotenv(dotenv_path=".env")
token = os.getenv("bot_token")

events.setup(bot, forceLowerCase.lowercase_locked)

# Booster Commands
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


@bot.tree.command(name="imitate", description="Imitate a user's message (Admin/Owner only)")
@app_commands.describe(user="User to imitate", msg="Message content")
@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
async def imitateCommand(
    interaction: discord.Interaction, user: discord.Member, msg: str
):
    await imitate.imitate(interaction=interaction, user=user, msg=msg)


# Fun Commands
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


@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="goon", description="Goon to someone on the server")
async def goonCommand(interaction: discord.Interaction, user: discord.Member):
    await goon.goon(interaction=interaction, user=user)


@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="dance", description="Hit a cool dance")
async def danceCommand(interaction: discord.Interaction):
    await dance.dance(interaction=interaction)


@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="giveaway", description="Start a giveaway (Admin/Owner only)")
@app_commands.describe(duration="Duration in minutes", prize="Prize", winners="Number of winners")
async def giveawayCommand(
    interaction: discord.Interaction, duration: int, prize: str, winners: int
):
    await giveaway.giveaway(
        interaction=interaction, duration=duration, prize=prize, winners=winners
    )


@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(
    name="forcelowercase", description="Force a member's messages to lowercase (toggle)"
)
@app_commands.describe(member="Member to lock/unlock")
@app_commands.checks.has_permissions(manage_messages=True)
async def forcelowercaseCommand(
    interaction: discord.Interaction, member: discord.Member
):
    await forceLowerCase.forcelowercase(interaction=interaction, member=member)


@bot.tree.command(
    name="addcolorreactionrole", description="Add emoji-role to color reaction message"
)
@app_commands.describe(emoji="Emoji to react with", role="Role to assign")
async def addcolorreactionroleCommand(
    interaction: discord.Interaction,
    target_message_id: str,
    emoji: str,
    role: discord.Role,
):
    await addReactionRole.addcolorreactionrole(
        interaction=interaction,
        target_message_id=target_message_id,
        emoji=emoji,
        role=role,
    )


@bot.tree.command(
    name="manageprisonmember", description="Send or free someone from prison"
)
@app_commands.describe(user="Person you want to lock or free in prison")
async def managePrisonMemberCommand(
    interaction: discord.Interaction, user: discord.Member, time: str | None = None
):
    await managePrison.managePrisonMember(
        interaction=interaction, user=user, time=time
    )


# Game Commands - Admin
@bot.tree.command(
    name="addmoney", description="Give coins to a user (Admin/Owner only)"
)
async def addMoneyCommand(
    interaction: discord.Interaction, user: discord.Member, amount: int
):
    await addMoney.addMoney(interaction=interaction, user=user, amount=amount)


@bot.tree.command(
    name="remove", description="Remove coins from a user (Admin/Owner only)"
)
async def removeCommand(
    interaction: discord.Interaction, user: discord.Member, amount: int
):
    await removeMoney.remove(interaction=interaction, user=user, amount=amount)


@bot.tree.command(name="setstatpoints", description="Set a user's stat points (Admin only)")
@app_commands.describe(user="Target user", amount="New amount of stat points")
async def setstatpointsCommand(
    interaction: discord.Interaction, user: discord.Member, amount: int
):
    await setStatpoints.setstatpoints(
        interaction=interaction, user=user, amount=amount
    )


@bot.tree.command(name="setstat", description="Set a user's stat (Admin only)")
@app_commands.describe(
    user="Target user",
    stat="Which stat to set (intelligence, strength, stealth)",
    amount="New stat value (≥ 0)",
)
async def setstatCommand(
    interaction: discord.Interaction, user: discord.Member, stat: str, amount: int
):
    await setStatpoints.setstat(
        interaction=interaction, user=user, stat=stat, amount=amount
    )


# Game Commands - Money Management
@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="balance", description="Check someone's coin balance")
async def balanceCommand(interaction: discord.Interaction, user: discord.Member):
    await balance.balance(interaction=interaction, user=user)


@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="request", description="Request coins from another user")
async def requestCommand(
    interaction: discord.Interaction, user: discord.Member, amount: int, reason: str
):
    await request.request(
        interaction=interaction, user=user, amount=amount, reason=reason
    )


@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="donate", description="Send coins to another user")
async def donateCommand(
    interaction: discord.Interaction, user: discord.Member, amount: str
):
    await donate.donate(interaction=interaction, user=user, amount=amount)


# Game Commands - Stats Management
@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="stats", description="Show your stats & unspent points")
async def statsCommand(
    interaction: discord.Interaction, user: discord.Member | None = None
):
    await stats.stats(interaction=interaction, user=user)


@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="allocate", description="Spend stat-points to increase a stat")
@app_commands.describe(
    stat="Which stat? (intelligence/strength/stealth)",
    points="How many points to allocate",
)
async def allocateCommand(
    interaction: discord.Interaction, stat: str, points: int
):
    await allocate.allocate(interaction=interaction, stat=stat, points=points)


@cooldown(rate=1, per=2.0, key=lambda i: i.user.id)
@bot.tree.command(name="buypoints", description="Buy stat-points with coins")
async def buypointsCommand(interaction: discord.Interaction, amount: int = 1):
    await buyPoints.buypoints(interaction=interaction, amount=amount)


# Game Commands - User Interaction
@cooldown(rate=1, per=2400, key=lambda i: i.user.id)
@bot.tree.command(
    name="hack", description="Hack the bank to win coins (needs intelligence ≥ 3)"
)
async def hackCommand(interaction: discord.Interaction):
    await hack.hack(interaction=interaction)


# Run the Bot
bot.run(token)
