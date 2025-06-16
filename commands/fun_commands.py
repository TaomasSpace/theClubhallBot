import discord
from discord import app_commands
from discord.ext import commands
from random import choice, random
from typing import Optional
from config import SHEHER_ROLE_ID, HEHIM_ROLE_ID
from utils import has_role


lowercase_locked: set[int] = set()


def setup(bot: commands.Bot):
    @bot.tree.command(
        name="forcelowercase", description="Force a member's messages to lowercase (toggle)"
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
        punch_gifs = [
            "https://media1.tenor.com/m/BoYBoopIkBcAAAAC/anime-smash.gif",
            "https://media4.giphy.com/media/NuiEoMDbstN0J2KAiH/giphy.gif",
            "https://i.pinimg.com/originals/8a/ab/09/8aab09880ff9226b1c73ee4c2ddec883.gif",
        ]
        if user.id == interaction.user.id:
            await interaction.response.send_message("You can't punch yourself ... or maybe you can?", ephemeral=True)
            return
        if not punch_gifs:
            await interaction.response.send_message("No Punch GIFs stored!", ephemeral=True)
            return
        selected_gif = choice(punch_gifs)
        embed = discord.Embed(title=f"{interaction.user.display_name} punches {user.display_name}!", color=discord.Colour.red())
        embed.set_image(url=selected_gif)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="stab", description="Stab someone with anime style")
    async def stab(interaction: discord.Interaction, user: discord.Member):
        special_gifs = ["https://i.pinimg.com/originals/15/dd/94/15dd945571c75b2a0f5141c313fb7dc6.gif"]
        stab_gifs = ["https://i.gifer.com/EJEW.gif"]
        sender_id = interaction.user.id
        try:
            if user.id == sender_id:
                if random() < 0.20:
                    selected_gif = choice(special_gifs)
                    embed = discord.Embed(title=f"{interaction.user.display_name} tried to stab themselves... and succeeded?!", color=discord.Color.red())
                    embed.set_image(url=selected_gif)
                    await interaction.response.send_message(embed=embed)
                    return
                else:
                    await interaction.response.send_message("You can't stab yourself... or can you?", ephemeral=True)
                    return
            if random() < 0.50:
                gif_url = choice(stab_gifs)
                embed = discord.Embed(title=f"{interaction.user.display_name} stabs {user.display_name}!", color=discord.Color.red())
                embed.set_image(url=gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                fail_messages = ["Isn't that illegal?", "You don't have a knife.", "You missed completely!"]
                await interaction.response.send_message(choice(fail_messages))
        except Exception:
            await interaction.response.send_message("You can't stab someone with higher permission than me.", ephemeral=True)

    @bot.tree.command(name="goon", description="goon to someone on the server")
    async def goon(interaction: discord.Interaction, user: discord.Member):
        die_gifs = ["https://images-ext-1.discordapp.net/external/NsMNJnl7MWCPxMK2Q-MdPdUApR3VX8-nxpDFhdWl7PI/https/media.tenor.com/wQZWGLcXSgYAAAPo/you-died-link.gif"]
        goon_gifs = ["https://images-ext-1.discordapp.net/external/aFNUqz7T07oOHvYQG1_DRBccPglRx_nRzshRGe0NDW8/https/media.tenor.com/LYFIesZUNiEAAAPo/lebron-james-lebron.gif"]
        if user.id == interaction.user.id:
            await interaction.response.send_message("You cant goon to yourself", ephemeral=True)
            return
        if random() < 0.95:
            gif_url = choice(goon_gifs)
            embed = discord.Embed(title=f"{interaction.user.display_name} goons to {user.display_name}!", color=discord.Color.red())
            embed.set_image(url=gif_url)
            await interaction.response.send_message(embed=embed)
        else:
            gif_url = choice(die_gifs)
            embed = discord.Embed(title=f"{interaction.user.display_name} dies because of gooning!", color=discord.Color.red())
            embed.set_image(url=gif_url)
            await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="dance", description="hit a cool dance")
    async def dance(interaction: discord.Interaction):
        dance_gifs = ["https://i.pinimg.com/originals/97/2d/aa/972daa47f0ce9cd21f79af88195b4c07.gif"]
        gif_url = choice(dance_gifs)
        embed = discord.Embed(title=f"{interaction.user.display_name} Dances", color=discord.Color.red())
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="good", description="Tell someone he/she is a good boy/girl")
    async def good(interaction: discord.Interaction, user: discord.Member):
        sheher_gifs = ["https://c.tenor.com/EXlBWDEJhIQAAAAd/tenor.gif"]
        hehim_gifs = ["https://c.tenor.com/FJApjvQ0aJQAAAAd/tenor.gif"]
        undefined_gifs = sheher_gifs + hehim_gifs
        try:
            if has_role(user, SHEHER_ROLE_ID) and not user.name == "goodyb":
                gif_url = choice(sheher_gifs)
                embed = discord.Embed(title=f"{interaction.user.display_name} calls {user.display_name} a good girl", color=discord.Color.red())
                embed.set_image(url=gif_url)
                await interaction.response.send_message(embed=embed)
            elif has_role(user, HEHIM_ROLE_ID):
                gif_url = choice(hehim_gifs)
                embed = discord.Embed(title=f"{interaction.user.display_name} calls {user.display_name} a good boy", color=discord.Color.red())
                embed.set_image(url=gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                gif_url = choice(undefined_gifs)
                embed = discord.Embed(title=f"{interaction.user.display_name} calls {user.display_name} a good child", color=discord.Color.red())
                embed.set_image(url=gif_url)
                await interaction.response.send_message(embed=embed)
        except Exception:
            await interaction.response.send_message("Command didnt work, sry :(", ephemeral=True)

    return (
        forcelowercase,
        punch,
        stab,
        goon,
        dance,
        good,
    )