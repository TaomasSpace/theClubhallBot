import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

from config import (
    ADMIN_ROLE_ID,
    SHEHER_ROLE_ID,
    HEHIM_ROLE_ID,
    LOG_CHANNEL_ID,
    MOD_ROLE_ID,
)
from config import CHANNEL_LOCK_ROLE_ID
from db.DBHelper import (
    register_user,
    _fetchone,
    add_shop_role,
    get_shop_roles,
    get_money,
    set_money,
    safe_add_coins,
    get_last_weekly,
    set_last_weekly,
    get_last_claim,
    set_last_claim,
    get_custom_role,
    set_custom_role,
    delete_custom_role,
    create_giveaway,
)
from utils import has_role, get_channel_webhook, parse_duration

active_prison_timers: dict[int, asyncio.Task] = {}


def setup(bot: commands.Bot):
    @bot.tree.command(
        name="setstatpoints", description="Set a user's stat points (Admin only)"
    )
    @app_commands.describe(user="Target user", amount="New amount of stat points")
    async def setstatpoints(
        interaction: discord.Interaction, user: discord.Member, amount: int
    ):
        if not has_role(interaction.user, ADMIN_ROLE_ID):
            await interaction.response.send_message(
                "Only the Owner can use this command.", ephemeral=True
            )
            return
        if amount < 0:
            await interaction.response.send_message(
                "Amount must be \u2265 0.", ephemeral=True
            )
            return
        uid = str(user.id)
        register_user(uid, user.display_name)
        _execute = __import__("db.DBHelper", fromlist=["_execute"])._execute
        _execute("UPDATE users SET stat_points = ? WHERE user_id = ?", (amount, uid))
        await interaction.response.send_message(
            f"\u2705 Set {user.display_name}'s stat points to {amount}.", ephemeral=True
        )

    @bot.tree.command(
        name="lastdate", description="Get a last date of user (Admin/Owner only)"
    )
    @app_commands.describe(user="User")
    async def lastdate(interaction: discord.Interaction, user: discord.Member):
        if (
            not has_role(interaction.user, ADMIN_ROLE_ID)
            and not interaction.user.premium_since
        ):
            await interaction.response.send_message(
                "You don't have permission to use this command.", ephemeral=True
            )
            return
        from db.DBHelper import get_lastdate

        await interaction.response.send_message(get_lastdate(user.id), ephemeral=True)

    @bot.tree.command(name="setstat", description="Set a user's stat (Owner only)")
    @app_commands.describe(
        user="Target user",
        stat="Which stat to set (intelligence, strength, stealth)",
        amount="New stat value (\u2265 0)",
    )
    async def setstat(
        interaction: discord.Interaction, user: discord.Member, stat: str, amount: int
    ):
        if not has_role(interaction.user, ADMIN_ROLE_ID):
            await interaction.response.send_message(
                "Only the Owner can use this command.", ephemeral=True
            )
            return
        from config import STAT_NAMES

        stat = stat.lower()
        if stat not in STAT_NAMES:
            await interaction.response.send_message(
                "Invalid stat name.", ephemeral=True
            )
            return
        if amount < 0:
            await interaction.response.send_message(
                "Amount must be \u2265 0.", ephemeral=True
            )
            return
        uid = str(user.id)
        register_user(uid, user.display_name)
        _execute = __import__("db.DBHelper", fromlist=["_execute"])._execute
        _execute(f"UPDATE users SET {stat} = ? WHERE user_id = ?", (amount, uid))
        await interaction.response.send_message(
            f"\u2705 Set {user.display_name}'s **{stat}** to **{amount}**.",
            ephemeral=True,
        )

    @bot.tree.command(
        name="addshoprole",
        description="Create/register a purchasable role (Owner/Admin)",
    )
    @app_commands.describe(
        name="Role name",
        price="Cost in coins",
        color="#RRGGBB (hex)",
        reference="Put the new role relative to this role (optional)",
        above="If True, place *above* the reference; else below",
    )
    async def addshoprole(
        inter: discord.Interaction,
        name: str,
        price: int,
        color: str,
        reference: discord.Role | None = None,
        above: bool = True,
    ):
        if not has_role(inter.user, ADMIN_ROLE_ID):
            await inter.response.send_message("No permission.", ephemeral=True)
            return
        try:
            colour_obj = discord.Colour(int(color.lstrip("#"), 16))
        except ValueError:
            await inter.response.send_message(
                "\u26a0\ufe0f Invalid hex color.", ephemeral=True
            )
            return
        guild = inter.guild
        role = discord.utils.get(guild.roles, name=name)
        if role is None:
            role = await guild.create_role(
                name=name, colour=colour_obj, reason="Shop role"
            )
        if reference:
            new_pos = reference.position + (1 if above else 0)
            try:
                await role.edit(position=new_pos)
            except discord.Forbidden:
                await inter.response.send_message(
                    "\u274c Bot kann die Rolle nicht verschieben. Achte darauf, dass seine h\xf6chste Rolle \xfcber dem Ziel steht.",
                    ephemeral=True,
                )
                return
        add_shop_role(role.id, price)
        await inter.response.send_message(
            f"\u2705 Rolle **{role.name}** registriert (Preis {price} Coins).",
            ephemeral=True,
        )

    @bot.tree.command(name="shop", description="Show all purchasable roles")
    async def shop(inter: discord.Interaction):
        entries = get_shop_roles()
        if not entries:
            await inter.response.send_message("The shop is empty.", ephemeral=True)
            return
        lines = []
        for rid, price in entries:
            role = inter.guild.get_role(int(rid))
            if role:
                lines.append(f"{role.mention} – **{price}** Coins")
        embed = discord.Embed(
            title="\U0001f6d2 Role Shop", description="\n".join(lines)
        )
        await inter.response.send_message(embed=embed)

    @bot.tree.command(name="buyrole", description="Buy a role from the shop")
    async def buyrole(inter: discord.Interaction, role: discord.Role):
        row = _fetchone("SELECT price FROM shop_roles WHERE role_id = ?", (role.id,))
        if not row:
            await inter.response.send_message(
                "This role does not exist in the shop.", ephemeral=True
            )
            return
        price = row[0]
        uid = str(inter.user.id)
        register_user(uid, inter.user.display_name)
        balance = get_money(uid)
        if balance < price:
            await inter.response.send_message(
                "\u274c Not enough coins.", ephemeral=True
            )
            return
        set_money(uid, balance - price)
        await inter.user.add_roles(role, reason="Shop purchase")
        await inter.response.send_message(
            f"\U0001f389 Congratulation! You bought **{role.name}** for {price} clubhall coins."
        )

    @bot.tree.command(
        name="manageprisonmember", description="Send or free someone from prison"
    )
    @app_commands.describe(
        user="Person you want to lock or free in prison",
        time="Duration (e.g. 10m, 2h) or 'cancel'",
    )
    async def managePrisonMember(
        interaction: discord.Interaction, user: discord.Member, time: str | None = None
    ):
        if not has_role(interaction.user, MOD_ROLE_ID):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        gooyb = interaction.user.name == "goodyb"
        role_name = "Guest of the Cyber Café"
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            await interaction.response.send_message(
                f"\u274c Role '{role_name}' not found.", ephemeral=True
            )
            return
        if time == "cancel":
            task = active_prison_timers.pop(user.id, None)
            if task and not task.done():
                task.cancel()
                await user.remove_roles(role)
                await interaction.response.send_message(
                    f"\U0001f54a\ufe0f Timer cancelled. {user.mention} has been freed.",
                    ephemeral=gooyb,
                )
            else:
                await interaction.response.send_message(
                    f"\u26a0\ufe0f No active timer for {user.mention}.", ephemeral=True
                )
            return
        if role not in user.roles:
            task = active_prison_timers.pop(user.id, None)
            if task and not task.done():
                task.cancel()
            await user.add_roles(role)
            await interaction.response.send_message(
                f"\U0001f513 {user.mention} has been freed from prison.",
                ephemeral=gooyb,
            )
            return
        await user.remove_roles(role)
        msg = f"\U0001f512 {user.mention} has been sent to prison."
        if time:
            seconds = parse_duration(time)
            if seconds is None:
                await interaction.response.send_message(
                    f"\u23f3 Invalid time format: `{time}`. Use `10m`, `2h`, etc.",
                    ephemeral=True,
                )
                return

            async def release_later():
                try:
                    await asyncio.sleep(seconds)
                    await user.add_roles(role)
                    await interaction.followup.send(
                        f"\U0001f54a\ufe0f {user.mention} has served their time and is now free.",
                        ephemeral=False,
                    )
                except asyncio.CancelledError:
                    pass

            task = asyncio.create_task(release_later())
            active_prison_timers[user.id] = task
            msg += f" They will be freed in {time}."
        await interaction.response.send_message(msg, ephemeral=False)

    @bot.tree.command(
        name="manageviltrumite",
        description="Give or remove the Viltrumite role from a member.",
    )
    @app_commands.describe(user="the user you want to add/remove the Viltrumite role")
    async def manageViltrumite(interaction: discord.Interaction, user: discord.Member):
        if (
            not has_role(interaction.user, ADMIN_ROLE_ID)
            and not interaction.user.id == 1068512374719520768
        ):
            await interaction.response.send_message(
                "You dont have permission to use this command.", ephemeral=True
            )
            return

        if has_role(user, 1387452893015052298):
            await user.remove_roles(
                discord.utils.get(interaction.guild.roles, name="Viltrumite")
            )
            await interaction.response.send_message(
                "Viltrumite role removed from " + user.display_name
            )
            return
        else:
            await user.add_roles(
                discord.utils.get(interaction.guild.roles, name="Viltrumite")
            )
            await interaction.response.send_message(
                "Viltrumite role added to " + user.display_name
            )
            return

    @bot.tree.command(
        name="addcolorreactionrole",
        description="Add emoji-role to color reaction message",
    )
    @app_commands.describe(emoji="Emoji to react with", role="Role to assign")
    async def addcolorreactionrole(
        interaction: discord.Interaction,
        target_message_id: str,
        emoji: str,
        role: discord.Role,
    ):
        if not has_role(interaction.user, ADMIN_ROLE_ID):
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
                f"\u2705 Added emoji {emoji} for role {role.name}.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"\u274c Error: {e}", ephemeral=True
            )

    @bot.tree.command(
        name="imitate", description="Imitate a user's message (Admin/Owner only)"
    )
    @app_commands.describe(user="User to imitate", msg="The message to send")
    async def imitate(interaction: discord.Interaction, user: discord.Member, msg: str):
        if (
            not has_role(interaction.user, ADMIN_ROLE_ID)
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
            await interaction.response.send_message(
                "\u2705 Message sent.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"\u274c Failed to imitate: {e}", ephemeral=True
            )

    @bot.tree.command(
        name="giveaway", description="Start a giveaway (only Admin/Owner)"
    )
    @app_commands.describe(
        duration="Duration in minutes", prize="Prize", winners="Number of winners"
    )
    async def giveaway(
        interaction: discord.Interaction, duration: int, prize: str, winners: int
    ):
        if (
            not has_role(interaction.user, ADMIN_ROLE_ID)
            and not interaction.user.id == 875279455222898698
        ):
            await interaction.response.send_message(
                "Only admins and owners can use this command", ephemeral=True
            )
            return
        if winners < 1:
            await interaction.response.send_message(
                "You need at least 1 winner.", ephemeral=True
            )
            return
        embed = discord.Embed(
            title="\U0001f389 GIVEAWAY \U0001f389",
            description=f"React with \U0001f389 to win **{prize}**!\n\U0001f514 Duration: **{duration} min**.\n\U0001f3c6 Winners: **{winners}**",
            color=discord.Color.gold(),
        )
        embed.set_footer(
            text=f"Created by: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.response.send_message(embed=embed)
        giveaway_msg = await interaction.original_response()
        await giveaway_msg.add_reaction("\U0001f389")
        end_time = datetime.now(timezone.utc) + timedelta(minutes=duration)
        create_giveaway(
            str(giveaway_msg.id), str(giveaway_msg.channel.id), end_time, prize, winners
        )
        from events import end_giveaway, active_giveaway_tasks

        async def end_later():
            try:
                await asyncio.sleep(duration * 60)
                await end_giveaway(
                    bot, giveaway_msg.channel.id, giveaway_msg.id, prize, winners
                )
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(end_later())
        active_giveaway_tasks[giveaway_msg.id] = task

    @bot.tree.command(name="lock", description="Lock this channel (Admin only)")
    async def lock_channel(interaction: discord.Interaction):
        if not has_role(interaction.user, ADMIN_ROLE_ID):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        role = interaction.guild.get_role(CHANNEL_LOCK_ROLE_ID)
        if role is None:
            await interaction.response.send_message("Role not found.", ephemeral=True)
            return
        await interaction.channel.set_permissions(role, send_messages=False)
        await interaction.response.send_message(
            "\U0001f512 Channel locked.", ephemeral=True
        )

    @bot.tree.command(name="unlock", description="Unlock this channel (Admin only)")
    async def unlock_channel(interaction: discord.Interaction):
        if not has_role(interaction.user, ADMIN_ROLE_ID):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        role = interaction.guild.get_role(CHANNEL_LOCK_ROLE_ID)
        if role is None:
            await interaction.response.send_message("Role not found.", ephemeral=True)
            return
        await interaction.channel.set_permissions(role, send_messages=True)
        await interaction.response.send_message(
            "\U0001f513 Channel unlocked.", ephemeral=True
        )

    @bot.tree.command(
        name="createrole",
        description="Create a role and assign to users (for goodyb & nannapat2410 only)",
    )
    @app_commands.describe(
        role_name="Name of the role",
        role_color="Hex color like #000000",
        member1="1st member",
        member2="2nd member",
        member3="3rd member",
        member4="4th member",
        member5="5th member",
    )
    async def createrole(
        interaction: discord.Interaction,
        role_name: str,
        role_color: str,
        member1: discord.Member,
        member2: discord.Member | None = None,
        member3: discord.Member | None = None,
        member4: discord.Member | None = None,
        member5: discord.Member | None = None,
    ):
        allowed_usernames = {"goodyb", "nannapat2410"}
        if interaction.user.name.lower() not in allowed_usernames:
            await interaction.response.send_message(
                "\u274c You don't have permission.", ephemeral=True
            )
            return
        try:
            colour_obj = discord.Colour(int(role_color.lstrip("#"), 16))
        except ValueError:
            await interaction.response.send_message(
                "\u26a0\ufe0f Invalid hex color.", ephemeral=True
            )
            return
        try:
            role = await interaction.guild.create_role(
                name=role_name, colour=colour_obj
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "\u274c I can't create roles.", ephemeral=True
            )
            return
        members = [
            m for m in [member1, member2, member3, member4, member5] if m is not None
        ]
        failed = []
        for m in members:
            try:
                await m.add_roles(role)
            except Exception:
                failed.append(m.display_name)
        msg = f"\u2705 Role **{role.name}** created and assigned to {len(members) - len(failed)} member(s)."
        if failed:
            msg += f"\n\u26a0\ufe0f Failed for: {', '.join(failed)}"
        await interaction.response.send_message(msg, ephemeral=True)

    return (
        setstatpoints,
        lastdate,
        setstat,
        addshoprole,
        shop,
        buyrole,
        managePrisonMember,
        addcolorreactionrole,
        imitate,
        giveaway,
        lock_channel,
        unlock_channel,
        createrole,
        manageViltrumite,
    )
