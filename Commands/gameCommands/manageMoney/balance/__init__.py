import discord
from db.DBHelper import register_user, get_money

async def balance(interaction: discord.Interaction, user: discord.Member) -> None:
    register_user(str(user.id), user.display_name)
    money_amt = get_money(str(user.id))
    await interaction.response.send_message(
        f"{user.display_name} has {money_amt} clubhall coins.", ephemeral=False
    )
