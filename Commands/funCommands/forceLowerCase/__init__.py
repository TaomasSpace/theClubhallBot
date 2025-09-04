from collections import defaultdict
import discord

lowercase_locked: dict[int, set[int]] = defaultdict(set)

async def forcelowercase(
    interaction: discord.Interaction, member: discord.Member
) -> None:
    locked = lowercase_locked[interaction.guild.id]
    if member.id in locked:
        locked.remove(member.id)
        await interaction.response.send_message(
            f"🔓 {member.display_name} unlocked – messages stay unchanged.",
            ephemeral=True,
        )
    else:
        locked.add(member.id)
        await interaction.response.send_message(
            f"🔒 {member.display_name} locked – messages will be lower-cased.",
            ephemeral=True,
        )
