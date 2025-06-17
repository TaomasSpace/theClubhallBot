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
            "https://i.imgflip.com/1zx1tj.gif",
        ]
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't punch yourself ... or maybe you can?", ephemeral=True
            )
            return
        if not punch_gifs:
            await interaction.response.send_message(
                "No Punch GIFs stored!", ephemeral=True
            )
            return
        selected_gif = choice(punch_gifs)
        embed = discord.Embed(
            title=f"{interaction.user.display_name} punches {user.display_name}!",
            color=discord.Colour.red(),
        )
        embed.set_image(url=selected_gif)
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
        dance_gifs = [
            "https://i.pinimg.com/originals/97/2d/aa/972daa47f0ce9cd21f79af88195b4c07.gif",
            "https://media.tenor.com/GOYRQva4UeoAAAAM/anime-dance.gif",
            "https://media.tenor.com/4QvbP2MXNjkAAAAM/guts-berserk.gif",
            "https://i.pinimg.com/originals/ce/7a/f8/ce7af890d23444939a9ed0b019dc46c6.gif",
            "https://media0.giphy.com/media/RLJxQtX8Hs7XytaoyX/200w.gif",
            "https://media4.giphy.com/media/lyN5qwcbXWXr2fUjBa/200.gif",
            "https://media2.giphy.com/media/euMGM3uD3NHva/200w.gif",
            "https://media.tenor.com/PKD99ODryUMAAAAM/rinrinne-rinne.gif",
            "https://i.imgur.com/AMA4d7I.gif",
            "https://usagif.com/wp-content/uploads/gify/39-anime-dance-girl-usagif.gif",
            "https://media1.giphy.com/media/11lxCeKo6cHkJy/200.gif",
            "https://gamingforevermore.weebly.com/uploads/2/5/8/9/25893592/6064743_orig.gif",
            "https://media1.giphy.com/media/M8ubTcdyKsJAj5DsLC/200w.gif",
            "https://www.icegif.com/wp-content/uploads/2024/02/icegif-497.gif",
            "https://i.imgur.com/jhFy1dS.gif",
            "https://gifsec.com/wp-content/uploads/2022/10/anime-dance-gif-26.gif",
            "https://i.redd.it/d5jtphmm52931.gif",
            "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/11a8fe33-328d-4dce-8c62-09fbfdfa4467/dh0aiaw-c412949f-3b1f-43f6-9c70-de76a18eaef1.gif?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzExYThmZTMzLTMyOGQtNGRjZS04YzYyLTA5ZmJmZGZhNDQ2N1wvZGgwYWlhdy1jNDEyOTQ5Zi0zYjFmLTQzZjYtOWM3MC1kZTc2YTE4ZWFlZjEuZ2lmIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0.s2bQH9zNTvXzUJMAp2BeuioND_4aq6IUTcrRDidBqvo",
            "https://media.tenor.com/xXdBqOdY_jAAAAAM/nino-nakano.gif",
        ]
        gif_url = choice(dance_gifs)
        embed = discord.Embed(
            title=f"{interaction.user.display_name} Dances", color=discord.Color.red()
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="good", description="Tell someone he/she is a good boy/girl")
    async def good(interaction: discord.Interaction, user: discord.Member):
        sheher_gifs = [
            "https://c.tenor.com/EXlBWDEJhIQAAAAd/tenor.gif",
            "https://c.tenor.com/ENcB_TMNJAYAAAAd/tenor.gif",
            "https://c.tenor.com/6-MIKH3o1BkAAAAd/tenor.gif",
            "https://c.tenor.com/hXlKC_Va6mgAAAAd/tenor.gif",
            "https://c.tenor.com/h4iOZke1ESMAAAAd/tenor.gif",
            "https://c.tenor.com/4MCocODtY4EAAAAd/tenor.gif",
            "https://c.tenor.com/jsOSJ9i3C6YAAAAd/tenor.gif",
        ]
        hehim_gifs = [
            "        https://c.tenor.com/FJApjvQ0aJQAAAAd/tenor.gif",
            "https://c.tenor.com/sIMPVgqJ07QAAAAd/tenor.gif",
            "https://media.discordapp.net/attachments/1241701136227110932/1241711528831356998/caption.gif?ex=680a1dfa&is=6808cc7a&hm=875565279cbad6af5b42c4610c96856f17446e3a95222ad26cbd81a97448ff80&=&width=440&height=848",
            "https://c.tenor.com/ZzTZ9p6dsccAAAAd/tenor.gif",
            "https://c.tenor.com/LZMc6NWsxgUAAAAd/tenor.gif",
            "https://c.tenor.com/UA4AsiQLhZYAAAAd/tenor.gif",
            "https://c.tenor.com/roTBuOK3MeMAAAAd/tenor.gif",
            "https://c.tenor.com/txwU-nHbUiQAAAAd/tenor.gif",
        ]
        undefined_gifs = sheher_gifs + hehim_gifs
        try:
            if has_role(user, SHEHER_ROLE_ID) and not user.name == "goodyb":
                gif_url = choice(sheher_gifs)
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} calls {user.display_name} a good girl",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                await interaction.response.send_message(embed=embed)
            elif has_role(user, HEHIM_ROLE_ID):
                gif_url = choice(hehim_gifs)
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} calls {user.display_name} a good boy",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
                await interaction.response.send_message(embed=embed)
            else:
                gif_url = choice(undefined_gifs)
                embed = discord.Embed(
                    title=f"{interaction.user.display_name} calls {user.display_name} a good child",
                    color=discord.Color.red(),
                )
                embed.set_image(url=gif_url)
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
    )
