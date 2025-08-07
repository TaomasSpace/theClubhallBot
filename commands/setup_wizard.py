import re
from dataclasses import dataclass
from typing import Callable, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from db.DBHelper import (
    set_welcome_channel,
    set_welcome_message,
    set_leave_channel,
    set_leave_message,
    set_booster_channel,
    set_booster_message,
    set_log_channel,
    set_anti_nuke_log_channel,

    add_filtered_word,
    add_trigger_response,
    set_anti_nuke_setting,
    add_safe_user,
    add_safe_role,
)
from utils import parse_duration
from anti_nuke import CATEGORIES


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _parse_id(value: str) -> Optional[int]:
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _parse_channel(guild: discord.Guild, value: str) -> Optional[discord.TextChannel]:
    cid = _parse_id(value)
    return guild.get_channel(cid) if cid else None


def _parse_role(guild: discord.Guild, value: str) -> Optional[discord.Role]:
    rid = _parse_id(value)
    return guild.get_role(rid) if rid else None


def _parse_member(guild: discord.Guild, value: str) -> Optional[discord.Member]:
    uid = _parse_id(value)
    return guild.get_member(uid) if uid else None


# ---------------------------------------------------------------------------
# Modal implementations for each step
# ---------------------------------------------------------------------------


class WelcomeModal(discord.ui.Modal, title="Welcome system"):
    channel = discord.ui.TextInput(
        label="Welcome channel", required=False, placeholder="#channel or ID"
    )
    message = discord.ui.TextInput(
        label="Welcome message",
        style=discord.TextStyle.long,
        required=False,
        placeholder="Use {member} for mention",
    )

    def __init__(self, wizard: "SetupWizard"):
        super().__init__()
        self.wizard = wizard

    async def on_submit(self, interaction: discord.Interaction):
        channel = _parse_channel(interaction.guild, self.channel.value)
        if channel:
            set_welcome_channel(interaction.guild.id, channel.id)
        if self.message.value:
            set_welcome_message(interaction.guild.id, self.message.value)
        await interaction.response.send_message(
            "Welcome settings saved.", ephemeral=True
        )
        await self.wizard.advance(interaction)


class LeaveModal(discord.ui.Modal, title="Leave system"):
    channel = discord.ui.TextInput(
        label="Leave channel", required=False, placeholder="#channel or ID"
    )
    message = discord.ui.TextInput(
        label="Leave message",
        style=discord.TextStyle.long,
        required=False,
        placeholder="Use {member} for mention",
    )

    def __init__(self, wizard: "SetupWizard"):
        super().__init__()
        self.wizard = wizard

    async def on_submit(self, interaction: discord.Interaction):
        channel = _parse_channel(interaction.guild, self.channel.value)
        if channel:
            set_leave_channel(interaction.guild.id, channel.id)
        if self.message.value:
            set_leave_message(interaction.guild.id, self.message.value)
        await interaction.response.send_message("Leave settings saved.", ephemeral=True)
        await self.wizard.advance(interaction)


class BoosterModal(discord.ui.Modal, title="Booster system"):
    channel = discord.ui.TextInput(
        label="Booster channel", required=False, placeholder="#channel or ID"
    )
    message = discord.ui.TextInput(
        label="Booster message",
        style=discord.TextStyle.long,
        required=False,
        placeholder="Message when someone boosts",
    )

    def __init__(self, wizard: "SetupWizard"):
        super().__init__()
        self.wizard = wizard

    async def on_submit(self, interaction: discord.Interaction):
        channel = _parse_channel(interaction.guild, self.channel.value)
        if channel:
            set_booster_channel(interaction.guild.id, channel.id)
        if self.message.value:
            set_booster_message(interaction.guild.id, self.message.value)
        await interaction.response.send_message("Booster settings saved.", ephemeral=True)
        await self.wizard.advance(interaction)


class LogChannelModal(discord.ui.Modal, title="Log channel"):
    channel = discord.ui.TextInput(
        label="Log channel", required=False, placeholder="#channel or ID"
    )

    def __init__(self, wizard: "SetupWizard"):
        super().__init__()
        self.wizard = wizard

    async def on_submit(self, interaction: discord.Interaction):
        channel = _parse_channel(interaction.guild, self.channel.value)
        if channel:
            set_log_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message("Log channel set.", ephemeral=True)
        await self.wizard.advance(interaction)


class AntiNukeLogModal(discord.ui.Modal, title="Anti-nuke log channel"):
    channel = discord.ui.TextInput(
        label="Anti-nuke log channel", required=False, placeholder="#channel or ID"
    )

    def __init__(self, wizard: "SetupWizard"):
        super().__init__()
        self.wizard = wizard

    async def on_submit(self, interaction: discord.Interaction):
        channel = _parse_channel(interaction.guild, self.channel.value)
        if channel:
            set_anti_nuke_log_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(
            "Anti-nuke log channel set.", ephemeral=True
        )
        await self.wizard.advance(interaction)


class SafeUsersModal(discord.ui.Modal, title="Anti-nuke safe users"):
    users = discord.ui.TextInput(
        label="Users",
        style=discord.TextStyle.long,
        required=False,
        placeholder="Mention or IDs separated by spaces",
    )

    def __init__(self, wizard: "SetupWizard"):
        super().__init__()
        self.wizard = wizard

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        for token in self.users.value.split():
            member = _parse_member(guild, token)
            if member:
                add_safe_user(guild.id, member.id)
        await interaction.response.send_message("Safe users updated.", ephemeral=True)
        await self.wizard.advance(interaction)


class SafeRolesModal(discord.ui.Modal, title="Anti-nuke safe roles"):
    roles = discord.ui.TextInput(
        label="Roles",
        style=discord.TextStyle.long,
        required=False,
        placeholder="Mention or IDs separated by spaces",
    )

    def __init__(self, wizard: "SetupWizard"):
        super().__init__()
        self.wizard = wizard

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        for token in self.roles.value.split():
            role = _parse_role(guild, token)
            if role:
                add_safe_role(guild.id, role.id)
        await interaction.response.send_message("Safe roles updated.", ephemeral=True)
        await self.wizard.advance(interaction)


class AntiNukeModal(discord.ui.Modal):
    enable = discord.ui.TextInput(
        label="Enable? yes/no", required=False, placeholder="yes"
    )
    threshold = discord.ui.TextInput(
        label="Threshold", required=False, placeholder="Number of actions"
    )
    punishment = discord.ui.TextInput(
        label="Punishment", required=False, placeholder="timeout/strip/kick/ban"
    )
    duration = discord.ui.TextInput(
        label="Duration", required=False, placeholder="e.g. 60s for timeout"
    )

    def __init__(self, wizard: "SetupWizard", category: str):
        title = f"Anti-nuke: {category}"
        super().__init__(title=title)
        self.wizard = wizard
        self.category = category

    async def on_submit(self, interaction: discord.Interaction):
        enabled = (
            1
            if self.enable.value.lower() in {"yes", "y", "true", "1"}
            else 0
        )
        threshold = int(self.threshold.value or 1)
        punishment = self.punishment.value.lower() or "kick"
        dur = (
            parse_duration(self.duration.value)
            if self.duration.value
            else None
        )
        set_anti_nuke_setting(
            self.category,
            enabled,
            threshold,
            punishment,
            dur,
            interaction.guild.id,
        )
        await interaction.response.send_message(
            f"Anti-nuke settings for {self.category} saved.", ephemeral=True
        )
        await self.wizard.advance(interaction)



class FilterWordsModal(discord.ui.Modal, title="Filtered words"):
    words = discord.ui.TextInput(
        label="Words",
        style=discord.TextStyle.long,
        required=False,
        placeholder="word1, word2, word3",
    )

    def __init__(self, wizard: "SetupWizard"):
        super().__init__()
        self.wizard = wizard

    async def on_submit(self, interaction: discord.Interaction):
        for word in self.words.value.replace("\n", ",").split(","):
            w = word.strip()
            if w:
                add_filtered_word(interaction.guild.id, w)
        await interaction.response.send_message("Filtered words saved.", ephemeral=True)
        await self.wizard.advance(interaction)


class TriggerResponsesModal(discord.ui.Modal, title="Trigger responses"):
    mappings = discord.ui.TextInput(
        label="trigger|response",
        style=discord.TextStyle.long,
        required=False,
        placeholder="hello|Hi there!\nbye|See you!",
    )

    def __init__(self, wizard: "SetupWizard"):
        super().__init__()
        self.wizard = wizard

    async def on_submit(self, interaction: discord.Interaction):
        from events import trigger_responses

        for line in self.mappings.value.splitlines():
            if "|" not in line:
                continue
            trigger, response = line.split("|", 1)
            if trigger and response:
                trig = trigger.strip()
                resp = response.strip()
                add_trigger_response(trig, resp, interaction.guild.id)
                trigger_responses.setdefault(interaction.guild.id, {})[trig.lower()] = resp
        await interaction.response.send_message("Trigger responses saved.", ephemeral=True)
        await self.wizard.advance(interaction)


# ---------------------------------------------------------------------------
# Wizard logic
# ---------------------------------------------------------------------------


@dataclass
class WizardStep:
    title: str
    description: str
    importance: str
    modal_factory: Optional[Callable[["SetupWizard"], discord.ui.Modal]] = None
    instruction: Optional[str] = None



class StepView(discord.ui.View):
    def __init__(self, wizard: "SetupWizard", step: WizardStep):
        super().__init__(timeout=None)
        self.wizard = wizard
        self.step = step

    @discord.ui.button(label="Configure", style=discord.ButtonStyle.green)
    async def configure(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.step.modal_factory:
            modal = self.step.modal_factory(self.wizard)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message(
                self.step.instruction or "No action required.", ephemeral=True
            )
            await self.wizard.advance(interaction)


    @discord.ui.button(label="Skip", style=discord.ButtonStyle.gray)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Step skipped.", ephemeral=True)
        await self.wizard.advance(interaction)


class SetupWizard:
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.steps = self._build_steps()
        self.index = 0
        self.message: Optional[discord.Message] = None

    def _build_steps(self) -> List[WizardStep]:
        steps: List[WizardStep] = [
            WizardStep(
                "Welcome system",
                "Set channel and message for welcoming new members.",
                "Medium",
                lambda w: WelcomeModal(w),
            ),
            WizardStep(
                "Leave system",
                "Set channel and message when members leave.",
                "Low",
                lambda w: LeaveModal(w),
            ),
            WizardStep(
                "Booster system",
                "Announce server boosters with custom message.",
                "Low",
                lambda w: BoosterModal(w),
            ),
            WizardStep(
                "Log channel",
                "Where general bot logs should go.",
                "High",
                lambda w: LogChannelModal(w),
            ),
            WizardStep(
                "Anti-nuke log channel",
                "Channel used to report anti-nuke actions.",
                "High",
                lambda w: AntiNukeLogModal(w),
            ),
            WizardStep(
                "Anti-nuke safe users",
                "Users ignored by anti-nuke.",
                "Medium",
                lambda w: SafeUsersModal(w),
            ),
            WizardStep(
                "Anti-nuke safe roles",
                "Roles ignored by anti-nuke.",
                "Medium",
                lambda w: SafeRolesModal(w),
            ),
        ]
        for cat in CATEGORIES.keys():
            steps.append(
                WizardStep(
                    f"Anti-nuke: {cat}",
                    f"Configure protection for {cat.replace('_', ' ')}.",
                    "High",
                    lambda w, c=cat: AntiNukeModal(w, c),
                )
            )
        steps.extend(
            [
                WizardStep(
                    "Server roles",
                    "Map custom names to role IDs for use in commands.",
                    "Medium",
                    instruction=(
                        "Use `/setrole <name> <@role>` after the wizard to register"
                        " role shortcuts."
                    ),

                ),
                WizardStep(
                    "Command permissions",
                    "Restrict commands to specific roles.",
                    "Medium",
                    instruction=(
                        "Use `/setcommandrole <command> <@role>` after the wizard"
                        " to limit command usage."
                    ),

                ),
                WizardStep(
                    "Filtered words",
                    "Block messages containing certain words.",
                    "Low",
                    lambda w: FilterWordsModal(w),
                ),
                WizardStep(
                    "Trigger responses",
                    "Automatic replies for keywords.",
                    "Low",
                    lambda w: TriggerResponsesModal(w),
                ),
            ]
        )
        return steps

    async def start(self) -> None:
        embed = self._build_embed()
        view = StepView(self, self.steps[self.index])
        await self.interaction.response.send_message(
            embed=embed, view=view, ephemeral=True
        )
        self.message = await self.interaction.original_response()

    async def advance(self, interaction: discord.Interaction) -> None:
        self.index += 1
        if self.index >= len(self.steps):
            await self.message.edit(
                content="✅ Setup complete! Run /setup-wizard again to revisit steps.",
                embed=None,
                view=None,
            )
            return
        embed = self._build_embed()
        view = StepView(self, self.steps[self.index])
        await self.message.edit(embed=embed, view=view)

    def _build_embed(self) -> discord.Embed:
        step = self.steps[self.index]
        embed = discord.Embed(
            title=f"Setup Wizard ({self.index + 1}/{len(self.steps)}): {step.title}",
            description=step.description,
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Importance", value=step.importance)
        embed.set_footer(text="Configure or skip using the buttons below.")
        return embed


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------


def setup(bot: commands.Bot):
    @bot.tree.command(
        name="setup-wizard", description="Start an interactive setup wizard for this server"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def _setup_wizard(interaction: discord.Interaction):
        wizard = SetupWizard(interaction)
        await wizard.start()
