import discord
from utils import get_channel_webhook, has_command_permission


async def imitate(interaction: discord.Interaction, user: discord.Member, msg: str) -> None:
    """Imitate a user's message via webhook."""
    if (
        not has_command_permission(interaction.user, "imitate", "admin")
        and not interaction.user.premium_since
    ):
        await interaction.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
        return
    channel = interaction.channel
    webhook = await get_channel_webhook(channel)
    try:
        await webhook.send(
            content=msg,
            username=user.display_name,
            avatar_url=user.display_avatar.url,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await interaction.response.send_message("✅ Message sent.", ephemeral=True)
    except Exception as e:  # pragma: no cover - network failures
        await interaction.response.send_message(
            f"❌ Failed to imitate: {e}", ephemeral=True
        )
