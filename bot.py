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
        # 1) Slash-Commands registrieren (deine setup-Funktionen)
        setup_fun(self)
        setup_booster(self)
        setup_economy(self)
        setup_stats(self, events.rod_shop)
        setup_action(self)
        setup_admin(self)
        setup_antinuke(self)
        setup_wizard(self)
        setup_explain(self)
        events.setup(self, lowercase_locked)
        anti_nuke.setup(self)

        # 2) Syncen, damit tree.* gefüllt ist
        await self.tree.sync()

        # 3) Slash → Prefix spiegeln
        for ac in self.tree.walk_commands():
            if isinstance(ac, app_commands.Command) and hasattr(ac, "to_command"):
                try:
                    self.add_command(ac.to_command())
                except commands.CommandRegistrationError:
                    # Namens-Kollision o.Ä. -> überspringen oder Alias vergeben
                    pass


bot = MyBot(command_prefix="!", intents=intents)

with open("code.txt", "r") as f:
    TOKEN = f.read().strip()

bot.run(TOKEN)
