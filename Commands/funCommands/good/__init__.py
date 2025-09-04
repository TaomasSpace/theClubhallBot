import discord
import requests
from db.DBHelper import get_role
from utils import has_role

async def good(interaction: discord.Interaction, user: discord.Member):
    response = requests.get("https://api.otakugifs.xyz/gif?reaction=pat&format=gif")
    gif = response.json()["url"]
    try:
        sheher_id = get_role(interaction.guild.id, "sheher")
        hehim_id = get_role(interaction.guild.id, "hehim")
        if sheher_id and has_role(user, sheher_id) and not user.name == "goodyb":
            embed = discord.Embed(
                title=f"{interaction.user.display_name} calls {user.display_name} a good girl",
                color=discord.Color.red(),
            )
            embed.set_image(url=gif)
            await interaction.response.send_message(embed=embed)
        elif hehim_id and has_role(user, hehim_id):
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
