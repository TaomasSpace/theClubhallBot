import discord
from discord import app_commands
from discord.ext import commands
from random import choice, random
from typing import Optional
from config import SHEHER_ROLE_ID, HEHIM_ROLE_ID
from utils import has_role
import requests

lowercase_locked: set[int] = set()


def setup(bot: commands.Bot):
    @bot.tree.command(
        name="forcelowercase",
        description="Force a member's messages to lowercase (toggle)",
    )
    @app_commands.describe(member="Member to lock/unlock")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def forcelowercase(interaction: discord.Interaction, member: discord.Member):
        if member.id in lowercase_locked:
            lowercase_locked.remove(member.id)
            await interaction.response.send_message(
                f"🔓 {member.display_name} unlocked – messages stay unchanged.",
                ephemeral=True,
            )
        else:
            lowercase_locked.add(member.id)
            await interaction.response.send_message(
                f"🔒 {member.display_name} locked – messages will be lower-cased.",
                ephemeral=True,
            )

    @bot.tree.command(name="punch", description="Punch someone with anime style")
    async def punch(interaction: discord.Interaction, user: discord.Member):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=punch&format=gif"
        )

        gif = response.json()
        gif = gif["url"]
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't punch yourself ... or maybe you can?", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"{interaction.user.display_name} punches {user.display_name}!",
            color=discord.Colour.red(),
        )
        embed.set_image(url=gif)
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
            "https://i.makeagif.com/media/11-18-2022/Ezac_n.gif",
            "https://c.tenor.com/uc9Qh0p1mOIAAAAC/yuno-gasai-mirai-nikki.gif",
        ]
        sender_id = interaction.user.id
        try:
            if user.id == sender_id:
                if random() < 0.20:
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
            if random() < 0.50:
                gif_url = choice(stab_gifs)
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} stabs {user.display_name}!",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                fail_messages = [
                    "Isn't that illegal?",
                    "You don't have a knife.",
                    "You missed completely!",
                ]
                await interaction.response.send_message(choice(fail_messages))
        except Exception:
            await interaction.response.send_message(
                "You can't stab someone with higher permission than me.", ephemeral=True
            )

    @bot.tree.command(name="goon", description="goon to someone on the server")
    async def goon(interaction: discord.Interaction, user: discord.Member):
        die_gifs = [
            "https://images-ext-1.discordapp.net/external/NsMNJnl7MWCPxMK2Q-MdPdUApR3VX8-nxpDFhdWl7PI/https/media.tenor.com/wQZWGLcXSgYAAAPo/you-died-link.gif"
        ]
        goon_gifs = [
            "https://images-ext-1.discordapp.net/external/aFNUqz7T07oOHvYQG1_DRBccPglRx_nRzshRGe0NDW8/https/media.tenor.com/LYFIesZUNiEAAAPo/lebron-james-lebron.gif"
        ]
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You cant goon to yourself", ephemeral=True
            )
            return
        if random() < 0.95:
            gif_url = choice(goon_gifs)
            embed = discord.Embed(
                title=f"{interaction.user.display_name} goons to {user.display_name}!",
                color=discord.Color.red(),
            )
            embed.set_image(url=gif_url)
            await interaction.response.send_message(embed=embed)
        else:
            gif_url = choice(die_gifs)
            embed = discord.Embed(
                title=f"{interaction.user.display_name} dies because of gooning!",
                color=discord.Color.red(),
            )
            embed.set_image(url=gif_url)
            await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="dance", description="hit a cool dance")
    async def dance(interaction: discord.Interaction):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=dance&format=gif"
        )

        gif = response.json()
        gif = gif["url"]
        embed = discord.Embed(
            title=f"{interaction.user.display_name} Dances", color=discord.Color.red()
        )
        embed.set_image(url=gif)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="kiss", description="kiss another user")
    async def kiss(interaction: discord.Interaction, user: discord.Member):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=kiss&format=gif"
        )

        gif = response.json()
        gif = gif["url"]
        embed = discord.Embed(
            title=f"{interaction.user.display_name} kisses {user.display_name} ꨄ︎",
            color=discord.Color.red(),
        )
        embed.set_image(url=gif)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="lick", description="Lick another member")
    async def lick(interaction: discord.Interaction, user: discord.Member):
        response = requests.get(
            "https://api.otakugifs.xyz/gif?reaction=lick&format=gif"
        )

        gif = response.json()
        gif = gif["url"]
        embed = discord.Embed(
            title=f"{interaction.user.display_name} licks {user.display_name} ꨄ︎ how does it taste?",
            color=discord.Color.red(),
        )
        embed.set_image(url=gif)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="good", description="Tell someone he/she is a good boy/girl")
    async def good(interaction: discord.Interaction, user: discord.Member):

        response = requests.get("https://api.otakugifs.xyz/gif?reaction=pat&format=gif")

        gif = response.json()
        gif = gif["url"]
        try:
            if has_role(user, SHEHER_ROLE_ID) and not user.name == "goodyb":
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} calls {user.display_name} a good girl",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif)
                await interaction.response.send_message(embed=embed)
            elif has_role(user, HEHIM_ROLE_ID):
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} calls {user.display_name} a good boy",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif)
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} calls {user.display_name} a good child",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif)
                await interaction.response.send_message(embed=embed)
        except Exception:
            await interaction.response.send_message(
                "Command didnt work, sry :(", ephemeral=True
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
    )
