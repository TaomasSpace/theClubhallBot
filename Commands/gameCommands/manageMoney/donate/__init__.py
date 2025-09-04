import discord
from db.DBHelper import register_user, get_money, safe_add_coins, set_money

async def donate(
    interaction: discord.Interaction, user: discord.Member, amount: str
) -> None:
    sender_id = str(interaction.user.id)
    receiver_id = str(user.id)
    if sender_id == receiver_id:
        await interaction.response.send_message(
            "You can't donate coins on yourself.", ephemeral=True
        )
        return
    register_user(sender_id, interaction.user.display_name)
    register_user(receiver_id, user.display_name)
    sender_balance = get_money(sender_id)
    try:
        amount_int = int(amount)
    except Exception:
        await interaction.response.send_message("Invalid amount.", ephemeral=True)
        return
    if amount_int <= 0:
        await interaction.response.send_message(
            "Amount must be greater than 0.", ephemeral=True
        )
        return
    if amount_int > sender_balance:
        await interaction.response.send_message(
            "You don't have enough clubhall coins.", ephemeral=True
        )
        return
    set_money(sender_id, sender_balance - amount_int)
    safe_add_coins(receiver_id, amount_int)
    await interaction.response.send_message(
        f"💸 You donated **{amount_int}** clubhall coins on {user.display_name}!",
        ephemeral=False,
    )
