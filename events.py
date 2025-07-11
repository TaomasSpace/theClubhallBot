import asyncio
import logging
from datetime import datetime, timezone, timedelta
import discord
from discord import app_commands
from discord.app_commands import CommandOnCooldown
from discord.ext import commands

from config import WELCOME_CHANNEL_ID, LOG_CHANNEL_ID
from db.initializeDB import init_db
from db.DBHelper import get_all_rods_from_shop, delete_custom_role, get_custom_role, _fetchone
from utils import get_channel_webhook, has_role

rod_shop: dict[int, tuple[int, float]] = {}
active_giveaway_tasks: dict[int, asyncio.Task] = {}
filtered_violations: dict[int, list[float]] = {}

async def end_giveaway(bot: commands.Bot, channel_id: int, message_id: int, prize: str, winners: int):
    channel = bot.get_channel(channel_id)
    if channel is None:
        from db.DBHelper import finish_giveaway
        finish_giveaway(str(message_id))
        return
    try:
        refreshed = await channel.fetch_message(message_id)
    except Exception:
        from db.DBHelper import finish_giveaway
        finish_giveaway(str(message_id))
        return

    reaction = discord.utils.get(refreshed.reactions, emoji="🎉")
    if reaction is None:
        await refreshed.reply("No one has participated.")
        from db.DBHelper import finish_giveaway
        finish_giveaway(str(message_id))
        active_giveaway_tasks.pop(message_id, None)
        return

    users = [u async for u in reaction.users() if not u.bot]
    if not users:
        await refreshed.reply("No one has participated.")
        from db.DBHelper import finish_giveaway
        finish_giveaway(str(message_id))
        active_giveaway_tasks.pop(message_id, None)
        return
    if winners > len(users):
        winners = len(users)
    selected_winners = ", ".join(u.mention for u in (users if winners > 1 else [users[0]]))
    await refreshed.reply(f"🎊 Congratulations! {selected_winners} won **{prize}** 🎉")
    from db.DBHelper import finish_giveaway
    finish_giveaway(str(message_id))
    active_giveaway_tasks.pop(message_id, None)

async def load_giveaways(bot: commands.Bot):
    from db.DBHelper import get_active_giveaways
    for mid, cid, end, prize, winners in get_active_giveaways():
        end_dt = datetime.fromisoformat(end)
        delay = (end_dt - datetime.now(timezone.utc)).total_seconds()

        async def runner(m=int(mid), c=int(cid), p=prize, w=winners, d=delay):
            try:
                if d > 0:
                    await asyncio.sleep(d)
                await end_giveaway(bot, c, m, p, w)
            except asyncio.CancelledError:
                pass
        task = asyncio.create_task(runner())
        active_giveaway_tasks[int(mid)] = task


async def on_ready(bot: commands.Bot):
    init_db()
    global rod_shop
    rod_shop = get_all_rods_from_shop()
    await bot.tree.sync()
    await load_giveaways(bot)
    print(f"Bot is online as {bot.user}")


async def on_member_update(bot: commands.Bot, before: discord.Member, after: discord.Member):
    if before.premium_since and not after.premium_since:
        role_id = get_custom_role(str(after.id))
        if role_id:
            role = after.guild.get_role(role_id)
            if role:
                try:
                    await role.delete(reason="User stopped boosting")
                except Exception:
                    pass
            delete_custom_role(str(after.id))
    if not before.premium_since and after.premium_since:
        channel = bot.get_channel(1371395099824750664)
        if channel:
            await channel.send(
                f"🎉 {after.mention} just boosted the server — thank you so much for the support! 💜\n"
                f"Check <https://discord.com/channels/1351475070312255498/1351528109702119496/1371189412125216869> to see what new features you unlock!"
            )

async def on_message(bot: commands.Bot, message: discord.Message, lowercase_locked: set[int]):
    if message.author.bot or message.webhook_id:
        return
    if message.author.id in lowercase_locked:
        try:
            await message.delete()
        except discord.Forbidden:
            return
        wh = await get_channel_webhook(message.channel)
        await wh.send(
            content=message.content.lower(),
            username=message.author.display_name,
            avatar_url=message.author.display_avatar.url,
            allowed_mentions=discord.AllowedMentions.all(),
        )
    content = message.content.lower()
    from config import TRIGGER_RESPONSES
    from db.DBHelper import update_date, get_filtered_words

    for word in get_filtered_words():
        if word in content:
            try:
                await message.delete()
            except discord.Forbidden:
                return
            now = datetime.now().timestamp()
            history = filtered_violations.setdefault(message.author.id, [])
            history.append(now)
            history = [t for t in history if now - t <= 60]
            filtered_violations[message.author.id] = history
            if len(history) >= 3:
                try:
                    await message.author.timeout(
                        datetime.now(timezone.utc) + timedelta(minutes=10),
                        reason="Filtered words",
                    )
                except Exception:
                    pass
                filtered_violations[message.author.id] = []
            return

    for trigger, reply in TRIGGER_RESPONSES.items():
        if trigger.lower() in content:
            await message.channel.send(reply)
            break
    if message.author.bot:
        return
    update_date(message.author.id, message.author.name)
    await bot.process_commands(message)

async def on_member_join(bot: commands.Bot, member: discord.Member):
    role = discord.utils.get(member.guild.roles, name="Member")
    if role:
        await member.add_roles(role)
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        server_name = member.guild.name
        member_count = member.guild.member_count
        message = (
            f"Welcome new member {member.mention}! <3\n"
            f"Thanks for joining **{server_name}**.\n"
            f"Don't forget to read the #rules and #information!\n"
            f"We are now **{member_count}** members."
        )
        await channel.send(message)

async def on_member_remove(bot: commands.Bot, member: discord.Member):
    channel = bot.get_channel(1361778101176107311)
    if channel:
        member_count = member.guild.member_count
        message = f"It seems {member.name} has left us... We are now **{member_count}** members."
        await channel.send(message)


async def on_raw_reaction_add(bot: commands.Bot, payload: discord.RawReactionActionEvent):
    if payload.member is None or payload.member.bot:
        return
    row = _fetchone(
        "SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?",
        (str(payload.message_id), str(payload.emoji)),
    )
    if not row:
        return
    role = payload.member.guild.get_role(int(row[0]))
    if role:
        await payload.member.add_roles(role, reason="Reaction role added")


async def on_raw_reaction_remove(bot: commands.Bot, payload: discord.RawReactionActionEvent):
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return
    row = _fetchone(
        "SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?",
        (str(payload.message_id), str(payload.emoji)),
    )
    if not row:
        return
    role = guild.get_role(int(row[0]))
    if role:
        await member.remove_roles(role, reason="Reaction role removed")


async def on_app_error(bot: commands.Bot, inter: discord.Interaction, error: Exception):
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if log_ch:
        embed = discord.Embed(
            title="Command error",
            colour=discord.Colour.red(),
            timestamp=datetime.utcnow(),
            description=f"```py\n{error}\n```",
        )
        embed.add_field(name="Command", value=inter.command.qualified_name)
        embed.add_field(name="User", value=f"{inter.user} (`{inter.user.id}`)", inline=False)
        embed.add_field(name="Channel", value=f"{inter.channel.mention}", inline=False)
        await log_ch.send(embed=embed)
    if isinstance(error, CommandOnCooldown):
        await inter.response.send_message(
            f"⏱ Cooldown: try again in {error.retry_after:.0f}s.", ephemeral=True
        )
        return
    logging.exception("Slash-command error", exc_info=error)
    if inter.response.is_done():
        await inter.followup.send("Oops, something went wrong 😵", ephemeral=True)
    else:
        await inter.response.send_message("Oops, something went wrong 😵", ephemeral=True)


def format_options(data: dict, interaction: discord.Interaction) -> str:
    result = []
    resolved = data.get("resolved", {})
    users_data = resolved.get("users", {}) if resolved else {}
    for opt in data.get("options", []):
        if opt.get("type") == 1:
            inner = ", ".join(_format_option(o, users_data) for o in opt.get("options", [])) or "–"
            result.append(f"{opt['name']}({inner})")
        else:
            result.append(_format_option(opt, users_data))
    return ", ".join(result) or "–"


def _format_option(opt: dict, users_data: dict) -> str:
    name = opt["name"]
    value = opt.get("value")
    if opt["type"] == 6 and value:
        user = users_data.get(str(value))
        if user and isinstance(user, dict):
            username = user.get("global_name") or user.get("username", "Unknown")
            return f"{name}={username} ({value})"
        else:
            return f"{name}=(unknown user) ({value})"
    return f"{name}={value}"

async def on_app_command_completion(bot: commands.Bot, inter: discord.Interaction, command: app_commands.Command):
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if not log_ch:
        return
    opts = format_options(inter.data, inter)
    embed = discord.Embed(
        title="Command executed",
        colour=discord.Colour.blue(),
        timestamp=datetime.utcnow(),
    )
    embed.add_field(name="Command", value=f"/{command.qualified_name}")
    embed.add_field(name="User", value=f"{inter.user} (`{inter.user.id}`)", inline=False)
    embed.add_field(name="Channel", value=inter.channel.mention, inline=False)
    embed.add_field(name="Options", value=opts, inline=False)
    await log_ch.send(embed=embed)


def setup(bot: commands.Bot, lowercase_locked: set[int]):
    async def ready_wrapper():
        await on_ready(bot)

    async def member_update_wrapper(before: discord.Member, after: discord.Member):
        await on_member_update(bot, before, after)

    async def message_wrapper(message: discord.Message):
        await on_message(bot, message, lowercase_locked)

    async def member_join_wrapper(member: discord.Member):
        await on_member_join(bot, member)

    async def member_remove_wrapper(member: discord.Member):
        await on_member_remove(bot, member)

    async def command_completion_wrapper(inter: discord.Interaction, command: app_commands.Command):
        await on_app_command_completion(bot, inter, command)

    async def reaction_add_wrapper(payload: discord.RawReactionActionEvent):
        await on_raw_reaction_add(bot, payload)

    async def reaction_remove_wrapper(payload: discord.RawReactionActionEvent):
        await on_raw_reaction_remove(bot, payload)

    async def app_error_wrapper(inter: discord.Interaction, error: Exception):
        await on_app_error(bot, inter, error)

    bot.add_listener(ready_wrapper, name="on_ready")
    bot.add_listener(member_update_wrapper, name="on_member_update")
    bot.add_listener(message_wrapper, name="on_message")
    bot.add_listener(member_join_wrapper, name="on_member_join")
    bot.add_listener(member_remove_wrapper, name="on_member_remove")
    bot.add_listener(reaction_add_wrapper, name="on_raw_reaction_add")
    bot.add_listener(reaction_remove_wrapper, name="on_raw_reaction_remove")
    bot.tree.error(app_error_wrapper)
    bot.add_listener(command_completion_wrapper, name="on_app_command_completion")


