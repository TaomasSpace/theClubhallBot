import discord
from discord import ui
from db.DBHelper import register_user, get_money, set_money

class RequestView(ui.View):
    def __init__(self, sender_id: int, receiver_id: int, amount: int):
        super().__init__(timeout=60)
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount

    @ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message(
                "This request isn't for you.", ephemeral=True
            )
            return
        sender_balance = get_money(str(self.sender_id))
        receiver_balance = get_money(str(self.receiver_id))
        if receiver_balance < self.amount:
            await interaction.response.send_message(
                "You don't have enough clubhall coins to accept this request.",
                ephemeral=True,
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
            await interaction.response.send_message(
                "This request isn't for you.", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content="❌ Request declined.", view=None
        )

async def request(
    interaction: discord.Interaction, user: discord.Member, amount: int, reason: str
) -> None:
    sender_id = interaction.user.id
    receiver_id = user.id
    if sender_id == receiver_id:
        await interaction.response.send_message(
            "You can't request clubhall coins from yourself.", ephemeral=True
        )
        return
    register_user(str(sender_id), interaction.user.display_name)
    register_user(str(receiver_id), user.display_name)
    view = RequestView(sender_id, receiver_id, amount)
    await interaction.response.send_message(
        f"{user.mention}, {interaction.user.display_name} requests **{amount}** clubhall coins for: _{reason}_",
        view=view,
    )
