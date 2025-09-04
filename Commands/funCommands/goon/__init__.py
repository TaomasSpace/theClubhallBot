import discord
from random import choice, random

async def goon(interaction: discord.Interaction, user: discord.Member) -> None:
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
