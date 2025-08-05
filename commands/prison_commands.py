import discord
from discord import app_commands
from discord.ext import commands
from typing import List

from db.DBHelper import set_prison_settings


class PrisonSetupView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=600)
        self.interaction = interaction
        self.guild = interaction.guild
        self.message: discord.Message | None = None
        self.prison_channel: discord.TextChannel | None = None
        self.prison_role: discord.Role | None = None
        self.immunized_roles: List[discord.Role] = []
        self.allowed_channels: List[discord.TextChannel] = []
        self.prison_exceptions: List[discord.TextChannel] = []

    async def start(self):
        await self.ask_prison_channel(self.interaction)

    async def ask_prison_channel(self, interaction: discord.Interaction):
        self.clear_items()
        channel_select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            placeholder="Select prison channel",
        )

        async def on_select(inter: discord.Interaction):
            self.prison_channel = channel_select.values[0]
            await self.ask_prison_role(inter)

        channel_select.callback = on_select
        self.add_item(channel_select)

        if self.message is None:
            await interaction.response.send_message(
                "Choose the channel to be used as the prison.",
                view=self,
                ephemeral=True,
            )
            self.message = await interaction.original_response()
        else:
            await interaction.response.edit_message(
                content="Choose the channel to be used as the prison.", view=self
            )

    async def ask_prison_role(self, interaction: discord.Interaction):
        self.clear_items()
        role_select = discord.ui.RoleSelect(
            placeholder="Select prison role (optional)",
            min_values=0,
            max_values=1,
        )
        auto_button = discord.ui.Button(
            label="Automatic", style=discord.ButtonStyle.primary
        )

        async def role_selected(inter: discord.Interaction):
            if role_select.values:
                self.prison_role = role_select.values[0]
                await self.ask_immunized_roles(inter)

        async def auto_selected(inter: discord.Interaction):
            self.prison_role = await self.guild.create_role(name="Prison role")
            await self.ask_immunized_roles(inter)

        role_select.callback = role_selected
        auto_button.callback = auto_selected

        self.add_item(role_select)
        self.add_item(auto_button)
        await interaction.response.edit_message(
            content="Select the role for prisoners or create one automatically.",
            view=self,
        )

    async def ask_immunized_roles(self, interaction: discord.Interaction):
        self.clear_items()
        role_select = discord.ui.RoleSelect(
            placeholder="Select roles immune to prison",
            min_values=0,
            max_values=25,
        )
        next_button = discord.ui.Button(
            label="Next", style=discord.ButtonStyle.primary
        )

        async def next_step(inter: discord.Interaction):
            self.immunized_roles = role_select.values
            await self.ask_normal_channels(inter)

        next_button.callback = next_step
        self.add_item(role_select)
        self.add_item(next_button)
        await interaction.response.edit_message(
            content="Select roles that cannot be imprisoned (optional).",
            view=self,
        )

    async def ask_normal_channels(self, interaction: discord.Interaction):
        self.clear_items()
        channel_select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=25,
            placeholder="Channels where normal users can chat",
        )
        next_button = discord.ui.Button(
            label="Next", style=discord.ButtonStyle.primary
        )

        async def next_step(inter: discord.Interaction):
            self.allowed_channels = channel_select.values
            await self.ask_prison_exceptions(inter)

        next_button.callback = next_step
        self.add_item(channel_select)
        self.add_item(next_button)
        await interaction.response.edit_message(
            content="Select normal communication channels.", view=self
        )

    async def ask_prison_exceptions(self, interaction: discord.Interaction):
        self.clear_items()
        channel_select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=25,
            placeholder="Extra channels prisoners may access",
        )
        skip_button = discord.ui.Button(
            label="Skip", style=discord.ButtonStyle.secondary
        )
        finish_button = discord.ui.Button(
            label="Finish", style=discord.ButtonStyle.primary
        )

        async def finish(inter: discord.Interaction):
            self.prison_exceptions = channel_select.values
            await self.finalize(inter)

        async def skip(inter: discord.Interaction):
            await self.finalize(inter)

        finish_button.callback = finish
        skip_button.callback = skip
        self.add_item(channel_select)
        self.add_item(skip_button)
        self.add_item(finish_button)
        await interaction.response.edit_message(
            content="Select additional channels for prisoners (optional).",
            view=self,
        )

    async def finalize(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Save settings
        set_prison_settings(
            self.guild.id,
            self.prison_channel.id if self.prison_channel else 0,
            self.prison_role.id if self.prison_role else 0,
            [r.id for r in self.immunized_roles],
            [c.id for c in self.allowed_channels],
            [c.id for c in self.prison_exceptions],
        )

        # Configure normal channels
        for ch in self.allowed_channels:
            try:
                await ch.set_permissions(self.guild.default_role, send_messages=False)
                if self.prison_role:
                    await ch.set_permissions(self.prison_role, send_messages=True)
                for role in self.immunized_roles:
                    await ch.set_permissions(role, send_messages=True)
            except Exception:
                pass

        # Configure prison channel
        if self.prison_channel and self.prison_role:
            try:
                await self.prison_channel.set_permissions(
                    self.guild.default_role, send_messages=True
                )
                await self.prison_channel.set_permissions(
                    self.prison_role, send_messages=False
                )
            except Exception:
                pass

        for ch in self.prison_exceptions:
            try:
                await ch.set_permissions(self.guild.default_role, send_messages=True)
            except Exception:
                pass

        # Assign prison role to all members
        if self.prison_role:
            for member in self.guild.members:
                if self.prison_role not in member.roles:
                    try:
                        await member.add_roles(self.prison_role)
                    except Exception:
                        pass

        await self.message.edit(content="Prison setup complete.", view=None)


def setup(bot: commands.Bot):
    @bot.tree.command(name="setupprison", description="Setup the prison system")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_prison(interaction: discord.Interaction):
        view = PrisonSetupView(interaction)
        await view.start()
