import discord
from discord.ext import commands
from discord import app_commands, ui
import sqlite3
import random
from datetime import datetime, timedelta, timezone
from discord.app_commands import CommandOnCooldown, Cooldown

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
    conn.commit()
    conn.close()

def register_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (user_id, username, money) VALUES (?, ?, ?)',
                       (user_id, username, 0))
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
        return random.choice(results)[0]
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
            await interaction.response.send_message("You don't have enough good boy coins to accept this request.", ephemeral=True)
            return

        set_money(str(self.receiver_id), receiver_balance - self.amount)
        set_money(str(self.sender_id), sender_balance + self.amount)
        await interaction.response.edit_message(content=f"✅ Request accepted. {self.amount} good boy coins sent!", view=None)

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
    channel = bot.get_channel(1351475070312255501)
    if channel:
        member_count = member.guild.member_count
        message = f"It seems {member.name} has left us... We are now **{member_count}** members."
        await channel.send(message)


# === SLASH COMMANDS ===
@bot.tree.command(name="money", description="Check your good boy coin balance")
async def money(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    register_user(user_id, interaction.user.name)
    money = get_money(user_id)
    await interaction.response.send_message(f"You have {money} good boy coins.", ephemeral=True)

@bot.tree.command(name="balance", description="Check someone else's good boy coin balance")
async def balance(interaction: discord.Interaction, user: discord.Member):
    register_user(str(user.id), user.name)
    money = get_money(str(user.id))
    await interaction.response.send_message(f"{user.name} has {money} good boy coins.")

@bot.tree.command(name="give", description="Give coins to a user (Admin/Owner only)")
async def give(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not has_role(interaction.user, ADMIN_ROLE_NAME) and not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message("You don't have permission to give good boy coins.", ephemeral=True)
        return

    register_user(str(user.id), user.name)
    total = get_total_money()
    max_limit = get_max_coins()

    if total + amount > max_limit and not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message(f"good boy coin limit of {max_limit} reached!", ephemeral=True)
        return

    current = get_money(str(user.id))
    set_money(str(user.id), current + amount)
    await interaction.response.send_message(f"{amount} good boy coins added to {user.name}.")

@bot.tree.command(name="remove", description="Remove good boy coins from a user (Admin/Owner only)")
async def remove(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not has_role(interaction.user, ADMIN_ROLE_NAME) and not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message("You don't have permission to remove good boy coins.", ephemeral=True)
        return

    current = get_money(str(user.id))
    set_money(str(user.id), max(0, current - amount))
    await interaction.response.send_message(f"{amount} good boy coins removed from {user.name}.")

@bot.tree.command(name="spend", description="Spend your own good boy coins")
async def spend(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    current = get_money(user_id)
    if amount > current:
        await interaction.response.send_message("You don't have enough good boy coins.", ephemeral=True)
        return
    set_money(user_id, current - amount)
    await interaction.response.send_message(f"You spent {amount} good boy coins.")

@bot.tree.command(name="setlimit", description="Set the maximum good boy coins limit (Owner only)")
async def setlimit(interaction: discord.Interaction, new_limit: int):
    if not has_role(interaction.user, OWNER_ROLE_NAME):
        await interaction.response.send_message("Only the owner can change the limit.", ephemeral=True)
        return
    set_max_coins(new_limit)
    await interaction.response.send_message(f"New coin limit set to {new_limit}.")

@bot.tree.command(name="request", description="Request good boy coins from another user")
async def request(interaction: discord.Interaction, user: discord.Member, amount: int, reason: str):
    sender_id = interaction.user.id
    receiver_id = user.id

    if sender_id == receiver_id:
        await interaction.response.send_message("You can't request good boy coins from yourself.", ephemeral=True)
        return

    register_user(str(sender_id), interaction.user.name)
    register_user(str(receiver_id), user.name)

    view = RequestView(sender_id, receiver_id, amount)
    await interaction.response.send_message(
        f"{user.mention}, {interaction.user.name} requests **{amount}** good boy coins for: _{reason}_",
        view=view
    )

cooldown_cache = {}

@bot.tree.command(name="stab", description="Stab someone with anime style")
async def stab(interaction: discord.Interaction, user: discord.Member):
    import random

    if not has_role(interaction.user, OWNER_ROLE_NAME):
        user_id = interaction.user.id
        now = datetime.now().timestamp()
        last_time = cooldown_cache.get(user_id, 0)

        if now - last_time < 120:
            seconds_left = int(120 - (now - last_time))
            await interaction.response.send_message(
                f"You're on cooldown! Try again in {seconds_left} seconds.",
                ephemeral=True
            )
            return
        cooldown_cache[user_id] = now

    special_gif_url = "https://i.pinimg.com/originals/15/dd/94/15dd945571c75b2a0f5141c313fb7dc6.gif"  
    sender_id = interaction.user.id
    try:
        if user.id == sender_id:
            chance = 0.20  
            if has_role(interaction.user, OWNER_ROLE_NAME):
                chance = 0.75 

            if random.random() < chance:
                embed = discord.Embed(title=f"{interaction.user.name} tried to stab themselves... and succeeded?!", color=discord.Color.red())
                embed.set_image(url=special_gif_url)
                if not has_role(user, OWNER_ROLE_NAME) and not has_role(user, "CEO"):
                    await user.timeout(datetime.now(timezone.utc) + timedelta(seconds=40), reason="You succesfully stabbed yourself")
                await interaction.response.send_message(embed=embed)
                return
            else:
                await interaction.response.send_message("You can't stab yourself... or can you?", ephemeral=True)
                return

        chance = 0.40 
        if has_role(interaction.user, OWNER_ROLE_NAME):
            chance = 0.90
        if random.random() < chance:
            gif_url = get_random_stab_gif()
            if gif_url:
                embed = discord.Embed(title=f"{interaction.user.name} stabs {user.name}!", color=discord.Color.red())
                embed.set_image(url=gif_url)
                print(gif_url)
                if not has_role(user, OWNER_ROLE_NAME) and not has_role(user, "CEO"):
                    await user.timeout(datetime.now(timezone.utc) + timedelta(seconds=20), reason="You got stabbed")
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
            await interaction.response.send_message(random.choice(fail_messages))
    except:
        await interaction.response.send_message("you cant stab someone with higher permission than me. (No owners and no CEO's)", ephemeral=True)

with open("code.txt", "r") as file:
    TOKEN = file.read().strip()

bot.run(TOKEN)