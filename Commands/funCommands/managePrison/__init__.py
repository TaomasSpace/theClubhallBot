import asyncio
import discord
from db.DBHelper import get_role
from utils import has_command_permission, parse_duration

active_prison_timers: dict[tuple[int, int], asyncio.Task] = {}

async def managePrisonMember(
    interaction: discord.Interaction, user: discord.Member, time: str | None = None
) -> None:
    if not has_command_permission(interaction.user, "manageprisonmember", "mod"):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return
    gooyb = interaction.user.name == "goodyb"
    role_id = get_role(interaction.guild.id, "prisoner")
    role = interaction.guild.get_role(role_id) if role_id else None
    if role is None:
        await interaction.response.send_message(
            "❌ Prisoner role not configured.", ephemeral=True
        )
        return
    key = (interaction.guild.id, user.id)
    if time == "cancel":
        task = active_prison_timers.pop(key, None)
        if task and not task.done():
            task.cancel()
            if role not in user.roles:
                await user.add_roles(role)
            await interaction.response.send_message(
                f"🕊️ Timer cancelled. {user.mention} has been freed.",
                ephemeral=gooyb,
            )
        else:
            await interaction.response.send_message(
                f"⚠️ No active timer for {user.mention}.", ephemeral=True
            )
        return
    if role not in user.roles:
        task = active_prison_timers.pop(key, None)
        if task and not task.done():
            task.cancel()
        await user.add_roles(role)
        await interaction.response.send_message(
            f"🔓 {user.mention} has been freed from prison.",
            ephemeral=gooyb,
        )
        return
    await user.remove_roles(role)
    msg = f"🔐 {user.mention} has been sent to prison."
    if time:
        seconds = parse_duration(time)
        if seconds is None:
            await interaction.response.send_message(
                f"⏳ Invalid time format: `{time}`. Use `10m`, `2h`, etc.",
                ephemeral=True,
            )
            return

        async def release_later():
            try:
                await asyncio.sleep(seconds)
                await user.add_roles(role)
                await interaction.followup.send(
                    f"🕊️ {user.mention} has served their time and is now free.",
                    ephemeral=False,
                )
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(release_later())
        active_prison_timers[key] = task
        msg += f" They will be freed in {time}."
    await interaction.response.send_message(msg, ephemeral=False)
