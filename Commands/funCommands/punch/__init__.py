import discord
import requests

async def punch(interaction: discord.Interaction, user: discord.Member):
    response = requests.get("https://api.otakugifs.xyz/gif?reaction=punch&format=gif")
    gif = response.json()["url"]
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
