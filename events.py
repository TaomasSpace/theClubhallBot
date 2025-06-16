import asyncio
import logging
from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands

from config import WELCOME_CHANNEL_ID, LOG_CHANNEL_ID
from db.initializeDB import init_db
from db.DBHelper import get_all_rods_from_shop, delete_custom_role, get_custom_role, _fetchone
from utils import get_channel_webhook, has_role

rod_shop: dict[int, tuple[int, float]] = {}
active_giveaway_tasks: dict[int, asyncio.Task] = {}

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
    from bot import TRIGGER_RESPONSES, update_date
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
    bot.add_listener(lambda: on_ready(bot), name="on_ready")
    bot.add_listener(lambda before, after: on_member_update(bot, before, after), name="on_member_update")
    bot.add_listener(lambda message: on_message(bot, message, lowercase_locked), name="on_message")
    bot.add_listener(lambda member: on_member_join(bot, member), name="on_member_join")
    bot.add_listener(lambda member: on_member_remove(bot, member), name="on_member_remove")
    bot.tree.error(cog=None)(lambda inter, error: asyncio.create_task(on_app_error(bot, inter, error)))
    bot.add_listener(lambda inter, command: on_app_command_completion(bot, inter, command), name="on_app_command_completion")

