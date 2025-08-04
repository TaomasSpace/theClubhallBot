import asyncio
import inspect
import io


import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

from config import LOG_CHANNEL_ID
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
    set_welcome_channel,
    set_leave_channel,
    set_welcome_message,
    set_leave_message,
    set_booster_channel,
    set_booster_message,
    set_role,
    get_role,
    set_command_permission,
)
from utils import has_role, has_command_permission, get_channel_webhook, parse_duration


async def run_command_tests(bot: commands.Bot) -> dict[str, str]:
    results: dict[str, str] = {}

    class DummyRole:
        def __init__(self, name: str = "role", role_id: int = 0):
            self.id = role_id
            self.name = name

        @property
        def mention(self) -> str:  # pragma: no cover - simple placeholder
            return f"<@&{self.id}>"

    class DummyResponse:
        async def send_message(self, *args, **kwargs):
            pass

        async def defer(self, *args, **kwargs):
            pass

    class DummyFollowup:
        async def send(self, *args, **kwargs):
            pass

    class DummyGuild:
        def __init__(self):
            self.roles: list[DummyRole] = []
            self.members: list[DummyUser] = []  # type: ignore[name-defined]

        def get_role(self, role_id: int):
            for role in self.roles:
                if role.id == role_id:
                    return role
            return None

        def get_member(self, user_id: int):
            for member in self.members:
                if member.id == user_id:
                    return member
            return None

        async def create_role(self, name: str, **kwargs):
            role = DummyRole(name=name)
            self.roles.append(role)
            return role

    class DummyMessage:
        def __init__(self, content="dummy"):
            self.content = content
            self.reactions = []

        async def add_reaction(self, emoji):
            self.reactions.append(emoji)

        async def edit(self, **kwargs):
            self.content = kwargs.get("content", self.content)

        async def reply(self, *args, **kwargs):
            pass  # Placeholder

    class DummyUser:
        def __init__(
            self,
            user_id: int = 0,
            name: str = "tester",
            guild: DummyGuild | None = None,
        ):

            self.id = user_id
            self.name = name
            self.display_name = name
            self.roles: list[DummyRole] = []
            self.guild_permissions = discord.Permissions.none()
            self.premium_since = None
            self.guild = guild

        @property
        def mention(self) -> str:  # pragma: no cover - simple placeholder
            return f"<@{self.id}>"

        async def add_roles(self, *roles, **kwargs):
            self.roles.extend(roles)

        async def remove_roles(self, *roles, **kwargs):
            for role in roles:
                if role in self.roles:
                    self.roles.remove(role)

    class DummyChannel:
        id = 0

    dummy_guild = DummyGuild()
    dummy_role = DummyRole(name="role", role_id=1)
    dummy_guild.roles.append(dummy_role)

    dummy_user = DummyUser(guild=dummy_guild)
    dummy_target = DummyUser(user_id=1, name="target", guild=dummy_guild)
    dummy_guild.members.extend([dummy_user, dummy_target])

    class DummyInteraction:
        user = dummy_user
        guild = dummy_guild
        channel = DummyChannel()
        response = DummyResponse()
        followup = DummyFollowup()

        def __init__(self):
            self._message = DummyMessage()

        async def original_response(self):
            return self._message

    dummy = DummyInteraction()

    def get_dummy_arg(p: inspect.Parameter):  # pragma: no cover - heuristic mapping
        ann = p.annotation
        name = p.name.lower()
        origin = getattr(ann, "__origin__", None)
        if origin is not None:
            ann = origin
        if ann in (discord.Member, discord.User):
            return dummy_target
        if ann is discord.Role:
            return dummy_role
        if ann in (
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.CategoryChannel,
            discord.ForumChannel,
        ):
            return DummyChannel()
        if ann is discord.Guild:
            return dummy_guild
        if ann is int:
            return 1
        if ann is float:
            return 1.0
        if ann is bool:
            return False
        if ann is str or ann is inspect._empty:
            if "time" in name or "duration" in name:
                return "1h"
            if "reason" in name:
                return "test reason"
            if "color" in name or "colour" in name:
                return "#ffffff"
            return "test"
        if ann is datetime:
            return datetime.now(timezone.utc)
        return None

    for cmd in bot.tree.get_commands():
        try:
            sig = inspect.signature(cmd.callback)
            params = list(sig.parameters.values())[1:]
            args = []
            for p in params:
                if p.default is inspect.Parameter.empty:
                    args.append(get_dummy_arg(p))
                else:
                    args.append(p.default)

            await cmd.callback(dummy, *args)
            results[cmd.name] = "OK"
        except Exception as e:
            results[cmd.name] = f"Error: {e}"
    return results


active_prison_timers: dict[int, asyncio.Task] = {}


def setup(bot: commands.Bot):
    @bot.tree.command(name="test", description="Test all commands")
    async def test_commands(inter: discord.Interaction):
        if not has_command_permission(inter.user, "test", "admin"):
            await inter.response.send_message("No permission.", ephemeral=True)
            return
        await inter.response.defer(thinking=True, ephemeral=True)
        results = await run_command_tests(bot)
        report_lines = [f"{name}: {status}" for name, status in results.items()]
        report = "\n".join(report_lines)
        if len(report) > 1900:
            file = discord.File(io.StringIO(report), filename="command_report.txt")
            await inter.followup.send("**Testergebnis**:", file=file, ephemeral=True)
        else:
            await inter.followup.send(f"**Testergebnis**:\n{report}", ephemeral=True)

    @bot.tree.command(
        name="setstatpoints", description="Set a user's stat points (Admin only)"
    )
    @app_commands.describe(user="Target user", amount="New amount of stat points")
    async def setstatpoints(
        interaction: discord.Interaction, user: discord.Member, amount: int
    ):
        if not has_command_permission(interaction.user, "setstatpoints", "admin"):
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
            not has_command_permission(interaction.user, "lastdate", "admin")
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
        if not has_command_permission(interaction.user, "setstat", "admin"):
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
        if not has_command_permission(inter.user, "addshoprole", "admin"):
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
        if not has_command_permission(interaction.user, "manageprisonmember", "mod"):
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
            not has_command_permission(interaction.user, "manageviltrumite", "admin")
            and interaction.user.id != 1068512374719520768
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
        name="manageyeager",
        description="Give or remove the Yeager role from a member.",
    )
    @app_commands.describe(user="the user you want to add/remove the Yeager role")
    async def manageYeager(interaction: discord.Interaction, user: discord.Member):
        if (
            not has_command_permission(interaction.user, "manageyeager", "admin")
            and interaction.user.id != 1348356899354972180
        ):
            await interaction.response.send_message(
                "You dont have permission to use this command.", ephemeral=True
            )
            return

        if has_role(user, 1392537949639544852):
            await user.remove_roles(
                discord.utils.get(interaction.guild.roles, name="yeager")
            )
            await interaction.response.send_message(
                "Yeager role removed from " + user.display_name
            )
            return
        else:
            await user.add_roles(
                discord.utils.get(interaction.guild.roles, name="yeager")
            )
            await interaction.response.send_message(
                "Yeager role added to " + user.display_name
            )
            return

    @bot.tree.command(
        name="manageackerman",
        description="Give or remove the ackerman  role from a member.",
    )
    @app_commands.describe(user="the user you want to add/remove the ackerman  role")
    async def manageackerman(interaction: discord.Interaction, user: discord.Member):
        if (
            not has_command_permission(interaction.user, "manageackerman", "admin")
            and interaction.user.id != 1348356899354972180
        ):
            await interaction.response.send_message(
                "You dont have permission to use this command.", ephemeral=True
            )
            return

        if has_role(user, 1392537815132147904):
            await user.remove_roles(
                discord.utils.get(interaction.guild.roles, name="ackerman")
            )
            await interaction.response.send_message(
                "ackerman role removed from " + user.display_name
            )
            return
        else:
            await user.add_roles(
                discord.utils.get(interaction.guild.roles, name="ackerman")
            )
            await interaction.response.send_message(
                "ackerman role added to " + user.display_name
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
        if not has_command_permission(
            interaction.user, "addcolorreactionrole", "admin"
        ):
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
            not has_command_permission(interaction.user, "giveaway", "admin")
            and interaction.user.id != 875279455222898698
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
        if not has_command_permission(interaction.user, "lock", "admin"):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        lock_id = get_role("channel_lock")
        role = interaction.guild.get_role(lock_id) if lock_id else None
        if role is None:
            await interaction.response.send_message("Role not found.", ephemeral=True)
            return
        await interaction.channel.set_permissions(role, send_messages=False)
        await interaction.response.send_message(
            "\U0001f512 Channel locked.", ephemeral=True
        )

    @bot.tree.command(name="unlock", description="Unlock this channel (Admin only)")
    async def unlock_channel(interaction: discord.Interaction):
        if not has_command_permission(interaction.user, "unlock", "admin"):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        lock_id = get_role("channel_lock")
        role = interaction.guild.get_role(lock_id) if lock_id else None
        if role is None:
            await interaction.response.send_message("Role not found.", ephemeral=True)
            return
        await interaction.channel.set_permissions(role, send_messages=True)
        await interaction.response.send_message(
            "\U0001f513 Channel unlocked.", ephemeral=True
        )

    @bot.tree.command(name="addfilterword", description="Add a word to the filter list")
    @app_commands.describe(word="Word to filter")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def addfilterword(interaction: discord.Interaction, word: str):
        from db.DBHelper import add_filtered_word

        add_filtered_word(word)
        await interaction.response.send_message(
            f"\u2705 Added `{word}` to the filter.", ephemeral=True
        )

    @bot.tree.command(
        name="removefilterword", description="Remove a word from the filter list"
    )
    @app_commands.describe(word="Word to remove")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def removefilterword(interaction: discord.Interaction, word: str):
        from db.DBHelper import remove_filtered_word

        remove_filtered_word(word)
        await interaction.response.send_message(
            f"\u2705 Removed `{word}` from the filter.", ephemeral=True
        )

    @bot.tree.command(name="filterwords", description="Show all filtered words")
    async def filterwords(interaction: discord.Interaction):
        from db.DBHelper import get_filtered_words

        words = get_filtered_words()
        if not words:
            await interaction.response.send_message("No filtered words.")
            return
        await interaction.response.send_message(", ".join(sorted(words)))

    @bot.tree.command(name="addtrigger", description="Add a trigger response")
    @app_commands.describe(trigger="Trigger word", response="Response message")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def addtrigger(
        interaction: discord.Interaction, trigger: str, response: str
    ):
        from db.DBHelper import add_trigger_response
        from events import trigger_responses

        add_trigger_response(trigger, response)
        trigger_responses[trigger.lower()] = response
        await interaction.response.send_message(
            f"\u2705 Added trigger `{trigger}`.", ephemeral=True
        )

    @bot.tree.command(name="removetrigger", description="Remove a trigger response")
    @app_commands.describe(trigger="Trigger word")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def removetrigger(interaction: discord.Interaction, trigger: str):
        from db.DBHelper import remove_trigger_response
        from events import trigger_responses

        remove_trigger_response(trigger)
        trigger_responses.pop(trigger.lower(), None)
        await interaction.response.send_message(
            f"\u2705 Removed trigger `{trigger}`.", ephemeral=True
        )

    @bot.tree.command(name="triggers", description="Show all trigger responses")
    async def triggers(interaction: discord.Interaction):
        from db.DBHelper import get_trigger_responses

        data = get_trigger_responses()
        if not data:
            await interaction.response.send_message("No trigger responses.")
            return
        await interaction.response.send_message(", ".join(sorted(data.keys())))

    @bot.tree.command(name="setwelcomechannel", description="Set the welcome channel")
    @app_commands.describe(channel="Channel for welcome messages")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setwelcomechannel(
        interaction: discord.Interaction, channel: discord.TextChannel
    ):
        set_welcome_channel(channel.id)
        await interaction.response.send_message(
            f"\u2705 Welcome channel set to {channel.mention}.", ephemeral=True
        )

    @bot.tree.command(name="setleavechannel", description="Set the leave channel")
    @app_commands.describe(channel="Channel for leave messages")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setleavechannel(
        interaction: discord.Interaction, channel: discord.TextChannel
    ):
        set_leave_channel(channel.id)
        await interaction.response.send_message(
            f"\u2705 Leave channel set to {channel.mention}.", ephemeral=True
        )

    @bot.tree.command(name="setwelcomemsg", description="Set the welcome message")
    @app_commands.describe(
        message="Message; placeholders: {member}, {member_mention}, {server}, {member_count}"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setwelcomemsg(interaction: discord.Interaction, message: str):
        set_welcome_message(message)
        await interaction.response.send_message(
            "\u2705 Welcome message updated.", ephemeral=True
        )

    @bot.tree.command(name="setleavemsg", description="Set the leave message")
    @app_commands.describe(
        message="Message; placeholders: {member}, {member_mention}, {server}, {member_count}"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setleavemsg(interaction: discord.Interaction, message: str):
        set_leave_message(message)
        await interaction.response.send_message(
            "\u2705 Leave message updated.", ephemeral=True
        )

    @bot.tree.command(name="setboostchannel", description="Set the booster channel")
    @app_commands.describe(channel="Channel for booster messages")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setboostchannel(
        interaction: discord.Interaction, channel: discord.TextChannel
    ):
        set_booster_channel(channel.id)
        await interaction.response.send_message(
            f"\u2705 Booster channel set to {channel.mention}.", ephemeral=True
        )

    @bot.tree.command(name="setboostmsg", description="Set the booster message")
    @app_commands.describe(
        message="Message; placeholders: {member}, {member_mention}, {server}"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setboostmsg(interaction: discord.Interaction, message: str):
        set_booster_message(message)
        await interaction.response.send_message(
            "\u2705 Booster message updated.", ephemeral=True
        )

    @bot.tree.command(name="setrole", description="Configure a role used by the bot")
    @app_commands.describe(
        name="Which role to configure (admin/mod/sheher/hehim/channel_lock)",
        role="The role to use",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setrole(
        interaction: discord.Interaction, name: str, role: discord.Role
    ):
        key = name.lower()
        valid = {"admin", "mod", "sheher", "hehim", "channel_lock"}
        if key not in valid:
            await interaction.response.send_message(
                "\u274c Invalid role name.", ephemeral=True
            )
            return
        set_role(key, role.id)
        await interaction.response.send_message(
            f"\u2705 Set {key} role to {role.mention}.", ephemeral=True
        )

    @bot.tree.command(name="setcommandrole", description="Set required role for a command")
    @app_commands.describe(command="Command name", role="Role allowed to use the command")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setcommandrole(
        interaction: discord.Interaction, command: str, role: discord.Role
    ):
        set_command_permission(command, role.id)
        await interaction.response.send_message(
            f"\u2705 Set {command} command role to {role.mention}.", ephemeral=True
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
        addfilterword,
        removefilterword,
        filterwords,
        addtrigger,
        removetrigger,
        triggers,
        setwelcomechannel,
        setleavechannel,
        setwelcomemsg,
        setleavemsg,
        setboostchannel,
        setboostmsg,
        setrole,
        createrole,
        manageViltrumite,
        manageYeager,
        manageackerman,
    )
