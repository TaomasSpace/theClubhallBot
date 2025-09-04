import discord
from utils import has_command_permission

async def addcolorreactionrole(
    interaction: discord.Interaction,
    target_message_id: str,
    emoji: str,
    role: discord.Role,
) -> None:
    if not has_command_permission(interaction.user, "addcolorreactionrole", "admin"):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    channel = interaction.channel
    try:
        message = await channel.fetch_message(target_message_id)
        await message.add_reaction(emoji)
        _execute = __import__("db.DBHelper", fromlist=["_execute"])._execute
        _execute(
            "INSERT OR REPLACE INTO reaction_roles (message_id, emoji, role_id) VALUES (?, ?, ?)",
            (str(target_message_id), emoji, str(role.id)),
        )
        await interaction.response.send_message(
            f"✅ Added emoji {emoji} for role {role.name}.", ephemeral=True
        )
    except Exception as e:  # pragma: no cover - fetch errors
        await interaction.response.send_message(
            f"❌ Error: {e}", ephemeral=True
        )
