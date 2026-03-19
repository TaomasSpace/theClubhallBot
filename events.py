import asyncio
import io
import logging
from datetime import datetime, timezone, timedelta
import uuid

import discord
from discord import app_commands
from discord.app_commands import CommandOnCooldown
from discord.ext import commands
import random

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageOps = None

from db.initializeDB import init_db
from db.DBHelper import (
    delete_custom_role,
    get_custom_role,
    _fetchone,
    get_trigger_responses,
    get_welcome_channel,
    get_leave_channel,
    get_welcome_message,
    get_leave_message,
    get_booster_channel,
    get_booster_message,
    get_log_channel,
    get_prison_role,
    start_message_log as db_start_message_log,
    get_active_message_logs,
    increment_message_log,
    get_message_log_counts,
    clear_message_log,
    get_skullboard_settings,
    get_skullboard_post,
    set_skullboard_post,
)
from utils import get_channel_webhook

from config import ROD_SHOP

rod_shop: dict[int, tuple[int, float]] = ROD_SHOP.copy()
active_giveaway_tasks: dict[int, asyncio.Task] = {}
filtered_violations: dict[int, dict[int, list[float]]] = {}
trigger_responses: dict[int, dict[str, str]] = {}
message_log_tasks: dict[int, asyncio.Task] = {}
active_message_logs: dict[int, tuple[int, float, int]] = {}

ERROR_LOG_CHANNEL_ID = 1373912883527815262


async def end_giveaway(
    bot: commands.Bot, channel_id: int, message_id: int, prize: str, winners: int
):
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
    selected = random.sample(users, winners)
    selected_winners = ", ".join(u.mention for u in selected)
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


async def end_message_log(bot: commands.Bot, guild_id: int):
    channel_id, _, top = active_message_logs.get(guild_id, (None, None, 30))
    channel = bot.get_channel(channel_id) if channel_id else None
    users = get_message_log_counts(guild_id, top)
    if channel:
        if users:
            lines = [
                f"{idx + 1}. {name} – {count} messages"
                for idx, (name, count) in enumerate(users)
            ]
            embed = discord.Embed(
                title=f"Top {len(users)} chatters",
                description="\n".join(lines),
                colour=discord.Colour.blue(),
            )
            await channel.send(embed=embed)
        else:
            await channel.send("No messages were recorded.")
    clear_message_log(guild_id)
    active_message_logs.pop(guild_id, None)
    message_log_tasks.pop(guild_id, None)


async def start_message_log(
    bot: commands.Bot, guild_id: int, channel_id: int, seconds: int, top: int
) -> bool:
    if guild_id in active_message_logs:
        return False
    end_dt = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    db_start_message_log(guild_id, channel_id, end_dt, top)
    end_ts = end_dt.timestamp()
    active_message_logs[guild_id] = (channel_id, end_ts, top)

    async def runner():
        try:
            await asyncio.sleep(seconds)
            await end_message_log(bot, guild_id)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(runner())
    message_log_tasks[guild_id] = task
    return True


async def load_message_logs(bot: commands.Bot):
    now = datetime.now(timezone.utc).timestamp()
    for gid, cid, end_dt, top in get_active_message_logs():
        end_ts = end_dt.timestamp()
        active_message_logs[gid] = (cid, end_ts, top)
        delay = end_ts - now

        async def runner(d=delay, g=gid):
            try:
                if d > 0:
                    await asyncio.sleep(d)
                await end_message_log(bot, g)
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(runner())
        message_log_tasks[gid] = task


async def on_ready(bot: commands.Bot):
    init_db()
    global rod_shop, trigger_responses
    # Load fixed shop from config
    rod_shop = ROD_SHOP.copy()
    trigger_responses = {g.id: get_trigger_responses(g.id) for g in bot.guilds}
    await bot.tree.sync()
    await load_giveaways(bot)
    await load_message_logs(bot)
    print(f"Bot is online as {bot.user}")


async def on_member_update(
    bot: commands.Bot, before: discord.Member, after: discord.Member
):
    if before.premium_since and not after.premium_since:
        role_id = get_custom_role(after.guild.id, str(after.id))
        if role_id:
            role = after.guild.get_role(role_id)
            if role:
                try:
                    await role.delete(reason="User stopped boosting")
                except Exception:
                    pass
            delete_custom_role(after.guild.id, str(after.id))
    if not before.premium_since and after.premium_since:
        cid = get_booster_channel(after.guild.id)
        if cid:
            channel = bot.get_channel(cid)
            if channel:
                args = {
                    "member": after.name,
                    "member_mention": after.mention,
                    "server": after.guild.name,
                }
                template = get_booster_message(after.guild.id)
                if template:
                    try:
                        message = template.format(**args)
                    except Exception:
                        message = template
                else:
                    message = f"🎉 {after.mention} just boosted the server — thank you so much for the support! 💜"
                await channel.send(message)


async def on_message(
    bot: commands.Bot, message: discord.Message, lowercase_locked: dict[int, set[int]]
):
    if message.author.bot or message.webhook_id or not message.guild:
        return
    if message.guild.id in active_message_logs:
        _, end_ts, _ = active_message_logs[message.guild.id]
        if datetime.now(timezone.utc).timestamp() < end_ts:
            increment_message_log(
                message.guild.id, str(message.author.id), message.author.display_name
            )
    locked = lowercase_locked.get(message.guild.id, set())
    if message.author.id in locked:
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
    from db.DBHelper import update_date, get_filtered_words

    content = message.content.lower()

    for word in get_filtered_words(message.guild.id):
        if content.startswith(word) or " " + word in content:
            try:
                await message.delete()
            except discord.Forbidden:
                return
            now = datetime.now().timestamp()
            guild_violations = filtered_violations.setdefault(message.guild.id, {})
            history = guild_violations.setdefault(message.author.id, [])
            history.append(now)
            history = [t for t in history if now - t <= 60]
            guild_violations[message.author.id] = history
            if len(history) >= 3:
                try:
                    await message.author.timeout(
                        datetime.now(timezone.utc) + timedelta(minutes=10),
                        reason="Filtered words",
                    )
                except Exception:
                    pass
                guild_violations[message.author.id] = []
            return

    for trigger, reply in trigger_responses.get(message.guild.id, {}).items():
        if content.startswith(trigger + " ") or " " + trigger + " " in content or content.endswith(" " + trigger) or trigger == content:
            await message.channel.send(reply)
            break
    if message.author.bot:
        return
    update_date(message.author.id, message.author.name)


async def on_member_join(bot: commands.Bot, member: discord.Member):
    role = discord.utils.get(member.guild.roles, name="Member")
    if role:
        await member.add_roles(role)
    pid = get_prison_role(member.guild.id)
    if pid:
        prole = member.guild.get_role(pid)
        if prole:
            await member.add_roles(prole)
    cid = get_welcome_channel(member.guild.id)
    if cid:
        channel = bot.get_channel(cid)
        if channel:
            args = {
                "member": member.name,
                "member_mention": member.mention,
                "server": member.guild.name,
                "member_count": member.guild.member_count,
            }
            template = get_welcome_message(member.guild.id)
            if template:
                try:
                    message = template.format(**args)
                except Exception:
                    message = template
            else:
                message = (
                    f"Welcome new member {member.mention}! <3\n"
                    f"Thanks for joining **{args['server']}**.\n"
                    "Don't forget to read the #rules\n"
                    f"We are now **{args['member_count']}** members."
                )
            await channel.send(message)


async def on_member_remove(bot: commands.Bot, member: discord.Member):
    cid = get_leave_channel(member.guild.id)
    if cid:
        channel = bot.get_channel(cid)
        if channel:
            args = {
                "member": member.name,
                "member_mention": member.mention,
                "server": member.guild.name,
                "member_count": member.guild.member_count,
            }
            template = get_leave_message(member.guild.id)
            if template:
                try:
                    message = template.format(**args)
                except Exception:
                    message = template
            else:
                message = (
                    f"It seems {member.name} has left us... "
                    f"We are now **{args['member_count']}** members."
                )
            await channel.send(message)


async def _resolve_text_channel(bot: commands.Bot, channel_id: int):
    channel = bot.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await bot.fetch_channel(channel_id)
    except Exception:
        return None


async def _count_human_reactions(reaction: discord.Reaction) -> int:
    users = [u async for u in reaction.users() if not u.bot]
    return len(users)


def _load_font(size: int):
    if ImageFont is None:
        raise RuntimeError("Pillow is not available")
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text_lines(
    draw,
    text: str,
    font,
    max_width: int,
    max_lines: int,
) -> list[str]:
    if not text:
        return ["(no text content)"]

    lines: list[str] = []
    truncated = False
    for raw_line in text.splitlines() or [""]:
        words = raw_line.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                    current = word
                else:
                    lines.append(word)
                    current = ""
                if len(lines) >= max_lines:
                    truncated = True
                    break
        if len(lines) >= max_lines:
            truncated = True
            break
        if current:
            lines.append(current)
            if len(lines) >= max_lines:
                truncated = True
                break
    if not lines:
        lines = ["(no text content)"]
    if truncated and lines:
        lines[-1] = lines[-1][: max(0, len(lines[-1]) - 1)] + "…"
    return lines[:max_lines]


async def _build_skullboard_snapshot_file(
    message: discord.Message,
) -> discord.File | None:
    if None in (Image, ImageDraw, ImageFont, ImageOps):
        return None

    width = 980
    outer_padding = 24
    header_height = 100
    avatar_size = 64
    bubble_padding = 20
    content_box_y = 130
    content_box_width = width - (outer_padding * 2)

    title_font = _load_font(30)
    body_font = _load_font(28)
    meta_font = _load_font(22)

    tmp_image = Image.new("RGB", (width, 600), (15, 17, 22))
    draw = ImageDraw.Draw(tmp_image)
    content_max_width = content_box_width - (bubble_padding * 2)
    lines = _wrap_text_lines(
        draw,
        message.content or "(no text content)",
        body_font,
        content_max_width,
        max_lines=8,
    )
    line_height = body_font.getbbox("Ag")[3] - body_font.getbbox("Ag")[1] + 6
    content_height = (bubble_padding * 2) + (line_height * len(lines)) + 42
    height = max(260, content_box_y + content_height + outer_padding)

    image = Image.new("RGB", (width, height), (15, 17, 22))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        ((0, 0), (width - 1, height - 1)),
        radius=16,
        outline=(42, 48, 60),
        width=2,
        fill=(15, 17, 22),
    )
    draw.rectangle(
        ((8, 20), (12, height - 20)),
        fill=(251, 216, 64),
    )

    avatar = None
    try:
        avatar_bytes = await message.author.display_avatar.read()
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        resampling = (
            Image.Resampling.LANCZOS
            if hasattr(Image, "Resampling")
            else Image.LANCZOS
        )
        avatar = ImageOps.fit(avatar, (avatar_size, avatar_size), method=resampling)
    except Exception:
        avatar = None
    if avatar is not None:
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar_x = outer_padding + 8
        avatar_y = outer_padding + 8
        image.paste(avatar, (avatar_x, avatar_y), mask)
    else:
        avatar_x = outer_padding + 8
        avatar_y = outer_padding + 8
        draw.ellipse(
            ((avatar_x, avatar_y), (avatar_x + avatar_size, avatar_y + avatar_size)),
            fill=(66, 80, 103),
        )

    text_x = avatar_x + avatar_size + 16
    draw.text(
        (text_x, avatar_y + 4),
        str(message.author),
        fill=(237, 242, 252),
        font=title_font,
    )
    draw.text(
        (text_x, avatar_y + 44),
        message.created_at.strftime("%d %b %Y • %H:%M"),
        fill=(148, 154, 171),
        font=meta_font,
    )

    content_box = (
        outer_padding,
        content_box_y,
        outer_padding + content_box_width,
        content_box_y + content_height,
    )
    draw.rounded_rectangle(
        ((content_box[0], content_box[1]), (content_box[2], content_box[3])),
        radius=14,
        fill=(44, 49, 60),
    )
    content_y = content_box_y + bubble_padding + 10
    for line in lines:
        draw.text(
            (outer_padding + bubble_padding, content_y),
            line,
            fill=(232, 236, 247),
            font=body_font,
        )
        content_y += line_height

    snapshot = io.BytesIO()
    image.save(snapshot, format="PNG", optimize=True)
    snapshot.seek(0)
    return discord.File(snapshot, filename=f"skullboard_snapshot_{message.id}.png")


def _build_skullboard_embed(
    message: discord.Message, emoji: str, reaction_count: int
) -> discord.Embed:
    embed = discord.Embed(
        title=f"{message.author.display_name}",
        description=message.content or "*No text content*",
        colour=discord.Colour.gold(),
        timestamp=message.created_at,
    )
    embed.set_author(
        name=f"{message.author}",
        icon_url=message.author.display_avatar.url,
    )
    embed.add_field(
        name="Author",
        value=f"{message.author.mention}\n({message.author})",
        inline=True,
    )
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(
        name="Jump to Message",
        value=f"[Click here]({message.jump_url})",
        inline=True,
    )
    if message.attachments:
        embed.add_field(
            name="Attachment",
            value=message.attachments[0].url,
            inline=False,
        )
    embed.set_footer(text=f"{emoji} {reaction_count}")
    return embed


async def handle_skullboard_reaction_add(
    bot: commands.Bot, payload: discord.RawReactionActionEvent
):
    if payload.guild_id is None:
        return

    settings = get_skullboard_settings(payload.guild_id)
    if not settings:
        return
    configured_emoji, min_reactions, target_channel_id = settings

    if str(payload.emoji) != configured_emoji:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    member = payload.member or guild.get_member(payload.user_id)
    if member is None:
        try:
            member = await guild.fetch_member(payload.user_id)
        except Exception:
            return
    if member.bot:
        return

    source_channel = await _resolve_text_channel(bot, payload.channel_id)
    if source_channel is None or not hasattr(source_channel, "fetch_message"):
        return

    try:
        source_message = await source_channel.fetch_message(payload.message_id)
    except Exception:
        return

    if source_message.author.bot:
        return

    matching_reaction = next(
        (r for r in source_message.reactions if str(r.emoji) == configured_emoji),
        None,
    )
    if matching_reaction is None:
        return

    reaction_count = await _count_human_reactions(matching_reaction)
    if reaction_count < min_reactions:
        return

    target_channel = await _resolve_text_channel(bot, target_channel_id)
    if target_channel is None or not hasattr(target_channel, "send"):
        return

    embed = _build_skullboard_embed(source_message, configured_emoji, reaction_count)
    post_content = f"{configured_emoji} **{reaction_count}**"
    existing_board_message_id = get_skullboard_post(
        payload.guild_id, payload.message_id
    )

    if existing_board_message_id and hasattr(target_channel, "fetch_message"):
        try:
            board_message = await target_channel.fetch_message(existing_board_message_id)
            await board_message.edit(content=post_content)
            return
        except Exception:
            pass

    snapshot_file = await _build_skullboard_snapshot_file(source_message)
    if snapshot_file is not None:
        embed.set_image(url=f"attachment://{snapshot_file.filename}")
        posted = await target_channel.send(
            content=post_content, embed=embed, file=snapshot_file
        )
    else:
        posted = await target_channel.send(content=post_content, embed=embed)
    try:
        await posted.add_reaction(configured_emoji)
    except Exception:
        pass
    set_skullboard_post(payload.guild_id, payload.message_id, posted.id)


async def on_raw_reaction_add(
    bot: commands.Bot, payload: discord.RawReactionActionEvent
):
    await handle_skullboard_reaction_add(bot, payload)

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


async def on_raw_reaction_remove(
    bot: commands.Bot, payload: discord.RawReactionActionEvent
):
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
    error_id = uuid.uuid4().hex[:8]
    cid = get_log_channel(inter.guild.id) if inter.guild else None
    log_ch = bot.get_channel(cid) if cid else None
    central_log = bot.get_channel(ERROR_LOG_CHANNEL_ID)

    embed = discord.Embed(
        title="Command error",
        colour=discord.Colour.red(),
        timestamp=datetime.utcnow(),
        description=f"```py\n{error}\n```",
    )
    embed.add_field(name="Command", value=inter.command.qualified_name)
    embed.add_field(
        name="User", value=f"{inter.user} (`{inter.user.id}`)", inline=False
    )
    embed.add_field(name="Channel", value=f"{inter.channel.mention}", inline=False)
    if inter.guild:
        embed.add_field(
            name="Guild", value=f"{inter.guild} (`{inter.guild_id}`)", inline=False
        )
    embed.add_field(name="Error ID", value=error_id, inline=False)
    embed.add_field(
        name="Error report",
        value="You can report the error in with the error number in this server: https://discord.gg/CfYdVBdg7v",
    )
    if central_log:
        await central_log.send(embed=embed)
    if log_ch and log_ch != central_log:
        await log_ch.send(embed=embed)
    if isinstance(error, CommandOnCooldown):
        await inter.response.send_message(
            f"⏱ Cooldown: try again in {error.retry_after:.0f}s.", ephemeral=True
        )
        return
    logging.exception(f"Slash-command error {error_id}", exc_info=error)
    msg = f"Oops, something went wrong 😵 (Error ID: {error_id})"
    if inter.response.is_done():
        await inter.followup.send(msg, ephemeral=True)
    else:
        await inter.response.send_message(msg, ephemeral=True)


async def on_command_error(
    bot: commands.Bot, ctx: commands.Context, error: commands.CommandError
):
    if isinstance(error, commands.CommandNotFound):
        return
    error_id = uuid.uuid4().hex[:8]
    cid = get_log_channel(ctx.guild.id) if ctx.guild else None
    log_ch = bot.get_channel(cid) if cid else None
    central_log = bot.get_channel(ERROR_LOG_CHANNEL_ID)

    embed = discord.Embed(
        title="Command error",
        colour=discord.Colour.red(),
        timestamp=datetime.utcnow(),
        description=f"```py\n{error}\n```",
    )
    cmd_name = ctx.command.qualified_name if ctx.command else "Unknown"
    embed.add_field(name="Command", value=cmd_name)
    embed.add_field(
        name="User", value=f"{ctx.author} (`{ctx.author.id}`)", inline=False
    )
    embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
    if ctx.guild:
        embed.add_field(
            name="Guild", value=f"{ctx.guild} (`{ctx.guild.id}`)", inline=False
        )
    embed.add_field(name="Error ID", value=error_id, inline=False)
    if central_log:
        await central_log.send(embed=embed)
    if log_ch and log_ch != central_log:
        await log_ch.send(embed=embed)
    logging.exception(f"Prefix command error {error_id}", exc_info=error)
    await ctx.send(f"Oops, something went wrong 😵 (Error ID: {error_id})")


def format_options(data: dict, interaction: discord.Interaction) -> str:
    result = []
    resolved = data.get("resolved", {})
    users_data = resolved.get("users", {}) if resolved else {}
    for opt in data.get("options", []):
        if opt.get("type") == 1:
            inner = (
                ", ".join(_format_option(o, users_data) for o in opt.get("options", []))
                or "–"
            )
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


async def on_app_command_completion(
    bot: commands.Bot, inter: discord.Interaction, command: app_commands.Command
):
    cid = get_log_channel(inter.guild.id) if inter.guild else None
    log_ch = bot.get_channel(cid) if cid else None
    if not log_ch:
        return
    opts = format_options(inter.data, inter)
    embed = discord.Embed(
        title="Command executed",
        colour=discord.Colour.blue(),
        timestamp=datetime.utcnow(),
    )
    embed.add_field(name="Command", value=f"/{command.qualified_name}")
    embed.add_field(
        name="User", value=f"{inter.user} (`{inter.user.id}`)", inline=False
    )
    embed.add_field(name="Channel", value=inter.channel.mention, inline=False)
    embed.add_field(name="Options", value=opts, inline=False)
    await log_ch.send(embed=embed)


def setup(bot: commands.Bot, lowercase_locked: dict[int, set[int]]):
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

    async def command_completion_wrapper(
        inter: discord.Interaction, command: app_commands.Command
    ):
        await on_app_command_completion(bot, inter, command)

    async def reaction_add_wrapper(payload: discord.RawReactionActionEvent):
        await on_raw_reaction_add(bot, payload)

    async def reaction_remove_wrapper(payload: discord.RawReactionActionEvent):
        await on_raw_reaction_remove(bot, payload)

    async def app_error_wrapper(inter: discord.Interaction, error: Exception):
        await on_app_error(bot, inter, error)

    async def command_error_wrapper(
        ctx: commands.Context, error: commands.CommandError
    ):
        await on_command_error(bot, ctx, error)

    bot.add_listener(ready_wrapper, name="on_ready")
    bot.add_listener(member_update_wrapper, name="on_member_update")
    bot.add_listener(message_wrapper, name="on_message")
    bot.add_listener(member_join_wrapper, name="on_member_join")
    bot.add_listener(member_remove_wrapper, name="on_member_remove")
    bot.add_listener(reaction_add_wrapper, name="on_raw_reaction_add")
    bot.add_listener(reaction_remove_wrapper, name="on_raw_reaction_remove")
    bot.tree.error(app_error_wrapper)
    bot.add_listener(command_completion_wrapper, name="on_app_command_completion")
    bot.add_listener(command_error_wrapper, name="on_command_error")
