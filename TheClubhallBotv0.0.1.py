import discord
from discord.ext import commands
from discord import app_commands, ui
import sqlite3
from datetime import datetime, timedelta
from discord.app_commands import CommandOnCooldown
from random import random, choice, randint
import asyncio
import logging

# === INTENTS & BOT ===
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === CONSTANTS ===
DB_PATH = "users.db"
OWNER_ROLE_NAME = "Owner"
ADMIN_ROLE_NAME = "Admin"
SHEHER_ROLE_NAME = "She/Her"
HEHIM_ROLE_NAME = "He/Him"
DEFAULT_MAX_COINS = 3000
DAILY_REWARD = 20
WELCOME_CHANNEL_ID = 1351487186557734942
LOG_CHANNEL_ID = 1364226902289813514
STAT_PRICE = 66
QUEST_COOLDOWN_HOURS = 3
FISHING_COOLDOWN_MINUTES = 30
WEEKLY_REWARD = 50
STAT_NAMES = ["intelligence", "strength", "stealth"]
rod_shop = {}
ROLE_THRESHOLDS = {
    "intelligence": ("Neuromancer", 50),
    "strength": ("Juggernaut", 50),
    "strength": ("Warriour", 100),
    "stealth": ("Shadow", 50),
    "stealth": ("Ninja", 100),
}
hack_cooldowns = {}
fight_cooldowns = {}
steal_cooldowns = {}

lowercase_locked: set[int] = set()

# === TRIGGERS ===
TRIGGER_RESPONSES = {
    "シャドウストーム": "Our beautiful majestic Emperor シャドウストーム! Long live our beloved King 👑",
    "goodyb": "Our beautiful majestic Emperor goodyb! Long live our beloved King 👑",
    "shadow": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑",
    "taoma": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑",
    "Taoma": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑",
    " King": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑",
}

# =====================================================================
#                              DATABASE
# =====================================================================


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            money INTEGER DEFAULT 0,
            last_claim TEXT,
            last_quest TEXT,
            stat_points INTEGER DEFAULT 0,
            intelligence INTEGER DEFAULT 1,
            strength INTEGER DEFAULT 1,
            stealth INTEGER DEFAULT 1
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS server (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            max_coins INTEGER
        )
    """
    )
    cursor.execute(
        "INSERT OR IGNORE INTO server (id, max_coins) VALUES (1, ?)",
        (DEFAULT_MAX_COINS,),
    )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS shop_roles (
        role_id     TEXT PRIMARY KEY,
        price       INTEGER NOT NULL
    )
    """
    )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS fishing_rods (
        user_id TEXT PRIMARY KEY,
        rod_level INTEGER DEFAULT 0
    )
    """
    )

    cursor.execute("PRAGMA table_info(users)")
    existing = {col[1] for col in cursor.fetchall()}
    for col, default in [
        ("last_quest", ""),
        ("last_fishing", ""),
        ("stat_points", 0),
        ("last_weekly", ""),
        ("intelligence", 1),
        ("strength", 1),
        ("stealth", 1),
    ]:
        if col not in existing:
            if col in ("last_quest", "last_weekly", "last_fishing"):
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
            else:
                cursor.execute(
                    f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT {default}"
                )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
#                        GENERIC DB HELPERS
# ---------------------------------------------------------------------


def _fetchone(query: str, params=()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return row


def _execute(query: str, params=()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()


# ---------- user registration ----------


def register_user(user_id: str, username: str):
    if not _fetchone("SELECT 1 FROM users WHERE user_id = ?", (user_id,)):
        _execute(
            "INSERT INTO users (user_id, username, money) VALUES (?,?,?)",
            (user_id, username, 5),
        )


# ---------- coins ----------


def get_money(user_id: str) -> int:
    row = _fetchone("SELECT money FROM users WHERE user_id = ?", (user_id,))
    return row[0] if row else 0


def set_money(user_id: str, amount: int):
    _execute("UPDATE users SET money = ? WHERE user_id = ?", (amount, user_id))


def safe_add_coins(user_id: str, amount: int) -> int:
    if amount <= 0:
        return 0

    current_total = get_total_money()
    max_total = get_max_coins()
    free_space = max_total - current_total

    if free_space <= 0:
        return 0

    addable = min(amount, free_space)
    old_balance = get_money(user_id)
    set_money(user_id, old_balance + addable)
    return addable


def get_total_money():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(money) FROM users")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result[0] else 0


def get_top_users(limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, money FROM users ORDER BY money DESC LIMIT ?", (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_last_claim(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT last_claim FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row and row[0] else None


def set_last_claim(user_id: str, ts: datetime):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_claim = ? WHERE user_id = ?", (ts.isoformat(), user_id)
    )
    conn.commit()
    conn.close()


# ---------- stats & stat‑points ----------


def get_stats(user_id: str):
    row = _fetchone(
        "SELECT intelligence, strength, stealth, stat_points FROM users WHERE user_id = ?",
        (user_id,),
    )
    if not row:
        return {s: 1 for s in STAT_NAMES} | {"stat_points": 0}
    return dict(zip(STAT_NAMES + ["stat_points"], row))


def add_stat_points(user_id: str, delta: int):
    _execute(
        "UPDATE users SET stat_points = stat_points + ? WHERE user_id = ?",
        (delta, user_id),
    )


def increase_stat(user_id: str, stat: str, amount: int):
    if stat not in STAT_NAMES:
        raise ValueError("invalid stat")
    _execute(
        f"UPDATE users SET {stat} = {stat} + ?, stat_points = stat_points - ? WHERE user_id = ?",
        (amount, amount, user_id),
    )


def get_rod_level(user_id: str) -> int:
    row = _fetchone("SELECT rod_level FROM fishing_rods WHERE user_id = ?", (user_id,))
    return row[0] if row else 0


def set_rod_level(user_id: str, level: int):
    if _fetchone("SELECT 1 FROM fishing_rods WHERE user_id = ?", (user_id,)):
        _execute(
            "UPDATE fishing_rods SET rod_level = ? WHERE user_id = ?", (level, user_id)
        )
    else:
        _execute(
            "INSERT INTO fishing_rods (user_id, rod_level) VALUES (?, ?)",
            (user_id, level),
        )


# ---------- timing helpers ----------


def get_timestamp(user_id: str, column: str):
    row = _fetchone(f"SELECT {column} FROM users WHERE user_id = ?", (user_id,))
    return datetime.fromisoformat(row[0]) if row and row[0] else None


def set_timestamp(user_id: str, column: str, ts: datetime):
    _execute(
        f"UPDATE users SET {column} = ? WHERE user_id = ?", (ts.isoformat(), user_id)
    )


def get_last_weekly(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT last_weekly FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row and row[0] else None


def set_last_weekly(user_id: str, ts: datetime):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_weekly = ? WHERE user_id = ?", (ts.isoformat(), user_id)
    )
    conn.commit()
    conn.close()


# ---------- server helpers ----------


def get_max_coins():
    return _fetchone("SELECT max_coins FROM server WHERE id = 1")[0]


def set_max_coins(limit: int):
    _execute("UPDATE server SET max_coins = ? WHERE id = 1", (limit,))


# ---------- shop helpers ----------
def add_shop_role(role_id: int, price: int):
    _execute(
        "INSERT OR REPLACE INTO shop_roles (role_id, price) VALUES (?,?)",
        (role_id, price),
    )


def remove_shop_role(role_id: int):
    _execute("DELETE FROM shop_roles WHERE role_id = ?", (role_id,))


def get_shop_roles():
    rows = _fetchone("SELECT role_id, price FROM shop_roles")  # liefert 1 Row
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role_id, price FROM shop_roles")
    rows = cursor.fetchall()
    conn.close()
    return rows


# =====================================================================
#                              UTILITIES
# =====================================================================


def has_role(member: discord.Member, role_name: str):
    return any(role.name == role_name for role in member.roles)


# ---------- webhook cache (unchanged) ----------
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


# === REQUEST BUTTON VIEW ===
class RequestView(ui.View):
    def __init__(self, sender_id, receiver_id, amount):
        super().__init__(timeout=60)
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount

    @ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message(
                "This request isn't for you.", ephemeral=True
            )
            return

        sender_balance = get_money(str(self.sender_id))
        receiver_balance = get_money(str(self.receiver_id))

        if receiver_balance < self.amount:
            await interaction.response.send_message(
                "You don't have enough clubhall coins to accept this request.",
                ephemeral=True,
            )
            return

        set_money(str(self.receiver_id), receiver_balance - self.amount)
        set_money(str(self.sender_id), sender_balance + self.amount)
        await interaction.response.edit_message(
            content=f"✅ Request accepted. {self.amount} clubhall coins sent!",
            view=None,
        )

    @ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message(
                "This request isn't for you.", ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="❌ Request declined.", view=None
        )


async def sync_stat_roles(member: discord.Member):
    stats = get_stats(str(member.id))
    for stat, (role_name, threshold) in ROLE_THRESHOLDS.items():
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role is None:
            continue

        has_role = role in member.roles
        meets_req = stats[stat] >= threshold

        if meets_req and not has_role:
            await member.add_roles(role, reason=f"{stat} {stats[stat]} ≥ {threshold}")
        elif not meets_req and has_role:
            await member.remove_roles(
                role, reason=f"{stat} {stats[stat]} < {threshold}"
            )


# =====================================================================
#                              EVENTS
# =====================================================================
@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync()
    print(f"Bot is online as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.webhook_id:
        return

    # force lowercase feature (unchanged)
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

    # Trigger‑responses
    content = message.content.lower()
    for trigger, reply in TRIGGER_RESPONSES.items():
        if trigger.lower() in content:
            await message.channel.send(reply)
            break

    await bot.process_commands(message)


@bot.event
async def on_member_join(member):
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


@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(1361778101176107311)
    if channel:
        member_count = member.guild.member_count
        message = f"It seems {member.name} has left us... We are now **{member_count}** members."
        await channel.send(message)


# =====================================================================
#                              SLASH COMMANDS – COINS (original)
# =====================================================================
@bot.tree.command(name="money", description="Check your clubhall coin balance")
async def money(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    register_user(user_id, interaction.user.display_name)
    await interaction.response.send_message(
        f"You have {get_money(user_id)} clubhall coins.", ephemeral=True
    )


@bot.tree.command(
    name="balance", description="Check someone else's clubhall coin balance"
)
async def balance(interaction: discord.Interaction, user: discord.Member):
    register_user(str(user.id), user.display_name)
    money = get_money(str(user.id))
    await interaction.response.send_message(
        f"{user.display_name} has {money} clubhall coins."
    )


@bot.tree.command(name="give", description="Give coins to a user (Admin/Owner only)")
async def give(interaction: discord.Interaction, user: discord.Member, amount: int):
    if (
        interaction.user.name == "alphawolf_001"
        or interaction.user.name == "Alpha-Wolf_01"
        and not has_role(interaction.user, ADMIN_ROLE_NAME)
        and not has_role(interaction.user, OWNER_ROLE_NAME)
    ):
        await interaction.response.send_message(
            "You don't have permission to give clubhall coins.", ephemeral=True
        )
        return

    register_user(str(user.id), user.display_name)
    added = safe_add_coins(str(user.id), amount)
    if added == 0:
        await interaction.response.send_message(
            f"Clubhall coin limit reached. No coins added.", ephemeral=True
        )
    elif added < amount:
        await interaction.response.send_message(
            f"Partial success: Only {added} coins added due to server limit.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            f"{added} clubhall coins added to {user.display_name}."
        )


@bot.tree.command(
    name="remove", description="Remove clubhall coins from a user (Admin/Owner only)"
)
async def remove(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not has_role(interaction.user, ADMIN_ROLE_NAME) and not has_role(
        interaction.user, OWNER_ROLE_NAME
    ):
        await interaction.response.send_message(
            "You don't have permission to remove clubhall coins.", ephemeral=True
        )
        return

    current = get_money(str(user.id))
    set_money(str(user.id), max(0, current - amount))
    await interaction.response.send_message(
        f"{amount} clubhall coins removed from {user.display_name}."
    )


@bot.tree.command(name="spend", description="Spend your own clubhall coins")
async def spend(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    current = get_money(user_id)
    if amount > current:
        await interaction.response.send_message(
            "You don't have enough clubhall coins.", ephemeral=True
        )
        return
    set_money(user_id, current - amount)
    await interaction.response.send_message(f"You spent {amount} clubhall coins.")


@bot.tree.command(
    name="setlimit", description="Set the maximum clubhall coins limit (Owner only)"
)
async def setlimit(interaction: discord.Interaction, new_limit: int):
    if not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message(
            "Only the owner can change the limit.", ephemeral=True
        )
        return
    set_max_coins(new_limit)
    await interaction.response.send_message(f"New coin limit set to {new_limit}.")


@bot.tree.command(
    name="request", description="Request clubhall coins from another user"
)
async def request(
    interaction: discord.Interaction, user: discord.Member, amount: int, reason: str
):
    sender_id = interaction.user.id
    receiver_id = user.id

    if sender_id == receiver_id:
        await interaction.response.send_message(
            "You can't request clubhall coins from yourself.", ephemeral=True
        )
        return

    register_user(str(sender_id), interaction.user.display_name)
    register_user(str(receiver_id), user.display_name)

    view = RequestView(sender_id, receiver_id, amount)
    await interaction.response.send_message(
        f"{user.mention}, {interaction.user.display_name} requests **{amount}** clubhall coins for: _{reason}_",
        view=view,
    )


cooldown_cache = {}


@bot.tree.command(name="punch", description="Punch someone with anime style")
async def punch(interaction: discord.Interaction, user: discord.Member):
    punch_gifs = [
        "https://media1.tenor.com/m/BoYBoopIkBcAAAAC/anime-smash.gif",
        "https://media4.giphy.com/media/NuiEoMDbstN0J2KAiH/giphy.gif",
        "https://i.pinimg.com/originals/8a/ab/09/8aab09880ff9226b1c73ee4c2ddec883.gif",
        "https://i.pinimg.com/originals/8d/50/60/8d50607e59db86b5afcc21304194ba57.gif",
        "https://i.imgur.com/g91XPGA.gif",
        "https://i.makeagif.com/media/3-16-2021/CKcOa2.gif",
        "https://i.pinimg.com/originals/a5/2e/ba/a52eba768035cb7ae66f15f3c66bb184.gif",
        "https://i.gifer.com/BKZ9.gif",
        "https://i.imgur.com/47ctNlt.gif",
        "https://gifdb.com/images/high/anime-punch-shiki-granbell-radiant-oxj18jt2n2c6vvky.gif",
        "https://i.pinimg.com/originals/48/d5/59/48d55975d1c4ec1aa74f4646962bb815.gif",
        "https://i.gifer.com/9eUJ.gif",
        "https://giffiles.alphacoders.com/131/13126.gif",
        "https://media.tenor.com/0ssFlowQEUQAAAAM/naru-punch.gif",
        "https://media0.giphy.com/media/arbHBoiUWUgmc/giphy.gif",
        "https://i.pinimg.com/originals/17/5c/f2/175cf269b6df62b75a5d25a0ed45e954.gif",
        "https://i.imgur.com/GsMjksq.gif",
        "https://media.tenor.com/VuF2NpuuLJsAAAAM/kanon-anime.gif",
        "https://i2.kym-cdn.com/photos/images/original/000/989/495/3b8.gif",
        "https://i.gifer.com/1Ky5.gif",
        "https://i.pinimg.com/originals/86/c3/ce/86c3ce1869454a96b138fe66992fa3b7.gif",
        "https://i.imgur.com/q6qjskO.gif",
        "https://racco.neocities.org/Saved%20Pictures/4ff4ab319bfb9a43bb8b526ef4fb222c.gif",
        "https://i.makeagif.com/media/4-14-2015/5JqC6M.gif",
        "https://static.wikia.nocookie.net/fzero-facts/images/d/d0/Falcon_Punch_%28anime_version%29.gif",
        "https://gifdb.com/images/high/anime-punch-meliodas-seven-clovers-f4bn40bmcsmy98qw.gif",
        "https://media.tenor.com/wTzNeEgfPicAAAAM/anime-punch.gif",
        "https://64.media.tumblr.com/7e30bb1047071490ac65828b96ef71a8/tumblr_nhgcpaDTOj1snbyiqo1_500.gif",
        "https://gifdb.com/images/high/anime-fight-funny-punch-s4n15b8fw49plyhd.gif",
        "https://i.pinimg.com/originals/b2/b1/16/b2b116143040bc3bb2e1e89a87de0f5f.gif",
        "https://gifdb.com/images/high/anime-saki-saki-powerful-punch-xzs7ab1am1a8e80o.gif",
        "https://media.tenor.com/yA_KtmPI1EMAAAAM/hxh-hunter-x-hunter.gif",
        "https://media.tenor.com/images/7a582f32ef2ed527c0f113f81a696ae3/tenor.gif",
        "https://i.imgur.com/qWpGotd.gif",
        "https://media4.giphy.com/media/2t9s7k3IlI6bcOdPj1/giphy.gif",
        "https://gifdb.com/images/high/yoruichi-bleach-anime-punch-ground-explode-destroy-city-h51x0wsb4rb7qmpz.gif",
        "https://i.pinimg.com/originals/d7/c3/0e/d7c30e46a937aaade4d7bc20eb09339b.gif",
        "https://upgifs.com//img/gifs/2C12FgA3jVbby.gif",
        "https://gifdb.com/images/high/anime-punch-damian-desmond-gun4qnn5009sa1ne.gif",
        "https://giffiles.alphacoders.com/200/200628.gif",
        "https://i.imgflip.com/1zx1tj.gif",
    ]

    if user.id == interaction.user.id:
        await interaction.response.send_message(
            "You can't punch yourself ... or maybe you can?", ephemeral=True
        )
        return

    if not punch_gifs:
        await interaction.response.send_message("No Punch GIFs stored!", ephemeral=True)
        return

    selected_gif = choice(punch_gifs)
    embed = discord.Embed(
        title=f"{interaction.user.display_name} punches {user.display_name}!",
        color=discord.Colour.red(),
    )
    embed.set_image(url=selected_gif)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="stab", description="Stab someone with anime style")
async def stab(interaction: discord.Interaction, user: discord.Member):

    special_gifs = [
        "https://i.pinimg.com/originals/15/dd/94/15dd945571c75b2a0f5141c313fb7dc6.gif",
        "https://i.gifer.com/E65z.gif",
        "https://i.makeagif.com/media/12-15-2017/I2zZ0u.gif",
        "https://media.tenor.com/2pCPJqG46awAAAAM/yes-adventure-time.gif",
    ]

    stab_gifs = [
        "https://i.gifer.com/EJEW.gif",
        "https://i.makeagif.com/media/9-04-2024/cpYT-t.gif",
        "https://64.media.tumblr.com/7e2453da9674bcb5b18a2b60795dfa07/6ffe034dc5a009bc-9b/s540x810/8eac80d1085f4d86de5c884ab107e79c6f16fc8c.gif",
        "https://i.pinimg.com/originals/94/c6/37/94c6374c19b627b3a9101f4f9c0585f7.gif",
        "https://i.gifer.com/IlQa.gif",
        "https://i.pinimg.com/originals/dc/ac/b2/dcacb261a7ed5b4f368134795017b12f.gif",
        "https://64.media.tumblr.com/tumblr_m7df09awmi1qbvovho1_500.gif",
        "https://i.imgur.com/S0TeWYF.gif",
        "https://i.makeagif.com/media/11-05-2023/mFVJ4J.gif",
        "https://pa1.aminoapps.com/6253/6fce33471439acfba14932815cc111d617d1ccc4_hq.gif",
        "https://64.media.tumblr.com/71996944f95f102c6bedc0191d8935d3/16b46dc7e02ca5dd-6d/s500x750/bbaee60ca59a9b5baea445b6440bd77e6f93f9c3.gif",
        "https://giffiles.alphacoders.com/732/73287.gif",
        "https://gifdb.com/images/high/haruhi-ryoko-asakura-stabbing-kyon-wv9iij0gq6khu6px.gif",
        "https://gifdb.com/images/high/kill-sekai-saionji-school-days-stabbing-anime-br2876uawee0jzus.gif",
        "https://gifdb.com/images/high/black-butler-stab-7n1xy2127wzi18sk.gif",
        "https://i.gyazo.com/1fdb81ac3ebfb2dee9af9b4127760b70.gif",
        "https://pa1.aminoapps.com/5765/b867c3725e281743e173dc86340c76733281d07f_hq.gif",
        "https://64.media.tumblr.com/003a4f007486f7963f29edcc454425d4/4ff62cb12f9f72e0-51/s540x810/3cb10ed0bdd781a9b5b0864e833f448ece0efed2.gif",
        "https://i.gifer.com/GeUx.gif",
        "https://i.makeagif.com/media/7-19-2018/NFSY1t.gif",
        "https://i.makeagif.com/media/4-17-2015/ba-nRJ.gif",
        "https://i.makeagif.com/media/11-12-2023/a3YlZs.gif",
        "https://i.redd.it/rq7v0ky0q9wb1.gif",
        "https://i.imgur.com/HifpF82.gif",
        "https://images.squarespace-cdn.com/content/v1/5b23e822f79392038cbd486c/1561132763571-XTIOP1FRN1OJRWSGZ9F1/tumblr_o5lpjy37HN1v7kio1o1_500.gif",
        "https://i.makeagif.com/media/11-18-2022/Ezac_n.gif",
        "https://c.tenor.com/uc9Qh0p1mOIAAAAC/yuno-gasai-mirai-nikki.gif",
    ]

    sender_id = interaction.user.id
    try:
        if user.id == sender_id:
            chance = 0.20
            if has_role(interaction.user, OWNER_ROLE_NAME):
                chance = 0.75

            if random() < chance:
                selected_gif = choice(special_gifs)
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} tried to stab themselves... and succeeded?!",
                    color=discord.Color.red(),
                )
                embed.set_image(url=selected_gif)
                await interaction.response.send_message(embed=embed)
                return
            else:
                await interaction.response.send_message(
                    "You can't stab yourself... or can you?", ephemeral=True
                )
                return

        chance = 0.50
        if has_role(interaction.user, OWNER_ROLE_NAME):
            chance = 0.90
        if random() < chance:
            gif_url = choice(stab_gifs)
            if gif_url:
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} stabs {user.display_name}!",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "No stab GIFs found in the database.", ephemeral=True
                )
        else:
            fail_messages = [
                "Isn't that illegal?",
                "You don't have a knife.",
                "You missed completely!",
                "They dodged like a ninja!",
                "You changed your mind last second.",
                "Your knife broke!",
            ]
            await interaction.response.send_message(choice(fail_messages))
    except:
        await interaction.response.send_message(
            "You can't stab someone with higher permission than me. (No owners and no CEO's)",
            ephemeral=True,
        )


# =====================================================================
#                              SLASH COMMANDS – STATS
# =====================================================================


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
    name="quest", description="Complete a short quest to earn stat‑points (3 h CD)"
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
            f"🕒 Next quest in {hrs} h {mins} min.", ephemeral=True
        )
        return

    earned = randint(1, 3)
    add_stat_points(uid, earned)
    set_timestamp(uid, "last_quest", now)
    await interaction.response.send_message(
        f"🏅 You completed the quest and earned **{earned}** stat‑point(s)!",
        ephemeral=True,
    )


@bot.tree.command(name="buypoints", description="Buy stat‑points with coins")
async def buypoints(interaction: discord.Interaction, amount: int = 1):
    if amount < 1:
        await interaction.response.send_message(
            "Specify a positive amount.", ephemeral=True
        )
        return
    uid = str(interaction.user.id)
    register_user(uid, interaction.user.display_name)

    price_per_point = int(STAT_PRICE)
    cost = price_per_point * amount
    balance = get_money(uid)
    if balance < cost:
        await interaction.response.send_message(
            f"❌ You need {cost} coins but only have {balance}.", ephemeral=True
        )
        return
    set_money(uid, balance - cost)
    add_stat_points(uid, amount)
    await interaction.response.send_message(
        f"✅ Purchased {amount} point(s) for {cost} coins."
    )


@bot.tree.command(name="allocate", description="Spend stat‑points to increase a stat")
@app_commands.describe(
    stat="Which stat? (intelligence/strength/stealth)",
    points="How many points to allocate",
)
async def allocate(interaction: discord.Interaction, stat: str, points: int):
    stat = stat.lower()
    if stat not in STAT_NAMES:
        await interaction.response.send_message("Invalid stat name.", ephemeral=True)
        return
    if points < 1:
        await interaction.response.send_message("Points must be > 0.", ephemeral=True)
        return

    uid = str(interaction.user.id)
    register_user(uid, interaction.user.display_name)
    user_stats = get_stats(uid)
    if user_stats["stat_points"] < points:
        await interaction.response.send_message(
            "Not enough unspent points.", ephemeral=True
        )
        return

    increase_stat(uid, stat, points)
    await sync_stat_roles(interaction.user)
    await interaction.response.send_message(f"🔧 {stat.title()} increased by {points}.")


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
    multiplier = 1 + 0.25 * rod_level
    reward = random()
    if (
        interaction.user.name == "alphawolf_001"
        or interaction.user.name == "Alpha-Wolf_01"
    ):
        earned = 10
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


@bot.tree.command(
    name="addrod", description="Add a fishing rod to the shop (Admin/Owner only)"
)
@app_commands.describe(
    level="Rod identifier (must be a unique positive number)",
    price="Price in coins",
    multiplier="Reward multiplier (e.g. 1.25)",
)
async def addrod(
    interaction: discord.Interaction, level: int, price: int, multiplier: float
):
    if not (
        has_role(interaction.user, OWNER_ROLE_NAME)
        or has_role(interaction.user, ADMIN_ROLE_NAME)
    ):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    rod_shop[level] = (price, multiplier)
    await interaction.response.send_message(
        f"🎣 Rod {level} added: {price} coins, {multiplier}× reward.", ephemeral=True
    )


@bot.tree.command(name="rodshop", description="Show available fishing rods")
async def rodshop(inter: discord.Interaction):
    if not rod_shop:
        await inter.response.send_message("🛒 The rod shop is empty.", ephemeral=True)
        return
    lines = [
        f"🎣 Rod {lvl}: **{price}** coins – {mult:.2f}× rewards"
        for lvl, (price, mult) in sorted(rod_shop.items())
    ]
    embed = discord.Embed(
        title="🎣 Rod Shop", description="\n".join(lines), color=discord.Color.teal()
    )
    await inter.response.send_message(embed=embed)


# =====================================================================
#                              STEAL COMMAND
# =====================================================================
@bot.tree.command(
    name="steal",
    description="Attempt to steal coins from another user (needs stealth ≥ 3)",
)
async def steal(interaction: discord.Interaction, target: discord.Member):
    if target.id == interaction.user.id:
        await interaction.response.send_message(
            "You can't steal from yourself!", ephemeral=True
        )
        return
    uid, tid = str(interaction.user.id), str(target.id)
    now = datetime.utcnow()
    cooldown = steal_cooldowns.get(uid)
    if cooldown and now - cooldown < timedelta(minutes=45):
        remaining = timedelta(minutes=45) - (now - cooldown)
        minutes, seconds = divmod(int(remaining.total_seconds()), 60)
        await interaction.response.send_message(
            f"⏳ You can steal again in **{minutes} minutes {seconds} seconds**.",
            ephemeral=True,
        )
        return
    register_user(uid, interaction.user.display_name)
    register_user(tid, target.display_name)
    actor_stats = get_stats(uid)
    target_stats = get_stats(tid)
    if actor_stats["stealth"] < 3:
        await interaction.response.send_message(
            "You need at least **3** Stealth to attempt a steal.", ephemeral=True
        )
        return
    actor_stealth, target_stealth = actor_stats["stealth"], target_stats["stealth"]
    success_chance = actor_stealth / (actor_stealth + target_stealth)
    if random() > success_chance:
        await interaction.response.send_message(
            "👀 You were caught and failed to steal any coins!", ephemeral=True
        )
        return
    target_balance = get_money(tid)
    if target_balance < 5:
        await interaction.response.send_message(
            "Target is too poor to bother...", ephemeral=True
        )
        return
    max_pct = min(0.05 + 0.02 * max(actor_stealth - target_stealth, 0), 0.25)
    stolen_pct = random() * max_pct
    stolen_amt = max(1, int(target_balance * stolen_pct))
    set_money(tid, target_balance - stolen_amt)
    safe_add_coins(uid, stolen_amt)
    steal_cooldowns[uid] = datetime.utcnow()
    await interaction.response.send_message(
        f"🕶️ Success! You stole **{stolen_amt}** coins from {target.display_name}.",
        ephemeral=True,
    )


# ==============================================================
#                          HACK COMMAND
#   – nutzt Intelligence vs. Intelligence
# ==============================================================


@bot.tree.command(
    name="hack", description="Hack the bank to win coins (needs intelligence ≥ 3)"
)
async def hack(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    register_user(uid, interaction.user.display_name)

    now = datetime.utcnow()
    cooldown = hack_cooldowns.get(uid)
    if cooldown and now - cooldown < timedelta(minutes=45):
        remaining = timedelta(minutes=45) - (now - cooldown)
        minutes, seconds = divmod(int(remaining.total_seconds()), 60)
        await interaction.response.send_message(
            f"⏳ You can hack again in **{minutes} minutes {seconds} seconds**.",
            ephemeral=True,
        )
        return

    stats = get_stats(uid)
    if stats["intelligence"] < 3:
        await interaction.response.send_message(
            "❌ You need at least **3** Intelligence to attempt a hack.", ephemeral=True
        )
        return

    int_level = stats["intelligence"]
    success = random() < min(0.20 + 0.05 * (int_level - 3), 0.80)

    hack_cooldowns[uid] = now
    if (
        interaction.user.name == "alphawolf_001"
        or interaction.user.name == "Alpha-Wolf_01"
    ):
        success = random() < min(0.20 + 0.05 * (int_level - 3), 0.80) * 0.5

    if not success:
        loss = randint(1, 5) * int_level
        new_bal = max(0, get_money(uid) - loss)
        set_money(uid, new_bal)
        await interaction.response.send_message(
            f"💻 Hack failed! Security traced you and you lost **{loss}** coins.",
            ephemeral=True,
        )
        return

    reward = randint(5, 12) * int_level
    added = safe_add_coins(uid, reward)

    if added > 0:
        await interaction.response.send_message(
            f"🔋 Hack successful! You siphoned **{added}** coins from the bank.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "⚠️ Hack succeeded but server coin limit reached. No coins added.",
            ephemeral=True,
        )


# ==============================================================
#                        FIGHT / MUG COMMAND
#   – nutzt Strength vs. Strength (Ziel-User)
# ==============================================================


@bot.tree.command(
    name="fight", description="Fight someone for coins (needs strength ≥ 3)"
)
async def fight(interaction: discord.Interaction, target: discord.Member):
    if target.id == interaction.user.id:
        await interaction.response.send_message(
            "You can't fight yourself!", ephemeral=True
        )
        return
    uid, tid = str(interaction.user.id), str(target.id)
    now = datetime.utcnow()
    cooldown = fight_cooldowns.get(uid)
    if cooldown and now - cooldown < timedelta(minutes=45):
        remaining = timedelta(minutes=45) - (now - cooldown)
        minutes, seconds = divmod(int(remaining.total_seconds()), 60)
        await interaction.response.send_message(
            f"⏳ You can fight again in **{minutes} minutes {seconds} seconds**.",
            ephemeral=True,
        )
        return
    register_user(uid, interaction.user.display_name)
    register_user(tid, target.display_name)
    atk = get_stats(uid)
    defn = get_stats(tid)
    if atk["strength"] < 3:
        await interaction.response.send_message(
            "You need at least **3** Strength to start a fight.", ephemeral=True
        )
        return
    atk_str, def_str = atk["strength"], defn["strength"]
    win_chance = atk_str / (atk_str + def_str)
    if random() > win_chance:
        penalty = max(1, int(get_money(uid) * 0.10))
        set_money(uid, get_money(uid) - penalty)
        safe_add_coins(tid, penalty)
        await interaction.response.send_message(
            f"🏋️ You lost the fight and paid **{penalty}** coins in damages to {target.display_name}.",
            ephemeral=True,
        )
        return
    target_coins = get_money(tid)
    steal_pct = random() * min(0.05 + 0.03 * max(atk_str - def_str, 0), 0.20)
    stolen = max(1, int(target_coins * steal_pct))
    set_money(tid, target_coins - stolen)
    safe_add_coins(uid, stolen)
    fight_cooldowns[uid] = datetime.utcnow()
    await interaction.response.send_message(
        f"💪 Victory! You took **{stolen}** coins from {target.display_name}.",
        ephemeral=True,
    )


# =====================================================================
#                     DAILY & OTHER ORIGINAL COMMANDS
# =====================================================================
@bot.tree.command(
    name="setstatpoints", description="Set a user's stat points (Owner only)"
)
@app_commands.describe(user="Target user", amount="New amount of stat points")
async def setstatpoints(
    interaction: discord.Interaction, user: discord.Member, amount: int
):
    if not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message(
            "Only the Owner can use this command.", ephemeral=True
        )
        return

    if amount < 0:
        await interaction.response.send_message("Amount must be ≥ 0.", ephemeral=True)
        return

    uid = str(user.id)
    register_user(uid, user.display_name)
    _execute("UPDATE users SET stat_points = ? WHERE user_id = ?", (amount, uid))
    await interaction.response.send_message(
        f"✅ Set {user.display_name}'s stat points to {amount}.", ephemeral=True
    )


@bot.tree.command(name="setstat", description="Set a user's stat (Owner only)")
@app_commands.describe(
    user="Target user",
    stat="Which stat to set (intelligence, strength, stealth)",
    amount="New stat value (≥ 0)",
)
async def setstat(
    interaction: discord.Interaction, user: discord.Member, stat: str, amount: int
):
    if not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message(
            "Only the Owner can use this command.", ephemeral=True
        )
        return

    stat = stat.lower()
    if stat not in STAT_NAMES:
        await interaction.response.send_message("Invalid stat name.", ephemeral=True)
        return

    if amount < 0:
        await interaction.response.send_message("Amount must be ≥ 0.", ephemeral=True)
        return

    uid = str(user.id)
    register_user(uid, user.display_name)
    _execute(f"UPDATE users SET {stat} = ? WHERE user_id = ?", (amount, uid))
    await interaction.response.send_message(
        f"✅ Set {user.display_name}'s **{stat}** to **{amount}**.", ephemeral=True
    )


@bot.tree.command(
    name="weekly", description="Claim your weekly clubhall coins (7d cooldown)"
)
async def weekly(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    register_user(user_id, interaction.user.display_name)

    now = datetime.utcnow()
    last = get_last_weekly(user_id)

    if last and now - last < timedelta(days=7):
        remaining = timedelta(days=7) - (now - last)
        days, seconds = divmod(int(remaining.total_seconds()), 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes = seconds // 60
        await interaction.response.send_message(
            f"⏳ You can claim again in **{days} days {hours} hours {minutes} minutes**.",
            ephemeral=True,
        )
        return

    added = safe_add_coins(user_id, WEEKLY_REWARD)
    set_last_weekly(user_id, now)

    if added > 0:
        await interaction.response.send_message(
            f"✅ {added} Coins added! You now have **{get_money(user_id)}** 💰.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "⚠️ Server coin limit reached. No weekly coins could be added.",
            ephemeral=True,
        )


@bot.tree.command(
    name="forcelowercase", description="Force a member's messages to lowercase (toggle)"
)
@app_commands.describe(member="Member to lock/unlock")
@app_commands.checks.has_permissions(manage_messages=True)
async def forcelowercase(interaction: discord.Interaction, member: discord.Member):

    if member.id in lowercase_locked:
        lowercase_locked.remove(member.id)
        await interaction.response.send_message(
            f"🔓 {member.display_name} unlocked – messages stay unchanged.",
            ephemeral=True,
        )
    else:
        lowercase_locked.add(member.id)
        await interaction.response.send_message(
            f"🔒 {member.display_name} locked – messages will be lower‑cased.",
            ephemeral=True,
        )


@bot.tree.command(
    name="gamble", description="Gamble your coins for a chance to win more!"
)
async def gamble(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    register_user(user_id, interaction.user.display_name)

    if amount < 2:
        await interaction.response.send_message(
            "🎲 Minimum bet is 2 clubhall coins.", ephemeral=True
        )
        return

    balance = get_money(user_id)
    if amount > balance:
        await interaction.response.send_message(
            "❌ You don't have enough clubhall coins!", ephemeral=True
        )
        return

    await interaction.response.send_message("🎲 Rolling the dice...", ephemeral=False)
    await asyncio.sleep(2)

    roll = random()
    if (
        interaction.user.name == "alphawolf_001"
        or interaction.user.name == "Alpha-Wolf_01"
    ):
        while roll < 0.28:
            roll = random()

    if roll < 0.05:
        multiplier = 3
        message = "💎 JACKPOT! 3x WIN!"
    elif roll < 0.30:
        multiplier = 2
        message = "🔥 Double win!"
    elif roll < 0.60:
        multiplier = 1
        message = "😐 You broke even."
    else:
        multiplier = 0
        message = "💀 You lost everything..."

    new_amount = amount * multiplier
    set_money(user_id, balance - amount + new_amount)

    emoji_result = {3: "💎", 2: "🔥", 1: "😐", 0: "💀"}

    await interaction.edit_original_response(
        content=(
            f"{emoji_result[multiplier]} **{interaction.user.display_name}**, you bet **{amount}** coins.\n"
            f"{message}\n"
            f"You now have **{get_money(user_id)}** clubhall coins."
        )
    )


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s: %(message)s"
)


@bot.tree.command(
    name="imitate", description="Imitate a user's message (Admin/Owner only)"
)
@app_commands.describe(user="User to imitate", msg="The message to send")
async def imitate(interaction: discord.Interaction, user: discord.Member, msg: str):
    if (
        not has_role(interaction.user, ADMIN_ROLE_NAME)
        and not has_role(interaction.user, OWNER_ROLE_NAME)
        and not has_role(interaction.user, "Rae‘s boyfriend")
        and not has_role(interaction.user, "Marmalades Boyfriend")
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
        await interaction.response.send_message("✅ Message sent.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Failed to imitate: {e}", ephemeral=True
        )


@bot.tree.command(name="giveaway", description="Start a giveaway (only Admin/Owner)")
@app_commands.describe(duration="duration in minutes", prize="Prize")
async def giveaway(interaction: discord.Interaction, duration: int, prize: str):

    if not has_role(interaction.user, ADMIN_ROLE_NAME) and not has_role(
        interaction.user, OWNER_ROLE_NAME
    ):
        await interaction.response.send_message(
            "Only admins and owners can use this command", ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=(
            f"React with 🎉 to win **{prize}**!\n" f"🔔 Duration: **{duration} min**."
        ),
        color=discord.Color.gold(),
    )
    embed.set_footer(
        text=f"Created by: {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url,
    )

    await interaction.response.send_message(embed=embed)
    giveaway_msg = await interaction.original_response()
    await giveaway_msg.add_reaction("🎉")

    await asyncio.sleep(duration * 60)

    refreshed = await giveaway_msg.channel.fetch_message(giveaway_msg.id)

    reaction = discord.utils.get(refreshed.reactions, emoji="🎉")
    if reaction is None:
        await refreshed.reply("No one has participated.")
        return

    users = [u async for u in reaction.users() if not u.bot]
    if not users:
        await refreshed.reply("No one has participated.")
        return

    winner = choice(users)
    await refreshed.reply(
        f"🎊 Congratulation! {winner.mention}! " f"You have won **{prize}** 🎉"
    )


@bot.tree.command(name="goon", description="goon to someone on the server")
async def goon(interaction: discord.Interaction, user: discord.Member):

    die_gifs = [
        "https://images-ext-1.discordapp.net/external/NsMNJnl7MWCPxMK2Q-MdPdUApR3VX8-nxpDFhdWl7PI/https/media.tenor.com/wQZWGLcXSgYAAAPo/you-died-link.gif",
    ]

    goon_gifs = [
        "https://images-ext-1.discordapp.net/external/aFNUqz7T07oOHvYQG1_DRBccPglRx_nRzshRGe0NDW8/https/media.tenor.com/LYFIesZUNiEAAAPo/lebron-james-lebron.gif",
    ]

    sender_id = interaction.user.id
    try:
        if user.id == sender_id:
            await interaction.response.send_message(
                "You cant goon to yourself", ephemeral=True
            )

        chance = 0.95
        if random() < chance:
            gif_url = choice(goon_gifs)
            if gif_url:
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} goons to {user.display_name}!",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "No goon GIFs found in the database.", ephemeral=False
                )
        else:
            gif_url = choice(die_gifs)
            if gif_url:
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} dies because of gooning!",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "No die GIFs found in the database.", ephemeral=False
                )
    except:
        await interaction.response.send_message(
            "Command didnt work, sry :(", ephemeral=True
        )


@bot.tree.command(name="dance", description="hit a cool dance")
async def dance(interaction: discord.Interaction):

    dance_gifs = [
        "https://i.pinimg.com/originals/97/2d/aa/972daa47f0ce9cd21f79af88195b4c07.gif",
        "https://media.tenor.com/GOYRQva4UeoAAAAM/anime-dance.gif",
        "https://media.tenor.com/4QvbP2MXNjkAAAAM/guts-berserk.gif",
        "https://i.pinimg.com/originals/ce/7a/f8/ce7af890d23444939a9ed0b019dc46c6.gif",
        "https://media0.giphy.com/media/RLJxQtX8Hs7XytaoyX/200w.gif",
        "https://media4.giphy.com/media/lyN5qwcbXWXr2fUjBa/200.gif",
        "https://media2.giphy.com/media/euMGM3uD3NHva/200w.gif",
        "https://media.tenor.com/PKD99ODryUMAAAAM/rinrinne-rinne.gif",
        "https://i.imgur.com/AMA4d7I.gif",
        "https://usagif.com/wp-content/uploads/gify/39-anime-dance-girl-usagif.gif",
        "https://media1.giphy.com/media/11lxCeKo6cHkJy/200.gif",
        "https://gamingforevermore.weebly.com/uploads/2/5/8/9/25893592/6064743_orig.gif",
        "https://media1.giphy.com/media/M8ubTcdyKsJAj5DsLC/200w.gif",
        "https://www.icegif.com/wp-content/uploads/2024/02/icegif-497.gif",
        "https://i.imgur.com/jhFy1dS.gif",
        "https://gifsec.com/wp-content/uploads/2022/10/anime-dance-gif-26.gif",
        "https://i.redd.it/d5jtphmm52931.gif",
        "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/11a8fe33-328d-4dce-8c62-09fbfdfa4467/dh0aiaw-c412949f-3b1f-43f6-9c70-de76a18eaef1.gif?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzExYThmZTMzLTMyOGQtNGRjZS04YzYyLTA5ZmJmZGZhNDQ2N1wvZGgwYWlhdy1jNDEyOTQ5Zi0zYjFmLTQzZjYtOWM3MC1kZTc2YTE4ZWFlZjEuZ2lmIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0.s2bQH9zNTvXzUJMAp2BeuioND_4aq6IUTcrRDidBqvo",
        "https://media.tenor.com/xXdBqOdY_jAAAAAM/nino-nakano.gif",
    ]

    try:
        gif_url = choice(dance_gifs)
        if gif_url:
            embed = discord.Embed(
                title=f"{interaction.user.display_name} Dances",
                color=discord.Color.red(),
            )
            embed.set_image(url=gif_url)
            print(gif_url)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                "No Dance GIFs found in the database.", ephemeral=False
            )
    except:
        await interaction.response.send_message(
            "Command didnt work, sry :(", ephemeral=True
        )


@bot.tree.command(name="good", description="Tell someone he/she is a good boy/girl")
async def good(interaction: discord.Interaction, user: discord.Member):
    sheher_gifs = [
        "https://c.tenor.com/EXlBWDEJhIQAAAAd/tenor.gif",
        "https://c.tenor.com/ENcB_TMNJAYAAAAd/tenor.gif",
        "https://c.tenor.com/6-MIKH3o1BkAAAAd/tenor.gif",
        "https://c.tenor.com/hXlKC_Va6mgAAAAd/tenor.gif",
        "https://c.tenor.com/h4iOZke1ESMAAAAd/tenor.gif",
        "https://c.tenor.com/4MCocODtY4EAAAAd/tenor.gif",
        "https://c.tenor.com/jsOSJ9i3C6YAAAAd/tenor.gif",
    ]
    hehim_gifs = [
        "https://c.tenor.com/FJApjvQ0aJQAAAAd/tenor.gif",
        "https://c.tenor.com/sIMPVgqJ07QAAAAd/tenor.gif",
        "https://media.discordapp.net/attachments/1241701136227110932/1241711528831356998/caption.gif?ex=680a1dfa&is=6808cc7a&hm=875565279cbad6af5b42c4610c96856f17446e3a95222ad26cbd81a97448ff80&=&width=440&height=848",
        "https://c.tenor.com/ZzTZ9p6dsccAAAAd/tenor.gif",
        "https://c.tenor.com/LZMc6NWsxgUAAAAd/tenor.gif",
        "https://c.tenor.com/UA4AsiQLhZYAAAAd/tenor.gif",
        "https://c.tenor.com/roTBuOK3MeMAAAAd/tenor.gif",
        "https://c.tenor.com/txwU-nHbUiQAAAAd/tenor.gif",
    ]
    undefined_gifs = sheher_gifs + hehim_gifs
    try:
        if has_role(user, SHEHER_ROLE_NAME):
            gif_url = choice(sheher_gifs)
            if gif_url:
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} calls {user.display_name} a good girl",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "No good girl GIFs found in the database.", ephemeral=False
                )
        elif has_role(user, HEHIM_ROLE_NAME):
            gif_url = choice(hehim_gifs)
            if gif_url:
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} calls {user.display_name} a good boy",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "No good boy GIFs found in the database.", ephemeral=False
                )
        else:
            gif_url = choice(undefined_gifs)
            if gif_url:
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} calls {user.display_name} a good child",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "No good person GIFs found in the database.", ephemeral=False
                )

    except:
        await interaction.response.send_message(
            "Command didnt work, sry :(", ephemeral=True
        )


# === LEADERBOARD ===
@bot.tree.command(name="topcoins", description="Show the richest players")
@app_commands.describe(count="How many spots to display (1–25)?")
async def topcoins(interaction: discord.Interaction, count: int = 10):
    count = max(1, min(count, 25))
    top = get_top_users(count)

    if not top:
        await interaction.response.send_message("No data yet 🤷‍♂️")
        return

    lines = [
        f"**#{i + 1:02d}**  {name} – **{coins}** 💰"
        for i, (name, coins) in enumerate(top)
    ]
    embed = discord.Embed(
        title=f"🏆 Top {count} Coin Holders",
        description="\n".join(lines),
        colour=discord.Colour.gold(),
    )
    await interaction.response.send_message(embed=embed)


# === DAILY REWARD ===
@bot.tree.command(name="daily", description="Claim your daily coins (24 h cooldown)")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    register_user(user_id, interaction.user.display_name)

    now = datetime.utcnow()
    last = get_last_claim(user_id)

    if last and now - last < timedelta(hours=24):
        remaining = timedelta(hours=24) - (now - last)
        hours, seconds = divmod(int(remaining.total_seconds()), 3600)
        minutes = seconds // 60
        await interaction.response.send_message(
            f"⏳ You can claim again in **{hours} h {minutes} min**.", ephemeral=True
        )
        return

    added = safe_add_coins(user_id, DAILY_REWARD)
    set_last_claim(user_id, now)

    if added > 0:
        await interaction.response.send_message(
            f"✅ {added} Coins added! You now have **{get_money(user_id)}** 💰.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "⚠️ Server coin limit reached. No daily coins could be added.",
            ephemeral=True,
        )


# =====================================================================
#                     Shop COMMANDS
# =====================================================================


@bot.tree.command(
    name="addshoprole", description="Create/register a purchasable role (Owner/Admin)"
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
    if not (
        has_role(inter.user, OWNER_ROLE_NAME) or has_role(inter.user, ADMIN_ROLE_NAME)
    ):
        await inter.response.send_message("No permission.", ephemeral=True)
        return

    try:
        colour_obj = discord.Colour(int(color.lstrip("#"), 16))
    except ValueError:
        await inter.response.send_message("⚠️  Invalid hex colour.", ephemeral=True)
        return

    guild = inter.guild
    role = discord.utils.get(guild.roles, name=name)
    if role is None:
        role = await guild.create_role(name=name, colour=colour_obj, reason="Shop role")

    if reference:
        new_pos = reference.position + (1 if above else 0)
        try:
            await role.edit(position=new_pos)
        except discord.Forbidden:
            await inter.response.send_message(
                "❌ Bot kann die Rolle nicht verschieben. "
                "Achte darauf, dass seine höchste Rolle über dem Ziel steht.",
                ephemeral=True,
            )
            return

    add_shop_role(role.id, price)

    await inter.response.send_message(
        f"✅ Rolle **{role.name}** registriert (Preis {price} Coins).", ephemeral=True
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
    embed = discord.Embed(title="🛒 Role Shop", description="\n".join(lines))
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
        await inter.response.send_message("❌ Not enough coins.", ephemeral=True)
        return

    set_money(uid, balance - price)
    await inter.user.add_roles(role, reason="Shop purchase")
    await inter.response.send_message(
        f"🎉 Congratulation! You bought **{role.name}** for {price} clubhall coins."
    )


# === GLOBAL ERROR HANDLER ===
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s: %(message)s"
)


@bot.tree.error
async def on_app_error(inter: discord.Interaction, error: Exception):
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if log_ch:
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
        await inter.response.send_message(
            "Oops, something went wrong 😵", ephemeral=True
        )


# === LOG COMMANDS ===
@bot.event
async def on_app_command_completion(
    inter: discord.Interaction, command: app_commands.Command
):
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
    embed.add_field(
        name="User", value=f"{inter.user} (`{inter.user.id}`)", inline=False
    )
    embed.add_field(name="Channel", value=inter.channel.mention, inline=False)
    embed.add_field(name="Options", value=opts, inline=False)

    await log_ch.send(embed=embed)


def format_options(data: dict, interaction: discord.Interaction) -> str:
    result = []

    resolved = data.get("resolved", {})
    users_data = resolved.get("users", {}) if resolved else {}

    for opt in data.get("options", []):
        if opt.get("type") == 1:  # Subcommand
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


# === TOKEN ===
with open("code.txt", "r") as file:
    TOKEN = file.read().strip()

bot.run(TOKEN)
