import discord
from discord.ext import commands
from discord import app_commands, ui
import sqlite3
from datetime import datetime, timedelta, timezone
from discord.app_commands import CommandOnCooldown, Cooldown
from random import random, choice
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

DB_PATH = 'users.db'
OWNER_ROLE_NAME = "Owner"
ADMIN_ROLE_NAME = "Admin"
DEFAULT_MAX_COINS = 1000

TRIGGER_RESPONSES = {
    "シャドウストーム": "Our beautiful majestic Emperor シャドウストーム! Long live our beloved King 👑",
    "goodyb": "Our beautiful majestic Emperor goodyb! Long live our beloved King 👑",
    "shadow": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑",
    "taoma": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑",
    "тaoma": "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑"
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stab_gifs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL
        )
    ''')
    cursor.execute('INSERT OR IGNORE INTO server (id, max_coins) VALUES (1, ?)', (DEFAULT_MAX_COINS,))
    cursor.execute('UPDATE users SET money = 5 WHERE money = 0')
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

def has_role(member: discord.Member, role_name):
    return any(role.name == role_name for role in member.roles)

def get_random_stab_gif():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT url FROM stab_gifs')
    results = cursor.fetchall()
    conn.close()
    if results:
        return choice(results)[0]
    else:
        return None

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
    if message.author.bot:
        return

    content = message.content.lower()
    for trigger, response in TRIGGER_RESPONSES.items():
        if trigger.lower() in content:
            await message.channel.send(response)
            break

    await bot.process_commands(message)  

WELCOME_CHANNEL_ID = 1351487186557734942 

@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name="Member")
    if role:
        await member.add_roles(role)

    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        server_name = member.guild.name
        member_count = member.guild.member_count - 12
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
    register_user(user_id, interaction.user.name)
    money = get_money(user_id)
    await interaction.response.send_message(f"You have {money} clubhall coins.", ephemeral=True)

@bot.tree.command(name="balance", description="Check someone else's clubhall coin balance")
async def balance(interaction: discord.Interaction, user: discord.Member):
    register_user(str(user.id), user.name)
    money = get_money(str(user.id))
    await interaction.response.send_message(f"{user.name} has {money} clubhall coins.")

@bot.tree.command(name="give", description="Give coins to a user (Admin/Owner only)")
async def give(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not has_role(interaction.user, ADMIN_ROLE_NAME) and not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message("You don't have permission to give clubhall coins.", ephemeral=True)
        return

    register_user(str(user.id), user.name)
    total = get_total_money()
    max_limit = get_max_coins()

    if total + amount > max_limit and not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message(f"clubhall coin limit of {max_limit} reached!", ephemeral=True)
        return

    current = get_money(str(user.id))
    set_money(str(user.id), current + amount)
    await interaction.response.send_message(f"{amount} clubhall coins added to {user.name}.")

@bot.tree.command(name="remove", description="Remove clubhall coins from a user (Admin/Owner only)")
async def remove(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not has_role(interaction.user, ADMIN_ROLE_NAME) and not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message("You don't have permission to remove clubhall coins.", ephemeral=True)
        return

    current = get_money(str(user.id))
    set_money(str(user.id), max(0, current - amount))
    await interaction.response.send_message(f"{amount} clubhall coins removed from {user.name}.")

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

    register_user(str(sender_id), interaction.user.name)
    register_user(str(receiver_id), user.name)

    view = RequestView(sender_id, receiver_id, amount)
    await interaction.response.send_message(
        f"{user.mention}, {interaction.user.name} requests **{amount}** clubhall coins for: _{reason}_",
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
        title=f"{interaction.user.name} punches {user.name}!",
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

    sender_id = interaction.user.id
    try:
        if user.id == sender_id:
            chance = 0.20  
            if has_role(interaction.user, OWNER_ROLE_NAME):
                chance = 0.75 

            if random() < chance:
                selected_gif = choice(special_gifs)
                embed = discord.Embed(
                    title=f"{interaction.user.name} tried to stab themselves... and succeeded?!",
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
            gif_url = get_random_stab_gif()
            if gif_url:
                embed = discord.Embed(title=f"{interaction.user.name} stabs {user.name}!", color=discord.Color.red())
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

@bot.tree.command(name="gamble", description="Gamble your coins for a chance to win more!")
async def gamble(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    register_user(user_id, interaction.user.name)

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
            f"{emoji_result[multiplier]} **{interaction.user.name}**, you bet **{amount}** coins.\n"
            f"{message}\n"
            f"You now have **{get_money(user_id)}** clubhall coins."
        )
    )

with open("code.txt", "r") as file:
    TOKEN = file.read().strip()

bot.run(TOKEN)