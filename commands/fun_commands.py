import discord
from discord import app_commands
from discord.ext import commands
from random import choice, random
from typing import Optional
from collections import defaultdict
import requests

from db.DBHelper import get_role
from utils import has_role

from .hybrid_helpers import respond

lowercase_locked: dict[int, set[int]] = defaultdict(set)


def setup(bot: commands.Bot):
    @bot.hybrid_command(
        name="forcelowercase",
        description="Force a member's messages to lowercase (toggle)",
    )
    @app_commands.describe(member="Member to lock/unlock")
    @commands.has_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def forcelowercase(ctx: commands.Context, member: discord.Member):
        if not ctx.guild:
            await respond(ctx, content="This command can only be used in a server.", ephemeral=True)
            return
        locked = lowercase_locked[ctx.guild.id]
        if member.id in locked:
            locked.remove(member.id)
            await respond(
                ctx,
                content=f"🔓 {member.display_name} unlocked – messages stay unchanged.",
                ephemeral=True,
            )
        else:
            locked.add(member.id)
            await respond(
                ctx,
                content=f"🔒 {member.display_name} locked – messages will be lower-cased.",
                ephemeral=True,
            )

    @bot.hybrid_command(name="punch", description="Punch someone with anime style")
    async def punch(ctx: commands.Context, user: discord.Member):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=punch&format=gif"
        )
        gif = response.json()["url"]
        if user.id == ctx.author.id:
            await respond(
                ctx, content="You can't punch yourself ... or maybe you can?", ephemeral=True
            )
            return
        embed = discord.Embed(
            title=f"{ctx.author.display_name} punches {user.display_name}!",
            color=discord.Colour.red(),
        )
        embed.set_image(url=gif)
        await respond(ctx, embed=embed)

    @bot.hybrid_command(name="stab", description="Stab someone with anime style")
    async def stab(ctx: commands.Context, user: discord.Member):
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
            "https://i.makeagif.com/media/11-18-2022/Ezac_n.gif",
            "https://c.tenor.com/uc9Qh0p1mOIAAAAC/yuno-gasai-mirai-nikki.gif",
        ]
        sender_id = ctx.author.id
        try:
            if user.id == sender_id:
                if random() < 0.30 or user.id == 756537363509018736:
                    selected_gif = choice(special_gifs)
                    embed = discord.Embed(
                        title=f"{ctx.author.display_name} tried to stab themselves... and succeeded?!",
                        color=discord.Color.red(),
                    )
                    embed.set_image(url=selected_gif)
                    await respond(ctx, embed=embed)
                    return
                await respond(ctx, content="You can't stab yourself... or can you?", ephemeral=True)
                return
            if random() < 0.75 or user.id == 756537363509018736:
                gif_url = choice(stab_gifs)
                embed = discord.Embed(
                    title=f"{ctx.author.display_name} stabs {user.display_name}!",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                await respond(ctx, embed=embed)
            else:
                fail_messages = [
                    "Isn't that illegal?",
                    "You don't have a knife.",
                    "You missed completely!",
                ]
                await respond(ctx, content=choice(fail_messages))
        except Exception:
            await respond(
                ctx,
                content="You can't stab someone with higher permission than me.",
                ephemeral=True,
            )

    @bot.hybrid_command(name="goon", description="goon to someone on the server")
    async def goon(ctx: commands.Context, user: discord.Member):
        die_gifs = [
            "https://images-ext-1.discordapp.net/external/NsMNJnl7MWCPxMK2Q-MdPdUApR3VX8-nxpDFhdWl7PI/https/media.tenor.com/wQZWGLcXSgYAAAPo/you-died-link.gif"
        ]
        goon_gifs = [
            "https://images-ext-1.discordapp.net/external/aFNUqz7T07oOHvYQG1_DRBccPglRx_nRzshRGe0NDW8/https/media.tenor.com/LYFIesZUNiEAAAPo/lebron-james-lebron.gif"
        ]
        if user.id == ctx.author.id:
            await respond(ctx, content="You cant goon to yourself", ephemeral=True)
            return
        if random() < 0.95:
            gif_url = choice(goon_gifs)
            embed = discord.Embed(
                title=f"{ctx.author.display_name} goons to {user.display_name}!",
                color=discord.Color.red(),
            )
            embed.set_image(url=gif_url)
            await respond(ctx, embed=embed)
        else:
            gif_url = choice(die_gifs)
            embed = discord.Embed(
                title=f"{ctx.author.display_name} dies because of gooning!",
                color=discord.Color.red(),
            )
            embed.set_image(url=gif_url)
            await respond(ctx, embed=embed)

    @bot.hybrid_command(name="dance", description="hit a cool dance")
    async def dance(ctx: commands.Context):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=dance&format=gif"
        )
        gif = response.json()["url"]
        embed = discord.Embed(
            title=f"{ctx.author.display_name} Dances", color=discord.Color.red()
        )
        embed.set_image(url=gif)
        await respond(ctx, embed=embed)

    @bot.hybrid_command(name="kiss", description="kiss another user")
    async def kiss(ctx: commands.Context, user: discord.Member):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=kiss&format=gif"
        )
        gif = response.json()["url"]
        embed = discord.Embed(
            title=f"{ctx.author.display_name} kisses {user.display_name} ꨄ︎",
            color=discord.Color.red(),
        )
        embed.set_image(url=gif)
        await respond(ctx, embed=embed)

    @bot.hybrid_command(name="blush", description="blush (bcs of another user)")
    async def blush(ctx: commands.Context, user: Optional[discord.Member] = None):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=blush&format=gif"
        )
        gif = response.json()["url"]
        if user is None:
            embed = discord.Embed(
                title=f"{ctx.author.display_name} blushes",
                color=discord.Color.red(),
            )
        else:
            embed = discord.Embed(
                title=f"{ctx.author.display_name} blushes because of {user.display_name} ꨄ",
                color=discord.Color.red(),
            )
        embed.set_image(url=gif)
        await respond(ctx, embed=embed)

    @bot.hybrid_command(name="mad", description="be mad (bcs of another user)")
    async def mad(ctx: commands.Context, user: Optional[discord.Member] = None):
        response = requests.get("https://api.otakugifs.xyz/gif?reaction=mad&format=gif")
        gif = response.json()["url"]
        if user is None:
            title = f"{ctx.author.display_name} is mad"
        else:
            title = f"{ctx.author.display_name} is mad because of {user.display_name}"
        embed = discord.Embed(title=title, color=discord.Color.red())
        embed.set_image(url=gif)
        await respond(ctx, embed=embed)

    @bot.hybrid_command(name="woah", description="woah")
    async def woah(ctx: commands.Context):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=woah&format=gif"
        )
        gif = response.json()["url"]
        embed = discord.Embed(
            title=f"{ctx.author.display_name} says woah!",
            color=discord.Color.red(),
        )
        embed.set_image(url=gif)
        await respond(ctx, embed=embed)

    @bot.hybrid_command(name="airkiss", description="send an airkiss to someone")
    async def airkiss(ctx: commands.Context, user: discord.Member):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=airkiss&format=gif"
        )
        gif = response.json()["url"]
        embed = discord.Embed(
            title=f"{ctx.author.display_name} sends an airkiss to {user.display_name} ꨄ",
            color=discord.Color.red(),
        )
        embed.set_image(url=gif)
        await respond(ctx, embed=embed)

    @bot.hybrid_command(name="yawn", description="yawn")
    async def yawn(ctx: commands.Context):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=yawn&format=gif"
        )
        gif = response.json()["url"]
        embed = discord.Embed(
            title=f"{ctx.author.display_name} yawns!",
            color=discord.Color.red(),
        )
        embed.set_image(url=gif)
        await respond(ctx, embed=embed)

    @bot.hybrid_command(name="tickle", description="tickle another user")
    async def tickle(ctx: commands.Context, user: discord.Member):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=tickle&format=gif"
        )
        gif = response.json()["url"]
        embed = discord.Embed(
            title=f"{ctx.author.display_name} tickles {user.display_name} ",
            color=discord.Color.red(),
        )
        embed.set_image(url=gif)
        await respond(ctx, embed=embed)

    @bot.hybrid_command(name="slap", description="slap another user")
    async def slap(ctx: commands.Context, user: discord.Member):
        try:
            response = requests.get(
                "https://api.otakugifs.xyz/gif?reaction=slap&format=gif",
                timeout=5,
            )
            response.raise_for_status()
            gif = response.json().get("url", "")
        except requests.RequestException:
            gif = ""
        embed = discord.Embed(
            title=f"{ctx.author.display_name} slaps {user.display_name} really hard!",
            color=discord.Color.red(),
        )
        if gif:
            embed.set_image(url=gif)
            await respond(ctx, embed=embed)
        else:
            await respond(
                ctx,
                content="*whiff* Can't fetch a slap gif right now.",
            )

    @bot.hybrid_command(name="lick", description="Lick another member")
    async def lick(ctx: commands.Context, user: discord.Member):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=lick&format=gif"
        )
        gif = response.json()["url"]
        embed = discord.Embed(
            title=f"{ctx.author.display_name} licks {user.display_name} ꨄ︎ how does it taste?",
            color=discord.Color.red(),
        )
        embed.set_image(url=gif)
        await respond(ctx, embed=embed)

    @bot.hybrid_command(name="good", description="Tell someone he/she is a good boy/girl")
    async def good(ctx: commands.Context, user: discord.Member):
        response = requests.get("https://api.otakugifs.xyz/gif?reaction=pat&format=gif")
        gif = response.json()["url"]
        try:
            if not ctx.guild:
                raise RuntimeError
            sheher_id = get_role(ctx.guild.id, "sheher")
            hehim_id = get_role(ctx.guild.id, "hehim")
            if sheher_id and has_role(user, sheher_id) and user.name != "goodyb":
                title = f"{ctx.author.display_name} calls {user.display_name} a good girl"
            elif hehim_id and has_role(user, hehim_id):
                title = f"{ctx.author.display_name} calls {user.display_name} a good boy"
            else:
                title = f"{ctx.author.display_name} calls {user.display_name} a good child"
            embed = discord.Embed(title=title, color=discord.Color.red())
            embed.set_image(url=gif)
            await respond(ctx, embed=embed)
        except Exception:
            await respond(ctx, content="Command didnt work, sry :(", ephemeral=True)

    @bot.hybrid_command(name="getbot", description="Get the bot for your server")
    async def getbot(ctx: commands.Context):
        await respond(
            ctx,
            content=(
                "This is the developer version of the Clubhallbot, so you can't get this bot for your server. "
                "BUT there is an official version you can add: https://discord.com/oauth2/authorize?client_id=1401961800504971316&permissions=8&integration_type=0&scope=bot+applications.commands"
            ),
            ephemeral=True,
        )

    return (
        forcelowercase,
        punch,
        stab,
        goon,
        dance,
        good,
        kiss,
        lick,
        blush,
        woah,
        tickle,
        getbot,
    )
