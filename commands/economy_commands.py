import asyncio

import discord
from discord import app_commands, ui
from discord.ext import commands
from datetime import datetime, timedelta
from random import random
from config import ADMIN_ROLE_ID, WEEKLY_REWARD, DAILY_REWARD
from db.DBHelper import (
    register_user,
    safe_add_coins,
    get_money,
    set_money,
    set_max_coins,
    get_top_users,
    get_last_weekly,
    set_last_weekly,
    get_last_claim,
    set_last_claim,
)
from utils import has_role

class RequestView(ui.View):
    def __init__(self, sender_id: int, receiver_id: int, amount: int):
        super().__init__(timeout=60)
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount

    @ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message("This request isn't for you.", ephemeral=True)
            return
        sender_balance = get_money(str(self.sender_id))
        receiver_balance = get_money(str(self.receiver_id))
        if receiver_balance < self.amount:
            await interaction.response.send_message(
                "You don't have enough clubhall coins to accept this request.", ephemeral=True
            )
            return
        set_money(str(self.receiver_id), receiver_balance - self.amount)
        set_money(str(self.sender_id), sender_balance + self.amount)
        await interaction.response.edit_message(
            content=f"✅ Request accepted. {self.amount} clubhall coins sent!",
            view=None,
        )

    @ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message("This request isn't for you.", ephemeral=True)
            return
        await interaction.response.edit_message(content="❌ Request declined.", view=None)


def setup(bot: commands.Bot):
    @bot.tree.command(name="money", description="Check your clubhall coin balance")
    async def money(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        register_user(user_id, interaction.user.display_name)
        await interaction.response.send_message(
            f"You have {get_money(user_id)} clubhall coins.", ephemeral=True
        )

    @bot.tree.command(name="balance", description="Check someone else's clubhall coin balance")
    async def balance(interaction: discord.Interaction, user: discord.Member):
        register_user(str(user.id), user.display_name)
        money_amt = get_money(str(user.id))
        await interaction.response.send_message(
            f"{user.display_name} has {money_amt} clubhall coins.", ephemeral=False
        )

    @bot.tree.command(name="give", description="Give coins to a user (Admin/Owner only)")
    async def give(interaction: discord.Interaction, user: discord.Member, amount: int):
        if not has_role(interaction.user, ADMIN_ROLE_ID):
            await interaction.response.send_message("You don't have permission to give clubhall coins.", ephemeral=True)
            return
        register_user(str(user.id), user.display_name)
        added = safe_add_coins(str(user.id), amount)
        if added == 0:
            await interaction.response.send_message("Clubhall coin limit reached. No coins added.", ephemeral=True)
        elif added < amount:
            await interaction.response.send_message(
                f"Partial success: Only {added} coins added due to server limit.", ephemeral=True
            )
        else:
            await interaction.response.send_message(f"{added} clubhall coins added to {user.display_name}.")

    @bot.tree.command(name="remove", description="Remove clubhall coins from a user (Admin/Owner only)")
    async def remove(interaction: discord.Interaction, user: discord.Member, amount: int):
        if not has_role(interaction.user, ADMIN_ROLE_ID):
            await interaction.response.send_message("You don't have permission to remove clubhall coins.", ephemeral=True)
            return
        current = get_money(str(user.id))
        set_money(str(user.id), max(0, current - amount))
        await interaction.response.send_message(f"{amount} clubhall coins removed from {user.display_name}.")

    @bot.tree.command(name="donate", description="Send coins to another user")
    async def donate(interaction: discord.Interaction, user: discord.Member, amount: int):
        sender_id = str(interaction.user.id)
        receiver_id = str(user.id)
        if sender_id == receiver_id:
            await interaction.response.send_message("You can't donate coins on yourself.", ephemeral=True)
            return
        register_user(sender_id, interaction.user.display_name)
        register_user(receiver_id, user.display_name)
        sender_balance = get_money(sender_id)
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return
        if amount > sender_balance:
            await interaction.response.send_message("You don't have enough clubhall coins.", ephemeral=True)
            return
        set_money(sender_id, sender_balance - amount)
        safe_add_coins(receiver_id, amount)
        await interaction.response.send_message(
            f"💸 You donated **{amount}** clubhall coins on {user.display_name}!",
            ephemeral=False,
        )

    @bot.tree.command(name="setlimit", description="Set the maximum clubhall coins limit (Owner only)")
    async def setlimit(interaction: discord.Interaction, new_limit: int):
        if not has_role(interaction.user, ADMIN_ROLE_ID):
            await interaction.response.send_message("Only the owner can change the limit.", ephemeral=True)
            return
        set_max_coins(new_limit)
        await interaction.response.send_message(f"New coin limit set to {new_limit}.")

    @bot.tree.command(name="request", description="Request clubhall coins from another user")
    async def request(interaction: discord.Interaction, user: discord.Member, amount: int, reason: str):
        sender_id = interaction.user.id
        receiver_id = user.id
        if sender_id == receiver_id:
            await interaction.response.send_message("You can't request clubhall coins from yourself.", ephemeral=True)
            return
        register_user(str(sender_id), interaction.user.display_name)
        register_user(str(receiver_id), user.display_name)
        view = RequestView(sender_id, receiver_id, amount)
        await interaction.response.send_message(
            f"{user.mention}, {interaction.user.display_name} requests **{amount}** clubhall coins for: _{reason}_",
            view=view,
        )

    @bot.tree.command(name="topcoins", description="Show the richest players")
    @app_commands.describe(count="How many spots to display (1–25)?")
    async def topcoins(interaction: discord.Interaction, count: int = 10):
        count = max(1, min(count, 25))
        top = get_top_users(count)
        if not top:
            await interaction.response.send_message("No data yet 🤷‍♂️")
            return
        lines = [f"**#{i + 1:02d}**  {name} – **{coins}** 💰" for i, (name, coins) in enumerate(top)]
        embed = discord.Embed(
            title=f"🏆 Top {count} Coin Holders",
            description="\n".join(lines),
            colour=discord.Colour.gold(),
        )
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="weekly", description="Claim your weekly clubhall coins (7d cooldown)")
    async def weekly(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        register_user(user_id, interaction.user.display_name)
        now = datetime.utcnow()
        last = get_last_weekly(user_id)
        if last and now - last < timedelta(days=7):
            remaining = timedelta(days=7) - (now - last)
            days, seconds = divmod(int(remaining.total_seconds()), 86400)
            hours, seconds = divmod(seconds, 3600)
            minutes = seconds // 60
            await interaction.response.send_message(
                f"⏳ You can claim again in **{days} days {hours} hours {minutes} minutes**.",
                ephemeral=True,
            )
            return
        added = safe_add_coins(user_id, WEEKLY_REWARD)
        set_last_weekly(user_id, now)
        if added > 0:
            await interaction.response.send_message(
                f"✅ {added} Coins added! You now have **{get_money(user_id)}** 💰.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "⚠️ Server coin limit reached. No weekly coins could be added.",
                ephemeral=True,
            )

    @bot.tree.command(name="daily", description="Claim your daily coins (24 h cooldown)")
    async def daily(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        register_user(user_id, interaction.user.display_name)
        now = datetime.utcnow()
        last = get_last_claim(user_id)
        if last and now - last < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last)
            hours, seconds = divmod(int(remaining.total_seconds()), 3600)
            minutes = seconds // 60
            await interaction.response.send_message(
                f"⏳ You can claim again in **{hours} hours {minutes} minutes**.",
                ephemeral=True,
            )
            return
        added = safe_add_coins(user_id, DAILY_REWARD)
        set_last_claim(user_id, now)
        if added > 0:
            await interaction.response.send_message(
                f"✅ {added} Coins added! You now have **{get_money(user_id)}** 💰.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "⚠️ Server coin limit reached. No daily coins could be added.",
                ephemeral=True,
            )

    @bot.tree.command(name="gamble", description="Gamble your coins for a chance to win more!")
    async def gamble(interaction: discord.Interaction, amount: int):
        user_id = str(interaction.user.id)
        register_user(user_id, interaction.user.display_name)
        if amount < 2:
            await interaction.response.send_message("🎲 Minimum bet is 2 clubhall coins.", ephemeral=True)
            return
        balance = get_money(user_id)
        if amount > balance:
            await interaction.response.send_message("❌ You don't have enough clubhall coins!", ephemeral=True)
            return
        await interaction.response.send_message("🎲 Rolling the dice...", ephemeral=False)
        await asyncio.sleep(2)
        roll = random()
        if roll < 0.05:
            multiplier = 3
            message = "💎 JACKPOT! 3x WIN!"
        elif roll < 0.30:
            multiplier = 2
            message = "🔥 Double win!"
        elif roll < 0.60:
            multiplier = 1
            message = "😐 You broke even."
        else:
            multiplier = 0
            message = "💀 You lost everything..."
        new_amount = amount * multiplier
        set_money(user_id, balance - amount + new_amount)
        emoji_result = {3: "💎", 2: "🔥", 1: "😐", 0: "💀"}
        await interaction.edit_original_response(
            content=(
                f"{emoji_result[multiplier]} **{interaction.user.display_name}**, you bet **{amount}** coins.\n"
                f"{message}\n"
                f"You now have **{get_money(user_id)}** clubhall coins."
            )
        )

    @bot.tree.command(name="casino", description="pay to win")
    @app_commands.describe(bet="How much you want to bet")
    async def casino(inter: discord.Interaction, bet: int):
        uid = str(inter.user.id)
        register_user(uid, inter.user.display_name)
        balance = get_money(uid)
        if bet <= 0:
            await inter.response.send_message("❌ Try number more than 0", ephemeral=True)
        if bet > balance:
            await inter.response.send_message("❌ Not enough coins.", ephemeral=True)
            return
        if random() > 0.5:
            set_money(uid, balance + bet)
            await inter.response.send_message(
                f"🎉 Congratulation! You won {bet} clubhall coins."
            )
            return
        set_money(uid, balance - bet)
        await inter.response.send_message(
            f"❌ Congratulation! You lose {bet} clubhall coins."
        )
        return


    return (
        money,
        balance,
        give,
        remove,
        donate,
        setlimit,
        request,
        topcoins,
        weekly,
        daily,
        gamble,
        casino,
    )
