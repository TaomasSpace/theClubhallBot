import discord
from discord import app_commands
from discord.ext import commands

from config import *
from commands.fun_commands import setup as setup_fun, lowercase_locked
from commands.booster_commands import setup as setup_booster
from commands.economy_commands import setup as setup_economy
from commands.stats_commands import setup as setup_stats
from commands.action_commands import setup as setup_action
from commands.admin_commands import setup as setup_admin
from commands.antinuke_commands import setup as setup_antinuke
from commands.setup_wizard import setup as setup_wizard
from commands.explain_commands import setup as setup_explain
import events
import anti_nuke

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True


class MyBot(commands.Bot):
    async def setup_hook(self):
        setup_fun(bot)
        setup_booster(bot)
        setup_economy(bot)
        setup_stats(bot, events.rod_shop)
        setup_action(bot)
        setup_admin(bot)
        setup_antinuke(bot)
        setup_wizard(bot)
        setup_explain(bot)
        events.setup(self, lowercase_locked)
        anti_nuke.setup(self)

        await self.tree.sync()

        failed = []
        mirrored = 0
        print("---- slash commands seen in tree ----")
        for ac in self.tree.walk_commands():
            print("slash:", ac.qualified_name)
            if hasattr(ac, "to_command"):
                try:
                    cmd = ac.to_command()
                    self.add_command(cmd)
                    print("  -> prefix OK:", cmd.qualified_name)
                    mirrored += 1
                except commands.CommandRegistrationError as e:
                    print("  -> prefix FAIL:", ac.qualified_name, "|", e)
                    failed.append((ac.qualified_name, str(e)))
        print(f"mirrored total: {mirrored}, failed: {len(failed)}")


bot = MyBot(command_prefix="!", intents=intents)


@bot.command()
async def ping(ctx):
    await ctx.send("pong")


with open("code.txt", "r") as f:
    TOKEN = f.read().strip()

bot.run(TOKEN)
