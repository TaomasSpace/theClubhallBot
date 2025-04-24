import discord
from discord.ext import commands
from discord import app_commands, ui
import sqlite3
from datetime import datetime, timedelta, timezone
from discord.app_commands import CommandOnCooldown, Cooldown
from random import random, choice
import asyncio
import logging

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

DB_PATH = 'users.db'
OWNER_ROLE_NAME = "Owner"
ADMIN_ROLE_NAME = "Admin"
SHEHER_ROLE_NAME = "She/Her"
HEHIM_ROLE_NAME = "He/Him"
DEFAULT_MAX_COINS = 3000
DAILY_REWARD = 10
WELCOME_CHANNEL_ID = 1351487186557734942 
LOG_CHANNEL_ID = 1364226902289813514
lowercase_locked: set[int] = set()          # User‑IDs

TRIGGER_RESPONSES = {
    "シャドウストーム": "Our beautiful majestic Emperor シャドウストーム! Long live our beloved King 👑",
    "goodyb": "Our beautiful majestic Emperor goodyb! Long live our beloved King 👑",
    "shadow": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑",
    "taoma": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑",
    "Taoma": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑",
    " King": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑"
}

# === DATABASE SETUP ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            money INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            max_coins INTEGER
        )
    ''')
    cursor.execute('INSERT OR IGNORE INTO server (id, max_coins) VALUES (1, ?)', (DEFAULT_MAX_COINS,))
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "last_claim" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_claim TEXT")
    conn.commit()
    conn.close()

def get_last_claim(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT last_claim FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row and row[0] else None

def set_last_claim(user_id: str, ts: datetime):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_claim = ? WHERE user_id = ?', (ts.isoformat(), user_id))
    conn.commit()
    conn.close()

def register_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (user_id, username, money) VALUES (?, ?, ?)',
                    (user_id, username, 5))
    conn.commit()
    conn.close()

def get_money(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT money FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def set_money(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET money = ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_total_money():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(money) FROM users')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result[0] else 0

def get_max_coins():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT max_coins FROM server WHERE id = 1')
    result = cursor.fetchone()
    conn.close()
    return result[0]

def set_max_coins(new_limit):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE server SET max_coins = ? WHERE id = 1', (new_limit,))
    conn.commit()
    conn.close()

def get_top_users(limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT username, money FROM users ORDER BY money DESC LIMIT ?',
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def has_role(member: discord.Member, role_name):
    return any(role.name == role_name for role in member.roles)

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
            await interaction.response.send_message("This request isn't for you.", ephemeral=True)
            return

        sender_balance = get_money(str(self.sender_id))
        receiver_balance = get_money(str(self.receiver_id))

        if receiver_balance < self.amount:
            await interaction.response.send_message("You don't have enough clubhall coins to accept this request.", ephemeral=True)
            return

        set_money(str(self.receiver_id), receiver_balance - self.amount)
        set_money(str(self.sender_id), sender_balance + self.amount)
        await interaction.response.edit_message(content=f"✅ Request accepted. {self.amount} clubhall coins sent!", view=None)

    @ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message("This request isn't for you.", ephemeral=True)
            return

        await interaction.response.edit_message(content="❌ Request declined.", view=None)

# === DISCORD EVENTS ===
@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync()
    print(f'Bot is online as {bot.user}')

@bot.event
async def on_message(message):
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
            allowed_mentions=discord.AllowedMentions.all()
        )

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


# === SLASH COMMANDS ===
@bot.tree.command(name="money", description="Check your clubhall coin balance")
async def money(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    register_user(user_id, interaction.user.display_name)
    money = get_money(user_id)
    await interaction.response.send_message(f"You have {money} clubhall coins.", ephemeral=True)

@bot.tree.command(name="balance", description="Check someone else's clubhall coin balance")
async def balance(interaction: discord.Interaction, user: discord.Member):
    register_user(str(user.id), user.display_name)
    money = get_money(str(user.id))
    await interaction.response.send_message(f"{user.display_name} has {money} clubhall coins.")

@bot.tree.command(name="give", description="Give coins to a user (Admin/Owner only)")
async def give(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not has_role(interaction.user, ADMIN_ROLE_NAME) and not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message("You don't have permission to give clubhall coins.", ephemeral=True)
        return

    register_user(str(user.id), user.display_name)
    total = get_total_money()
    max_limit = get_max_coins()

    if total + amount > max_limit and not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message(f"clubhall coin limit of {max_limit} reached!", ephemeral=True)
        return

    current = get_money(str(user.id))
    set_money(str(user.id), current + amount)
    await interaction.response.send_message(f"{amount} clubhall coins added to {user.display_name}.")

@bot.tree.command(name="remove", description="Remove clubhall coins from a user (Admin/Owner only)")
async def remove(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not has_role(interaction.user, ADMIN_ROLE_NAME) and not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message("You don't have permission to remove clubhall coins.", ephemeral=True)
        return

    current = get_money(str(user.id))
    set_money(str(user.id), max(0, current - amount))
    await interaction.response.send_message(f"{amount} clubhall coins removed from {user.display_name}.")

@bot.tree.command(name="spend", description="Spend your own clubhall coins")
async def spend(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    current = get_money(user_id)
    if amount > current:
        await interaction.response.send_message("You don't have enough clubhall coins.", ephemeral=True)
        return
    set_money(user_id, current - amount)
    await interaction.response.send_message(f"You spent {amount} clubhall coins.")

@bot.tree.command(name="setlimit", description="Set the maximum clubhall coins limit (Owner only)")
async def setlimit(interaction: discord.Interaction, new_limit: int):
    if not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message("Only the owner can change the limit.", ephemeral=True)
        return
    set_max_coins(new_limit)
    await interaction.response.send_message(f"New coin limit set to {new_limit}.")

@bot.tree.command(name="request", description="Request clubhall coins from another user")
async def request(interaction: discord.Interaction, user: discord.Member, amount: int, reason: str):
    sender_id = interaction.user.id
    receiver_id = user.id

    if sender_id == receiver_id:
        await interaction.response.send_message("You can't request clubhall coins from yourself.", ephemeral=True)
        return

    register_user(str(sender_id), interaction.user.display_name)
    register_user(str(receiver_id), user.display_name)

    view = RequestView(sender_id, receiver_id, amount)
    await interaction.response.send_message(
        f"{user.mention}, {interaction.user.display_name} requests **{amount}** clubhall coins for: _{reason}_",
        view=view
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
        "https://i.imgflip.com/1zx1tj.gif"
    ]

    if user.id == interaction.user.id:
        await interaction.response.send_message("You can't punch yourself ... or maybe you can?", ephemeral=True)
        return

    if not punch_gifs:
        await interaction.response.send_message("No Punch GIFs stored!", ephemeral=True)
        return

    selected_gif = choice(punch_gifs)
    embed = discord.Embed(
        title=f"{interaction.user.display_name} punches {user.display_name}!",
        color=discord.Colour.red()
    )
    embed.set_image(url=selected_gif)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stab", description="Stab someone with anime style")
async def stab(interaction: discord.Interaction, user: discord.Member):

    special_gifs = [
        "https://i.pinimg.com/originals/15/dd/94/15dd945571c75b2a0f5141c313fb7dc6.gif",
        "https://i.gifer.com/E65z.gif",
        "https://i.makeagif.com/media/12-15-2017/I2zZ0u.gif",
        "https://media.tenor.com/2pCPJqG46awAAAAM/yes-adventure-time.gif"
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
                    color=discord.Color.red()
                )
                embed.set_image(url=selected_gif)
                await interaction.response.send_message(embed=embed)
                return
            else:
                await interaction.response.send_message("You can't stab yourself... or can you?", ephemeral=True)
                return

        chance = 0.50
        if has_role(interaction.user, OWNER_ROLE_NAME):
            chance = 0.90
        if random() < chance:
            gif_url = choice(stab_gifs)
            if gif_url:
                embed = discord.Embed(title=f"{interaction.user.display_name} stabs {user.display_name}!", color=discord.Color.red())
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("No stab GIFs found in the database.", ephemeral=True)
        else:
            fail_messages = [
                "Isn't that illegal?",
                "You don't have a knife.",
                "You missed completely!",
                "They dodged like a ninja!",
                "You changed your mind last second.",
                "Your knife broke!"
            ]
            await interaction.response.send_message(choice(fail_messages))
    except:
        await interaction.response.send_message("You can't stab someone with higher permission than me. (No owners and no CEO's)", ephemeral=True)

@bot.tree.command(name="forcelowercase",
                  description="Force a member's messages to lowercase (toggle)")
@app_commands.describe(member="Member to lock/unlock")
@app_commands.checks.has_permissions(manage_messages=True)
async def forcelowercase(interaction: discord.Interaction,
                         member: discord.Member):

    if member.id in lowercase_locked:
        lowercase_locked.remove(member.id)
        await interaction.response.send_message(
            f"🔓 {member.display_name} unlocked – messages stay unchanged.",
            ephemeral=True
        )
    else:
        lowercase_locked.add(member.id)
        await interaction.response.send_message(
            f"🔒 {member.display_name} locked – messages will be lower‑cased.",
            ephemeral=True
        )

@bot.tree.command(name="gamble", description="Gamble your coins for a chance to win more!")
async def gamble(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    register_user(user_id, interaction.user.display_name)

    if amount < 2:
        await interaction.response.send_message("🎲 Minimum bet is 2 clubhall coins.", ephemeral=True)
        return

    balance = get_money(user_id)
    if amount > balance:
        await interaction.response.send_message("❌ You don't have enough clubhall coins!", ephemeral=True)
        return

    await interaction.response.send_message("🎲 Rolling the dice...", ephemeral=False)
    await asyncio.sleep(2)

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

    emoji_result = {
        3: "💎",
        2: "🔥",
        1: "😐",
        0: "💀"
    }

    await interaction.edit_original_response(
        content=(
            f"{emoji_result[multiplier]} **{interaction.user.display_name}**, you bet **{amount}** coins.\n"
            f"{message}\n"
            f"You now have **{get_money(user_id)}** clubhall coins."
        )
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s: %(message)s"
)

@bot.tree.command(name="imitate", description="Imitate a user's message (Admin/Owner only)")
@app_commands.describe(user="User to imitate", msg="The message to send")
async def imitate(interaction: discord.Interaction, user: discord.Member, msg: str):
    if not has_role(interaction.user, ADMIN_ROLE_NAME) and not has_role(interaction.user, OWNER_ROLE_NAME) and not has_role(interaction.user, "Rae‘s boyfriend") and not has_role(interaction.user, "Marmalades Boyfriend"):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    channel = interaction.channel
    webhook = await get_channel_webhook(channel)

    try:
        await webhook.send(
            content=msg,
            username=user.display_name,
            avatar_url=user.display_avatar.url,
            allowed_mentions=discord.AllowedMentions.none()
        )
        await interaction.response.send_message("✅ Message sent.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to imitate: {e}", ephemeral=True)

@bot.tree.command(name="giveaway", description="Start a giveaway (only Admin/Owner)")
@app_commands.describe(duration="duration in minutes", prize="Prize")
async def giveaway(interaction: discord.Interaction,
                   duration: int,
                   prize: str):

    if (not has_role(interaction.user, ADMIN_ROLE_NAME) and
        not has_role(interaction.user, OWNER_ROLE_NAME)):
        await interaction.response.send_message(
            "Only admins and owners can use this command",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=(
            f"React with 🎉 to win **{prize}**!\n"
            f"🔔 Duration: **{duration} min**."
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(
        text=f"Created by: {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url
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
        f"🎊 Congratulation! {winner.mention}! "
        f"You have won **{prize}** 🎉"
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
                await interaction.response.send_message("You cant goon to yourself", ephemeral=True)

        chance = 0.95
        if random() < chance:
            gif_url = choice(goon_gifs)
            if gif_url:
                embed = discord.Embed(title=f"{interaction.user.display_name} goons to {user.display_name}!", color=discord.Color.red())
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("No goon GIFs found in the database.", ephemeral=False)
        else:
                gif_url = choice(die_gifs)
                if gif_url:
                    embed = discord.Embed(title=f"{interaction.user.display_name} dies because of gooning!", color=discord.Color.red())
                    embed.set_image(url=gif_url)
                    print(gif_url)
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("No die GIFs found in the database.", ephemeral=False)
    except:
        await interaction.response.send_message("Command didnt work, sry :(", ephemeral=True)

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
            embed = discord.Embed(title=f"{interaction.user.display_name} Dances", color=discord.Color.red())
            embed.set_image(url=gif_url)
            print(gif_url)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No Dance GIFs found in the database.", ephemeral=False)
    except:
        await interaction.response.send_message("Command didnt work, sry :(", ephemeral=True)

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
                embed = discord.Embed(title=f"{interaction.user.display_name} calls {user.display_name} a good girl", color=discord.Color.red())
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("No good girl GIFs found in the database.", ephemeral=False)
        elif has_role(user, HEHIM_ROLE_NAME):
            gif_url = choice(hehim_gifs)
            if gif_url:
                embed = discord.Embed(title=f"{interaction.user.display_name} calls {user.display_name} a good boy", color=discord.Color.red())
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("No good boy GIFs found in the database.", ephemeral=False)
        else:
            gif_url = choice(undefined_gifs)
            if gif_url:
                embed = discord.Embed(title=f"{interaction.user.display_name} calls {user.display_name} a good child", color=discord.Color.red())
                embed.set_image(url=gif_url)
                print(gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("No good person GIFs found in the database.", ephemeral=False)

    except:
        await interaction.response.send_message("Command didnt work, sry :(", ephemeral=True)

# === LEADERBOARD ===
@bot.tree.command(name="topcoins", description="Show the richest players")
@app_commands.describe(count="How many spots to display (1–25)?")
async def topcoins(interaction: discord.Interaction, count: int = 10):
    count = max(1, min(count, 25))
    top = get_top_users(count)

    if not top:
        await interaction.response.send_message("No data yet 🤷‍♂️")
        return

    lines = [f"**#{i + 1:02d}**  {name} – **{coins}** 💰" for i, (name, coins) in enumerate(top)]
    embed = discord.Embed(
        title=f"🏆 Top {count} Coin Holders",
        description="\n".join(lines),
        colour=discord.Colour.gold()
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
            f"⏳ You can claim again in **{hours} h {minutes} min**.",
            ephemeral=True
        )
        return

    current = get_money(user_id)
    set_money(user_id, current + DAILY_REWARD)
    set_last_claim(user_id, now)

    await interaction.response.send_message(
        f"✅ {DAILY_REWARD} Coins added! You now have **{current + DAILY_REWARD}** 💰.",
        ephemeral=True
    )

# === GLOBAL ERROR HANDLER ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s: %(message)s")

@bot.tree.error
async def on_app_error(inter: discord.Interaction, error: Exception):
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if log_ch:
        embed = discord.Embed(
            title="Command error",
            colour=discord.Colour.red(),
            timestamp=datetime.utcnow(),
            description=f"```py\n{error}\n```"
        )
        embed.add_field(name="Command", value=inter.command.qualified_name)
        embed.add_field(name="User", value=f"{inter.user} (`{inter.user.id}`)", inline=False)
        embed.add_field(name="Channel", value=f"{inter.channel.mention}", inline=False)
        await log_ch.send(embed=embed)
    if isinstance(error, CommandOnCooldown):
        await inter.response.send_message(
            f"⏱ Cooldown: try again in {error.retry_after:.0f}s.",
            ephemeral=True
        )
        return

    logging.exception("Slash-command error", exc_info=error)

    if inter.response.is_done():
        await inter.followup.send("Oops, something went wrong 😵", ephemeral=True)
    else:
        await inter.response.send_message("Oops, something went wrong 😵", ephemeral=True)

# === LOG COMMANDS ===
@bot.event
async def on_app_command_completion(inter: discord.Interaction,
                                    command: app_commands.Command):
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if not log_ch:
        return

    opts = format_options(inter.data)

    embed = discord.Embed(
        title="Command executed",
        colour=discord.Colour.blue(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Command", value=f"/{command.qualified_name}")
    embed.add_field(name="User", value=f"{inter.user} (`{inter.user.id}`)", inline=False)
    embed.add_field(name="Channel", value=inter.channel.mention, inline=False)
    embed.add_field(name="Options", value=opts, inline=False)

    await log_ch.send(embed=embed)

def format_options(data: dict) -> str:
    """Flattens options (incl. sub‑commands) into 'name=DisplayName (ID)' CSV."""
    result = []

    for opt in data.get("options", []):
        if opt.get("type") == 1:  # Subcommand
            inner = ", ".join(
                _format_option(o)
                for o in opt.get("options", [])
            ) or "–"
            result.append(f"{opt['name']}({inner})")
        else:
            result.append(_format_option(opt))

    return ", ".join(result) or "–"

def _format_option(opt: dict) -> str:
    name = opt["name"]
    value = opt.get("value")

    if opt["type"] == 6:
        user_obj = opt.get("user", None)
        if isinstance(user_obj, dict):
            username = user_obj.get("global_name") or user_obj.get("username", "Unknown")
            return f"{name}={username} ({value})"
    return f"{name}={value}"


# === Message‑Intercept ===
webhook_cache: dict[int, discord.Webhook] = {}

async def get_channel_webhook(channel: discord.TextChannel) -> discord.Webhook:
    wh = webhook_cache.get(channel.id)
    if wh:                       #   <— reicht völlig
        return wh

    webhooks = await channel.webhooks()
    wh = discord.utils.get(webhooks, name="LowercaseRelay")
    if wh is None:
        wh = await channel.create_webhook(name="LowercaseRelay")

    webhook_cache[channel.id] = wh
    return wh

with open("code.txt", "r") as file:
    TOKEN = file.read().strip()

bot.run(TOKEN)