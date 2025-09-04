import discord
from random import choice, random

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
            if random() < 0.30 or user.id == 756537363509018736:
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
        if random() < 0.75 or user.id == 756537363509018736:
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
