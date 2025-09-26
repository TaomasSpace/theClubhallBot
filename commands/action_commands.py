import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from random import randint, random

from db.DBHelper import (
    register_user,
    get_stats,
    get_money,
    set_money,
    safe_add_coins,
)
from .hybrid_helpers import respond

hack_cooldowns: dict[int, datetime] = {}
fight_cooldowns: dict[int, datetime] = {}
steal_cooldowns: dict[int, datetime] = {}


async def _respond(
    ctx: commands.Context,
    *,
    content: str | None = None,
    embed: discord.Embed | None = None,
    ephemeral: bool = False,
) -> None:
    """Send a response for both prefix and slash command invocations."""

    if ctx.interaction:
        interaction = ctx.interaction
        if interaction.response.is_done():
            await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)

        else:
            await interaction.response.send_message(
                content=content, embed=embed, ephemeral=ephemeral
            )
        return

    send_kwargs = {}
    if content is not None:
        send_kwargs["content"] = content
    if embed is not None:
        send_kwargs["embed"] = embed
    await ctx.send(**send_kwargs)


def setup(bot: commands.Bot):
    @bot.hybrid_command(
        name="steal",
        description="Attempt to steal coins from another user (needs stealth \u2265 3)",
    )
    @app_commands.describe(target="Member to steal from")
    async def steal(ctx: commands.Context, target: discord.Member):
        if target.id == ctx.author.id:
            await respond(ctx, content="You can't steal from yourself!", ephemeral=True)

            return
        uid, tid = str(ctx.author.id), str(target.id)
        now = datetime.utcnow()
        cooldown = steal_cooldowns.get(ctx.author.id)
        if cooldown and now - cooldown < timedelta(minutes=45):
            remaining = timedelta(minutes=45) - (now - cooldown)
            minutes, seconds = divmod(int(remaining.total_seconds()), 60)
            await respond(

                ctx,
                content=f"\u23f3 You can steal again in **{minutes} minutes {seconds} seconds**.",
                ephemeral=True,
            )
            return
        register_user(uid, ctx.author.display_name)
        register_user(tid, target.display_name)
        actor_stats = get_stats(uid)
        target_stats = get_stats(tid)
        if actor_stats["stealth"] < 3:
            await respond(

                ctx,
                content="You need at least **3** Stealth to attempt a steal.",
                ephemeral=True,
            )
            return
        actor_stealth, target_stealth = actor_stats["stealth"], target_stats["stealth"]
        success_chance = actor_stealth / (actor_stealth + target_stealth)
        if random() > success_chance:
            await respond(

                ctx,
                content="\U0001f440 You were caught and failed to steal any coins!",
                ephemeral=True,
            )
            return
        target_balance = get_money(tid)
        if target_balance < 5:
            await respond(ctx, content="Target is too poor to bother...", ephemeral=True)

            return
        max_pct = min(0.05 + 0.02 * max(actor_stealth - target_stealth, 0), 0.25)
        stolen_pct = random() * max_pct
        stolen_amt = max(1, int(target_balance * stolen_pct))
        set_money(tid, target_balance - stolen_amt)
        safe_add_coins(uid, stolen_amt)
        steal_cooldowns[ctx.author.id] = datetime.utcnow()
        await respond(

            ctx,
            content=(
                f"\U0001f576\ufe0f Success! You stole **{stolen_amt}** coins from {target.display_name}."
            ),
            ephemeral=True,
        )

    @bot.hybrid_command(
        name="hack", description="Hack the bank to win coins (needs intelligence \u2265 3)"

    )
    async def hack(ctx: commands.Context):
        uid = str(ctx.author.id)
        register_user(uid, ctx.author.display_name)
        now = datetime.utcnow()
        cooldown = hack_cooldowns.get(ctx.author.id)
        if cooldown and now - cooldown < timedelta(minutes=45):
            remaining = timedelta(minutes=45) - (now - cooldown)
            minutes, seconds = divmod(int(remaining.total_seconds()), 60)
            await respond(

                ctx,
                content=f"\u23f3 You can hack again in **{minutes} minutes {seconds} seconds**.",
                ephemeral=True,
            )
            return
        stats = get_stats(uid)
        if stats["intelligence"] < 3:
            await respond(

                ctx,
                content="\u274c You need at least **3** Intelligence to attempt a hack.",
                ephemeral=True,
            )
            return
        int_level = stats["intelligence"]
        success = random() < min(0.20 + 0.05 * (int_level - 3), 0.80)
        hack_cooldowns[ctx.author.id] = now
        if not success:
            loss = randint(1, 5) * int_level
            new_bal = max(0, get_money(uid) - loss)
            set_money(uid, new_bal)
            await respond(

                ctx,
                content=(
                    f"\U0001f4bb Hack failed! Security traced you and you lost **{loss}** coins."
                ),
                ephemeral=True,
            )
            return
        reward = randint(5, 12) * int_level
        added = safe_add_coins(uid, reward)
        if added > 0:
            await respond(

                ctx,
                content=(
                    f"\U0001f50b Hack successful! You siphoned **{added}** coins from the bank."
                ),
                ephemeral=True,
            )
        else:
            await respond(

                ctx,
                content=(
                    "\u26a0\ufe0f Hack succeeded but server coin limit reached. No coins added."
                ),
                ephemeral=True,
            )

    @bot.hybrid_command(
        name="fight", description="Fight someone for coins (needs strength \u2265 3)"
    )
    @app_commands.describe(target="Member to fight")
    async def fight(ctx: commands.Context, target: discord.Member):
        if target.id == ctx.author.id:
            await respond(ctx, content="You can't fight yourself!", ephemeral=True)

            return
        uid, tid = str(ctx.author.id), str(target.id)
        now = datetime.utcnow()
        cooldown = fight_cooldowns.get(ctx.author.id)
        if cooldown and now - cooldown < timedelta(minutes=45):
            remaining = timedelta(minutes=45) - (now - cooldown)
            minutes, seconds = divmod(int(remaining.total_seconds()), 60)
            await respond(

                ctx,
                content=f"\u23f3 You can fight again in **{minutes} minutes {seconds} seconds**.",
                ephemeral=True,
            )
            return
        register_user(uid, ctx.author.display_name)
        register_user(tid, target.display_name)
        atk = get_stats(uid)
        defn = get_stats(tid)
        if atk["strength"] < 3:
            await respond(

                ctx,
                content="You need at least **3** Strength to start a fight.",
                ephemeral=True,
            )
            return
        atk_str, def_str = atk["strength"], defn["strength"]
        win_chance = atk_str / (atk_str + def_str)
        if random() > win_chance:
            penalty = max(1, int(get_money(uid) * 0.10))
            set_money(uid, get_money(uid) - penalty)
            safe_add_coins(tid, penalty)
            await respond(

                ctx,
                content=(
                    f"\U0001f3cb\ufe0f You lost the fight and paid **{penalty}** coins in damages to {target.display_name}."
                ),
                ephemeral=True,
            )
            return
        target_coins = get_money(tid)
        steal_pct = random() * min(0.05 + 0.03 * max(atk_str - def_str, 0), 0.20)
        stolen = max(1, int(target_coins * steal_pct))
        set_money(tid, target_coins - stolen)
        safe_add_coins(uid, stolen)
        fight_cooldowns[ctx.author.id] = datetime.utcnow()
        await respond(

            ctx,
            content=(
                f"\U0001f4aa Victory! You took **{stolen}** coins from {target.display_name}."
            ),
            ephemeral=True,
        )

    return steal, hack, fight
