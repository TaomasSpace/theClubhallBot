from datetime import datetime, timedelta
from random import random, randint
import discord
from db.DBHelper import register_user, get_stats, get_money, set_money, safe_add_coins

hack_cooldowns: dict[int, datetime] = {}

async def hack(interaction: discord.Interaction) -> None:
    uid = str(interaction.user.id)
    register_user(uid, interaction.user.display_name)
    now = datetime.utcnow()
    cooldown = hack_cooldowns.get(interaction.user.id)
    if cooldown and now - cooldown < timedelta(minutes=45):
        remaining = timedelta(minutes=45) - (now - cooldown)
        minutes, seconds = divmod(int(remaining.total_seconds()), 60)
        await interaction.response.send_message(
            f"⏳ You can hack again in **{minutes} minutes {seconds} seconds**.",
            ephemeral=True,
        )
        return
    stats = get_stats(uid)
    if stats["intelligence"] < 3:
        await interaction.response.send_message(
            "❌ You need at least **3** Intelligence to attempt a hack.",
            ephemeral=True,
        )
        return
    int_level = stats["intelligence"]
    success = random() < min(0.20 + 0.05 * (int_level - 3), 0.80)
    hack_cooldowns[interaction.user.id] = now
    if not success:
        loss = randint(1, 5) * int_level
        new_bal = max(0, get_money(uid) - loss)
        set_money(uid, new_bal)
        await interaction.response.send_message(
            f"💻 Hack failed! Security traced you and you lost **{loss}** coins.",
            ephemeral=True,
        )
        return
    reward = randint(5, 12) * int_level
    added = safe_add_coins(uid, reward)
    if added > 0:
        await interaction.response.send_message(
            f"🔋 Hack successful! You siphoned **{added}** coins from the bank.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "⚠️ Hack succeeded but server coin limit reached. No coins added.",
            ephemeral=True,
        )
