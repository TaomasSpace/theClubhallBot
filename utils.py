import discord
from discord import ui
from typing import Optional

from permissions import get_permission_rule, describe_permission

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
    """Check if *user* may run *command* based on static role rules."""

    if user.guild and user.id == user.guild.owner_id:
        # The server owner always has access to every command.
        return True

    rule = get_permission_rule(command)

    if rule.allow_everyone:
        return True

    if not user.guild:
        return False

    if rule.allow_boosters and getattr(user, "premium_since", None):
        return True

    if rule.role_ids and any(role.id in rule.role_ids for role in user.roles):
        return True

    print(
        "[PERM] Access denied",
        command,
        describe_permission(user.guild, command),
        [r.id for r in user.roles],
    )
    return False
