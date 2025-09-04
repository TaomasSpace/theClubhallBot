import discord
from config import STAT_PRICE
from db.DBHelper import register_user, get_money, set_money, add_stat_points

async def buypoints(
    interaction: discord.Interaction, amount: int = 1
) -> None:
    price_per_point = int(STAT_PRICE)
    if amount < 1:
        await interaction.response.send_message(
            "Specify a positive amount.", ephemeral=True
        )
        return
    uid = str(interaction.user.id)
    register_user(uid, interaction.user.display_name)
    cost = price_per_point * amount
    balance = get_money(uid)
    if balance < cost:
        await interaction.response.send_message(
            f"💰 You need {cost} coins but only have {balance}.", ephemeral=True
        )
        return
    set_money(uid, balance - cost)
    add_stat_points(uid, amount)
    await interaction.response.send_message(
        f"Purchased {amount} point(s) for {cost} coins."
    )
