import inspect
import discord
from discord import app_commands
from discord.ext import commands


class PrefixFollowupAdapter:
    def __init__(self, ctx: commands.Context):
        self._ctx = ctx

    async def send(self, *args, **kwargs):
        return await respond(self._ctx, *args, **kwargs)


class PrefixResponseAdapter:
    def __init__(self, ctx: commands.Context, interaction: "PrefixInteractionAdapter"):
        self._ctx = ctx
        self._interaction = interaction
        self._done = False
        self._message: discord.Message | None = None
        self._deferred = False
        self._deferred_ephemeral = False

    def is_done(self) -> bool:
        return self._done

    async def send_message(self, *args, **kwargs):
        if args:
            raise TypeError("Prefix command adapter only supports keyword arguments")
        self._done = True
        self._deferred = False
        self._message = await respond(self._ctx, **kwargs)
        return self._message

    async def defer(self, *, thinking: bool = False, ephemeral: bool = False):
        self._done = True
        self._deferred = True
        self._deferred_ephemeral = ephemeral
        if thinking:
            self._message = await respond(
                self._ctx, content="Processing...", ephemeral=ephemeral
            )

    async def send_modal(self, modal: discord.ui.Modal):
        self._done = True
        await respond(
            self._ctx,
            content="This action requires the slash command interface. Please use the slash command version instead.",
            ephemeral=True,
        )

    async def edit_message(self, *args, **kwargs):
        if args:
            raise TypeError("Prefix command adapter only supports keyword arguments")
        if self._message:
            await self._message.edit(**kwargs)
        else:
            await respond(self._ctx, **kwargs)

    async def edit_original_response(self, *args, **kwargs):
        if args:
            raise TypeError("Prefix command adapter only supports keyword arguments")
        if self._message:
            await self._message.edit(**kwargs)
        else:
            self._message = await respond(
                self._ctx,
                ephemeral=self._deferred_ephemeral,
                **kwargs,
            )
        return self._message

    @property
    def message(self) -> discord.Message | None:
        return self._message


class PrefixInteractionAdapter:
    def __init__(self, ctx: commands.Context):
        self._ctx = ctx
        self.user = ctx.author
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.client = ctx.bot
        self.response = PrefixResponseAdapter(ctx, self)
        self.followup = PrefixFollowupAdapter(ctx)

    @property
    def guild_id(self) -> int | None:
        return self.guild.id if self.guild else None

    @property
    def channel_id(self) -> int | None:
        return self.channel.id if self.channel else None

    async def edit_original_response(self, *args, **kwargs):
        return await self.response.edit_original_response(*args, **kwargs)

    async def original_response(self) -> discord.Message | None:
        return self.response.message


def add_prefix_command(
    bot: commands.Bot,
    func,
    *,
    name: str | None = None,
) -> commands.Command:
    """Register a prefix equivalent for an app-command callback."""

    command_obj: app_commands.Command | None = None
    if isinstance(func, app_commands.Command):
        command_obj = func
        func = command_obj.callback
        if name is None:
            name = command_obj.name


    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    if not params:
        raise TypeError("Command callback must accept at least an interaction/context parameter")
    prefix_params = [
        inspect.Parameter(
            "ctx",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=commands.Context,
        )
    ] + params[1:]
    new_sig = sig.replace(parameters=prefix_params)

    annotations = dict(getattr(func, "__annotations__", {}))
    annotations.pop(params[0].name, None)
    annotations["ctx"] = commands.Context

    checks = list(getattr(func, "__discord_app_commands_checks__", []))

    async def wrapper(*args, **kwargs):
        ctx: commands.Context = args[0]
        interaction = PrefixInteractionAdapter(ctx)
        for check in checks:
            try:
                result = check(interaction)
                if inspect.isawaitable(result):
                    await result
            except app_commands.AppCommandError as exc:
                raise commands.CheckFailure(str(exc)) from exc
        return await func(interaction, *args[1:], **kwargs)

    wrapper.__name__ = f"{func.__name__}_prefix"
    wrapper.__signature__ = new_sig
    wrapper.__annotations__ = annotations
    if command_obj is not None and command_obj.description:
        wrapper.__doc__ = command_obj.description
    else:
        wrapper.__doc__ = func.__doc__


    return bot.command(name=name or func.__name__)(wrapper)


async def respond(
    ctx: commands.Context,
    *,
    content: str | None = None,
    embed: discord.Embed | None = None,
    embeds: list[discord.Embed] | None = None,
    view: discord.ui.View | None = None,
    file: discord.File | None = None,
    files: list[discord.File] | None = None,
    ephemeral: bool = False,
    allowed_mentions: discord.AllowedMentions | None = None,
    delete_after: float | None = None,
) -> discord.Message | None:
    """Send a response that works for both prefix and slash invocations."""

    interaction = ctx.interaction
    if interaction:
        send_kwargs: dict[str, object] = {}
        if content is not None:
            send_kwargs["content"] = content
        if embed is not None:
            send_kwargs["embed"] = embed
        if embeds is not None:
            send_kwargs["embeds"] = embeds
        if view is not None:
            send_kwargs["view"] = view
        if file is not None:
            send_kwargs["file"] = file
        if files is not None:
            send_kwargs["files"] = files
        if allowed_mentions is not None:
            send_kwargs["allowed_mentions"] = allowed_mentions

        if interaction.response.is_done():
            return await interaction.followup.send(
                **send_kwargs, ephemeral=ephemeral, delete_after=delete_after
            )
        else:
            await interaction.response.send_message(
                **send_kwargs, ephemeral=ephemeral, delete_after=delete_after
            )
            if not interaction.response.is_done():
                return None
            try:
                return await interaction.original_response()
            except Exception:
                return None
        return

    send_kwargs2: dict[str, object] = {}
    if content is not None:
        send_kwargs2["content"] = content
    if embed is not None:
        send_kwargs2["embed"] = embed
    if embeds is not None:
        send_kwargs2["embeds"] = embeds
    if view is not None:
        send_kwargs2["view"] = view
    if file is not None:
        send_kwargs2["file"] = file
    if files is not None:
        send_kwargs2["files"] = files
    if allowed_mentions is not None:
        send_kwargs2["allowed_mentions"] = allowed_mentions
    if delete_after is not None:
        send_kwargs2["delete_after"] = delete_after

    return await ctx.send(**send_kwargs2)
