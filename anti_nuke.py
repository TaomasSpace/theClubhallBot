import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from db.DBHelper import (
    get_anti_nuke_setting,
    get_safe_users,
    get_safe_roles,
    get_anti_nuke_log_channel,
)

OWNER_ID = 756537363509018736

ACTION_WINDOW = 15  # seconds

action_history: Dict[str, Dict[int, List[float]]] = {}


CATEGORIES = {
    "delete_roles": discord.AuditLogAction.role_delete,
    "add_roles": discord.AuditLogAction.role_create,
    "kick": discord.AuditLogAction.kick,
    "ban": discord.AuditLogAction.ban,
    "delete_channels": discord.AuditLogAction.channel_delete,
    "webhook": discord.AuditLogAction.webhook_create,
    "anti_mention": None,
}


async def punish(member: discord.Member, punishment: str, duration: Optional[int]) -> None:

    try:
        if punishment == "timeout":
            if duration is None:
                duration = 60
            until = discord.utils.utcnow() + timedelta(seconds=duration)
            await member.timeout(until, reason="Anti-nuke")
        elif punishment == "strip":
            roles = [r for r in member.roles if not r.is_default()]
            if roles:
                await member.remove_roles(*roles, reason="Anti-nuke")
        elif punishment == "kick":
            await member.kick(reason="Anti-nuke")
        elif punishment == "ban":
            await member.ban(reason="Anti-nuke")
    except Exception:
        pass


async def log_action(member: discord.Member, category: str, punishment: str, duration: Optional[int]) -> None:

    cid = get_anti_nuke_log_channel()
    if not cid:
        return
    channel = member.guild.get_channel(cid)
    if channel:
        info = f"{punishment}"
        if punishment == "timeout" and duration:
            info += f" {duration}s"
        await channel.send(
            f"<@{OWNER_ID}> {member.mention} triggered **{category}** - {info}"
        )

async def handle_event(guild: discord.Guild, user: Optional[discord.Member], category: str):

    setting = get_anti_nuke_setting(category)
    if not setting:
        return
    enabled, threshold, punishment, duration = setting
    if not enabled:
        return
    uid = user.id if user else None
    if uid is None:
        return
    if uid in get_safe_users():
        return
    safe_roles = set(get_safe_roles())
    if any(r.id in safe_roles for r in user.roles):
        return
    hist = action_history.setdefault(category, {}).setdefault(uid, [])
    now = datetime.utcnow().timestamp()
    hist = [t for t in hist if now - t <= ACTION_WINDOW]
    hist.append(now)
    action_history[category][uid] = hist
    if len(hist) >= threshold:
        await punish(user, punishment, duration)
        await log_action(user, category, punishment, duration)
        action_history[category][uid] = []



async def on_message(message: discord.Message):
    if message.author.bot or message.webhook_id:
        return
    setting = get_anti_nuke_setting("anti_mention")
    if not setting:
        return
    enabled, threshold, punishment, duration = setting
    if not enabled:
        return
    mention_count = len(message.mentions)
    mention_count += message.content.count("@here")
    mention_count += message.content.count("@everyone")
    if mention_count >= threshold:
        await punish(message.author, punishment, duration)
        await log_action(message.author, "anti_mention", punishment, duration)


async def on_channel_delete(channel: discord.abc.GuildChannel):
    guild = channel.guild
    entry = None
    async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        entry = e
        break
    if entry and (datetime.utcnow() - entry.created_at).total_seconds() < ACTION_WINDOW:
        member = guild.get_member(entry.user.id)
        if member:
            await handle_event(guild, member, "delete_channels")


async def on_role_delete(role: discord.Role):
    guild = role.guild
    entry = None
    async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        entry = e
        break
    if entry and (datetime.utcnow() - entry.created_at).total_seconds() < ACTION_WINDOW:
        member = guild.get_member(entry.user.id)
        if member:
            await handle_event(guild, member, "delete_roles")


async def on_role_create(role: discord.Role):
    guild = role.guild
    entry = None
    async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        entry = e
        break
    if entry and (datetime.utcnow() - entry.created_at).total_seconds() < ACTION_WINDOW:
        member = guild.get_member(entry.user.id)
        if member:
            await handle_event(guild, member, "add_roles")


async def on_member_remove(member: discord.Member):
    guild = member.guild
    async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        if e.target.id == member.id and (datetime.utcnow() - e.created_at).total_seconds() < ACTION_WINDOW:
            actor = guild.get_member(e.user.id)
            if actor:
                await handle_event(guild, actor, "kick")
            return


async def on_member_ban(guild: discord.Guild, user: discord.User):
    async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        if e.target.id == user.id and (datetime.utcnow() - e.created_at).total_seconds() < ACTION_WINDOW:
            actor = guild.get_member(e.user.id)
            if actor:
                await handle_event(guild, actor, "ban")
            return


async def on_webhooks_update(channel: discord.abc.GuildChannel):
    guild = channel.guild
    async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
        if (datetime.utcnow() - e.created_at).total_seconds() < ACTION_WINDOW:
            member = guild.get_member(e.user.id)
            if member:
                await handle_event(guild, member, "webhook")
            break


def setup(bot: commands.Bot):
    bot.add_listener(on_channel_delete, name="on_guild_channel_delete")
    bot.add_listener(on_role_delete, name="on_guild_role_delete")
    bot.add_listener(on_role_create, name="on_guild_role_create")
    bot.add_listener(on_member_remove, name="on_member_remove")
    bot.add_listener(on_member_ban, name="on_member_ban")
    bot.add_listener(on_webhooks_update, name="on_webhooks_update")
    bot.add_listener(on_message, name="on_message")
