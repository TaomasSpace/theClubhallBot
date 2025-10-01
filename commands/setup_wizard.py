from dataclasses import dataclass
from typing import Callable, List, Optional, Union

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
from utils import parse_duration, has_command_permission
from .hybrid_helpers import add_prefix_command
from anti_nuke import CATEGORIES


# ---------------------------------------------------------------------------
# Views and modals for each step
# ---------------------------------------------------------------------------


class MessageModal(discord.ui.Modal, title="Message"):
    content = discord.ui.TextInput(
        label="Message",
        style=discord.TextStyle.long,
        required=False,
    )

    def __init__(self, view: "ChannelMessageView"):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        self.view.message_value = self.content.value
        await interaction.response.send_message(
            "Message stored, click Save to apply.", ephemeral=True
        )


class ChannelMessageView(discord.ui.View):
    def __init__(
        self,
        wizard: "SetupWizard",
        channel_setter: Callable[[int, int], None],
        message_setter: Callable[[int, str], None],
        success: str,
        placeholder: str,
    ):
        super().__init__(timeout=None)
        self.wizard = wizard
        self.channel_setter = channel_setter
        self.message_setter = message_setter
        self.success = success
        self.message_value: Optional[str] = None
        self.select = discord.ui.ChannelSelect(placeholder=placeholder, min_values=0, max_values=1)
        self.add_item(self.select)

    @discord.ui.button(label="Set message", style=discord.ButtonStyle.blurple)
    async def set_message(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(MessageModal(self))

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = self.select.values[0] if self.select.values else None
        if channel:
            self.channel_setter(interaction.guild.id, channel.id)
        if self.message_value:
            self.message_setter(interaction.guild.id, self.message_value)
        await interaction.response.send_message(self.success, ephemeral=True)
        await self.wizard.advance(interaction)


class ChannelSelectView(discord.ui.View):
    def __init__(
        self,
        wizard: "SetupWizard",
        channel_setter: Callable[[int, int], None],
        success: str,
        placeholder: str,
    ):
        super().__init__(timeout=None)
        self.wizard = wizard
        self.channel_setter = channel_setter
        self.success = success
        self.select = discord.ui.ChannelSelect(placeholder=placeholder)
        self.add_item(self.select)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = self.select.values[0]
        self.channel_setter(interaction.guild.id, channel.id)
        await interaction.response.send_message(self.success, ephemeral=True)
        await self.wizard.advance(interaction)


class UserSelectView(discord.ui.View):
    def __init__(self, wizard: "SetupWizard"):
        super().__init__(timeout=None)
        self.wizard = wizard
        self.select = discord.ui.UserSelect(placeholder="Select users")
        self.add_item(self.select)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        for member in self.select.values:
            add_safe_user(guild.id, member.id)
        await interaction.response.send_message("Safe users updated.", ephemeral=True)
        await self.wizard.advance(interaction)


class RoleSelectView(discord.ui.View):
    def __init__(self, wizard: "SetupWizard"):
        super().__init__(timeout=None)
        self.wizard = wizard
        self.select = discord.ui.RoleSelect(placeholder="Select roles")
        self.add_item(self.select)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        for role in self.select.values:
            add_safe_role(guild.id, role.id)
        await interaction.response.send_message("Safe roles updated.", ephemeral=True)
        await self.wizard.advance(interaction)


class WelcomeView(ChannelMessageView):
    def __init__(self, wizard: "SetupWizard"):
        super().__init__(
            wizard,
            set_welcome_channel,
            set_welcome_message,
            "Welcome settings saved.",
            "Select welcome channel",
        )


class LeaveView(ChannelMessageView):
    def __init__(self, wizard: "SetupWizard"):
        super().__init__(
            wizard,
            set_leave_channel,
            set_leave_message,
            "Leave settings saved.",
            "Select leave channel",
        )


class BoosterView(ChannelMessageView):
    def __init__(self, wizard: "SetupWizard"):
        super().__init__(
            wizard,
            set_booster_channel,
            set_booster_message,
            "Booster settings saved.",
            "Select booster channel",
        )


class LogChannelView(ChannelSelectView):
    def __init__(self, wizard: "SetupWizard"):
        super().__init__(
            wizard,
            set_log_channel,
            "Log channel set.",
            "Select log channel",
        )


class AntiNukeLogView(ChannelSelectView):
    def __init__(self, wizard: "SetupWizard"):
        super().__init__(
            wizard,
            set_anti_nuke_log_channel,
            "Anti-nuke log channel set.",
            "Select anti-nuke log channel",
        )


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
    ui_factory: Optional[
        Callable[["SetupWizard"], Union[discord.ui.View, discord.ui.Modal]]
    ] = None
    instruction: Optional[str] = None



class StepView(discord.ui.View):
    def __init__(self, wizard: "SetupWizard", step: WizardStep):
        super().__init__(timeout=None)
        self.wizard = wizard
        self.step = step

    @discord.ui.button(label="Configure", style=discord.ButtonStyle.green)
    async def configure(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.step.ui_factory:
            ui = self.step.ui_factory(self.wizard)
            if isinstance(ui, discord.ui.Modal):
                await interaction.response.send_modal(ui)
            else:
                await interaction.response.send_message(view=ui, ephemeral=True)
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
                lambda w: WelcomeView(w),
            ),
            WizardStep(
                "Leave system",
                "Set channel and message when members leave.",
                "Low",
                lambda w: LeaveView(w),
            ),
            WizardStep(
                "Booster system",
                "Announce server boosters with custom message.",
                "Low",
                lambda w: BoosterView(w),
            ),
            WizardStep(
                "Log channel",
                "Where general bot logs should go.",
                "High",
                lambda w: LogChannelView(w),
            ),
            WizardStep(
                "Anti-nuke log channel",
                "Channel used to report anti-nuke actions.",
                "High",
                lambda w: AntiNukeLogView(w),
            ),
            WizardStep(
                "Anti-nuke safe users",
                "Users ignored by anti-nuke.",
                "Medium",
                lambda w: UserSelectView(w),
            ),
            WizardStep(
                "Anti-nuke safe roles",
                "Roles ignored by anti-nuke.",
                "Medium",
                lambda w: RoleSelectView(w),
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
                        "Make sure staff members have the required Discord roles"
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
    async def _setup_wizard(interaction: discord.Interaction):
        if not has_command_permission(interaction.user, "setup-wizard", "admin"):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        wizard = SetupWizard(interaction)
        await wizard.start()

    add_prefix_command(bot, _setup_wizard, name="setupwizard")
