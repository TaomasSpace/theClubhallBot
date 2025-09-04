import discord
import requests

async def dance(interaction: discord.Interaction) -> None:
    response = requests.get("https://api.otakugifs.xyz/gif?reaction=dance&format=gif")
    gif = response.json()["url"]
    embed = discord.Embed(
        title=f"{interaction.user.display_name} Dances",
        color=discord.Color.red(),
    )
    embed.set_image(url=gif)
    await interaction.response.send_message(embed=embed)
