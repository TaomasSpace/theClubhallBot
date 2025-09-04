import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from random import choice, randint, random
import asyncio
from collections import Counter

from config import (
    STAT_PRICE,
    STAT_NAMES,
    QUEST_COOLDOWN_HOURS,
    FISHING_COOLDOWN_MINUTES,
)
from db.DBHelper import (
    register_user,
    safe_add_coins,
    get_stats,
    add_stat_points,
    increase_stat,
    get_timestamp,
    set_timestamp,
    get_rod_level,
    get_rod_multiplier,
    set_rod_level,
    get_money,
    set_money,
)

rod_shop: dict[int, tuple[int, float]] = {}


async def sync_stat_roles(member: discord.Member):
    stats = get_stats(str(member.id))
    from config import ROLE_THRESHOLDS

    for stat, (role_name, threshold) in ROLE_THRESHOLDS.items():
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role is None:
            continue
        has_r = role in member.roles
        meets = stats[stat] >= threshold
        if meets and not has_r:
            await member.add_roles(role, reason=f"{stat} {stats[stat]} = {threshold}")
        elif not meets and has_r:
            await member.remove_roles(
                role, reason=f"{stat} {stats[stat]} < {threshold}"
            )


def setup(bot: commands.Bot, shop: dict[int, tuple[int, float]]):
    global rod_shop
    rod_shop = shop

    @bot.tree.command(name="stats", description="Show your stats & unspent points")
    async def stats_cmd(
        interaction: discord.Interaction, user: discord.Member | None = None
    ):
        target = user or interaction.user
        register_user(str(target.id), target.display_name)
        stats = get_stats(str(target.id))
        description = "\n".join(f"**{s.title()}**: {stats[s]}" for s in STAT_NAMES)
        embed = discord.Embed(
            title=f"{target.display_name}'s Stats",
            description=description,
            colour=discord.Colour.green(),
        )
        embed.set_footer(text=f"Unspent points: {stats['stat_points']}")
        await interaction.response.send_message(embed=embed, ephemeral=(user is None))

    @bot.tree.command(
        name="quest", description="Complete a short quest to earn stat-points (3?h CD)"
    )
    async def quest(interaction: discord.Interaction):
        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        last = get_timestamp(uid, "last_quest")
        now = datetime.utcnow()
        if last and now - last < timedelta(hours=QUEST_COOLDOWN_HOURS):
            remain = timedelta(hours=QUEST_COOLDOWN_HOURS) - (now - last)
            hrs, sec = divmod(int(remain.total_seconds()), 3600)
            mins = sec // 60
            await interaction.response.send_message(
                f"⏳ Next quest in {hrs}h {mins}min.", ephemeral=True
            )
            return
        earned = randint(1, 3)
        add_stat_points(uid, earned)
        set_timestamp(uid, "last_quest", now)
        await interaction.response.send_message(
            f"✅ You completed the quest and earned **{earned}** stat-point(s)!",
            ephemeral=True,
        )

    @bot.tree.command(name="buypoints", description="Buy stat-points with coins")
    async def buypoints(interaction: discord.Interaction, amount: str = "1"):
        amountasInt = 1
        price_per_point = int(STAT_PRICE)
        if amount == "all":
            amountasInt = get_money(interaction.user.id) // price_per_point
        else:
            amountasInt = int(amount)
        if int(amountasInt) < 1:
            await interaction.response.send_message(
                "Specify a positive amount.", ephemeral=True
            )
            return
        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        cost = price_per_point * amountasInt
        balance = get_money(uid)
        if balance < cost:
            await interaction.response.send_message(
                f"💰 You need {cost} coins but only have {balance}.", ephemeral=True
            )
            return
        set_money(uid, balance - cost)
        add_stat_points(uid, amountasInt)
        await interaction.response.send_message(
            f"Purchased {amountasInt} point(s) for {cost} coins."
        )

    @bot.tree.command(
        name="allocate", description="Spend stat-points to increase a stat"
    )
    @app_commands.describe(
        stat="Which stat? (intelligence/strength/stealth)",
        points="How many points to allocate",
    )
    async def allocate(interaction: discord.Interaction, stat: str, points: str):
        stat = stat.lower()
        if stat not in STAT_NAMES:
            await interaction.response.send_message(
                "Invalid stat name.", ephemeral=True
            )
            return
        if points == "all":
            user_stats = get_stats(str(interaction.user.id))
            pointsAsInt = user_stats["stat_points"]
        else:
            pointsAsInt = int(points)
        if pointsAsInt < 1:
            await interaction.response.send_message(
                "Points must be > 0.", ephemeral=True
            )
            return
        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        user_stats = get_stats(uid)
        if user_stats["stat_points"] < pointsAsInt:
            await interaction.response.send_message(
                "Not enough unspent points.", ephemeral=True
            )
            return
        increase_stat(uid, stat, pointsAsInt)
        await sync_stat_roles(interaction.user)
        await interaction.response.send_message(
            f"{stat.title()} increased by {pointsAsInt}."
        )

    @bot.tree.command(name="fishing", description="Phish for stat-points")
    async def fish(interaction: discord.Interaction):
        fish_gifs = [
            "https://media.tenor.com/ceoQ6q8vfbQAAAAM/stark-goes-fishing-looking-sad.gif",
            "https://media.tenor.com/QnyltZCHI8cAAAAM/kirby-fishing.gif",
            "https://i.pinimg.com/originals/6b/22/a5/6b22a575b0c783615c2b77e67951758c.gif",
            "https://media.tenor.com/nUdopBNmWUIAAAAM/pain-kill.gif",
            "https://i.pinimg.com/originals/6c/0c/aa/6c0caaee431885fbae24e0ac36855af1.gif",
            "https://media.tenor.com/jMAXdnyH2GAAAAAM/ellenoar-seiran.gif",
            "https://media.tenor.com/xYR-Agrj9nIAAAAM/bofuri-maple-anime.gif",
            "https://64.media.tumblr.com/tumblr_ltojtsz13k1qmpg90o1_500.gif",
            "https://giffiles.alphacoders.com/131/131082.gif",
            "https://mir-s3-cdn-cf.behance.net/project_modules/source/0ab4b036812305.572a1cada9fdc.gif",
            "https://64.media.tumblr.com/bdd9da69dc4f84bd90bc65bd6f015b50/tumblr_okihcp5dkZ1rd4ymxo1_500.gif",
            "https://giffiles.alphacoders.com/176/176112.gif",
            "https://pa1.aminoapps.com/7516/f85e46bc6e0884f53e5dbb6336852bdf4ed917f9r1-500-245_hq.gif",
            "https://i.pinimg.com/originals/26/a4/8f/26a48f25f2d58a359afa156b03466baa.gif",
            "https://i.gifer.com/MtWY.gif",
            "https://64.media.tumblr.com/b288db5c592bb12deec4761e9549c8bb/tumblr_otnj940KHT1uep5pko2_r1_500.gif",
            "https://giffiles.alphacoders.com/999/99914.gif",
        ]
        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        last = get_timestamp(uid, "last_fishing")
        now = datetime.utcnow()
        if last and now - last < timedelta(minutes=FISHING_COOLDOWN_MINUTES):
            remain = timedelta(minutes=FISHING_COOLDOWN_MINUTES) - (now - last)
            minutes, seconds = divmod(int(remain.total_seconds()), 60)
            await interaction.response.send_message(
                f"⏳ You can fish again in **{minutes} minutes {seconds} seconds**.",
                ephemeral=True,
            )
            return
        rod_level = get_rod_level(uid)
        multiplier = get_rod_multiplier(rod_level)
        reward = random()
        if reward < 0.50:
            earned = int(randint(1, 5) * multiplier)
            add_stat_points(uid, earned)
            set_timestamp(uid, "last_fishing", now)
            gif_url = choice(fish_gifs)
            if gif_url:
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} has fished {earned} stat points",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                await interaction.response.send_message(embed=embed)
                return
            else:
                await interaction.response.send_message(
                    "No fishing GIFs found in the database.", ephemeral=False
                )
                return
        if reward < 0.85:
            earned = int(randint(10, 30) * multiplier)
            safe_add_coins(uid, earned)
            set_timestamp(uid, "last_fishing", now)
            gif_url = choice(fish_gifs)
            if gif_url:
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} has fished {earned} clubhall coins",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                await interaction.response.send_message(embed=embed)
                return
            else:
                await interaction.response.send_message(
                    "No fishing GIFs found in the database.", ephemeral=False
                )
                return
        else:
            earned = int(randint(45, 115) * multiplier)
            safe_add_coins(uid, earned)
            set_timestamp(uid, "last_fishing", now)
            gif_url = choice(fish_gifs)
            if gif_url:
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} has fished {earned} clubhall coins",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                await interaction.response.send_message(embed=embed)
                return
            else:
                await interaction.response.send_message(
                    "No fishing GIFs found in the database.", ephemeral=False
                )
                return

    @bot.tree.command(name="buyrod", description="Buy a fishing rod")
    @app_commands.describe(level="Rod level to buy")
    async def buyrod(interaction: discord.Interaction, level: int):
        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        if level not in rod_shop:
            await interaction.response.send_message(
                "This rod is not available.", ephemeral=True
            )
            return
        price, _ = rod_shop[level]
        balance = get_money(uid)
        if balance < price:
            await interaction.response.send_message(
                f"❌ Not enough coins. ({price} required)", ephemeral=True
            )
            return
        current_level = get_rod_level(uid)
        if level <= current_level:
            await interaction.response.send_message(
                "You already have this rod or better.", ephemeral=True
            )
            return
        set_money(uid, balance - price)
        set_rod_level(uid, level)
        await interaction.response.send_message(f"🎣 You bought Rod {level}!")

    # Dynamic rod additions are disabled; rods are defined in code (config.ROD_SHOP).

    @bot.tree.command(name="rodshop", description="Show available fishing rods")
    async def rodshop(inter: discord.Interaction):
        if not rod_shop:
            await inter.response.send_message(
                "🛒 The rod shop is empty.", ephemeral=True
            )
            return
        lines = [
            f"🎣 Rod {lvl}: **{price}** coins – {mult:.2f}× rewards"
            for lvl, (price, mult) in sorted(rod_shop.items())
        ]
        embed = discord.Embed(
            title="🎣 Rod Shop",
            description="\n".join(lines),
            color=discord.Color.teal(),
        )
        await inter.response.send_message(embed=embed)

    @bot.tree.command(name="myrod", description="Show your fishing rod")
    async def myrod(
        interaction: discord.Interaction, user: discord.Member | None = None
    ):
        target = user or interaction.user
        register_user(str(target.id), target.display_name)
        rod_level = get_rod_level(str(target.id))
        multiplier = get_rod_multiplier(rod_level)
        if rod_level == 0:
            desc = "You don't own a fishing rod."
        else:
            desc = f"Rod {rod_level} – {multiplier:.2f}× rewards"
        embed = discord.Embed(
            title=f"{target.display_name}'s Rod",
            description=desc,
            color=discord.Color.teal(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=(user is None))

    @bot.tree.command(
        name="refund", description="refund stat points for ~75% of its value"
    )
    @app_commands.describe(
        stat="stat u wanna refund stat points from (Intelligence/Stealth/Strength)"
    )
    async def refund(interaction: discord.Interaction, stat: str, amount: int):
        from config import STAT_NAMES

        stat = stat.lower()
        if stat not in STAT_NAMES:
            await interaction.response.send_message(
                "Invalid stat name.", ephemeral=True
            )
            return
        if amount < 0:
            await interaction.response.send_message(
                "Amount must be ≥ 0.", ephemeral=True
            )
            return

        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        userstats = get_stats(uid)
        if amount > userstats[stat]:
            await interaction.response.send_message(
                "You dont have enough stat points on this stat.", ephemeral=True
            )
            return
        rest = userstats[stat] - amount
        startMoney = get_money(uid)
        endMoney = startMoney + (amount * 49)
        set_money(uid, endMoney)
        _execute = __import__("db.DBHelper", fromlist=["_execute"])._execute
        _execute(f"UPDATE users SET {stat} = ? WHERE user_id = ?", (rest, uid))
        await interaction.response.send_message(
            f"✅ Removed from {interaction.user.display_name}'s **{stat}** **{amount}** stats points and added **{endMoney}** coins to your balance.",
            ephemeral=True,
        )

    @bot.tree.command(
        name="logmessages",
        description="Log messages for a duration and show top users",
    )
    @app_commands.describe(
        duration="Duration like 10m or 1h",
        top="Number of users to show (default 30)",
    )
    async def logmessages(
        interaction: discord.Interaction, duration: str, top: int = 30
    ):
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        unit = duration[-1].lower()
        try:
            amount = int(duration[:-1])
            seconds = amount * multipliers[unit]
        except (ValueError, KeyError):
            await interaction.response.send_message(
                "Invalid duration format. Use like '10m' or '1h'.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"📝 Logging messages for {amount}{unit}...",
            ephemeral=True,
        )
        counts: Counter[str] = Counter()

        def check(msg: discord.Message) -> bool:
            return msg.guild == interaction.guild and not msg.author.bot

        end_time = asyncio.get_event_loop().time() + seconds
        while True:
            timeout = end_time - asyncio.get_event_loop().time()
            if timeout <= 0:
                break
            try:
                message = await bot.wait_for(
                    "message", timeout=timeout, check=check
                )
            except asyncio.TimeoutError:
                break
            counts[message.author.display_name] += 1

        top_users = counts.most_common(top)
        if not top_users:
            await interaction.followup.send("No messages were recorded.")
            return
        lines = [
            f"{idx + 1}. {name} – {count} messages"
            for idx, (name, count) in enumerate(top_users)
        ]
        embed = discord.Embed(
            title=f"Top {len(top_users)} chatters",
            description="\n".join(lines),
            colour=discord.Colour.blue(),
        )
        await interaction.followup.send(embed=embed)

    return (
        stats_cmd,
        quest,
        buypoints,
        allocate,
        fish,
        buyrod,
        rodshop,
        myrod,
        refund,
        logmessages,
    )
