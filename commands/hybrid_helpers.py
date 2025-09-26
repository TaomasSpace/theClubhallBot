from __future__ import annotations

import enum
import inspect
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Optional, Sequence, Union, get_args, get_origin

import discord
from discord import app_commands
from discord.ext import commands


MISSING = object()

TRUE_VALUES = {"true", "t", "yes", "y", "1", "enable", "enabled", "on"}
FALSE_VALUES = {"false", "f", "no", "n", "0", "disable", "disabled", "off"}


_CONVERTER_TYPES: Mapping[type[Any], type[commands.Converter]] = {
    discord.Member: commands.MemberConverter,
    discord.User: commands.UserConverter,
    discord.Role: commands.RoleConverter,
    discord.TextChannel: commands.TextChannelConverter,
    discord.VoiceChannel: commands.VoiceChannelConverter,
    discord.CategoryChannel: commands.CategoryChannelConverter,
    discord.Thread: commands.ThreadConverter,
    discord.Emoji: commands.EmojiConverter,
    discord.PartialEmoji: commands.PartialEmojiConverter,
    discord.Guild: commands.GuildConverter,
    discord.Invite: commands.InviteConverter,
    discord.Message: commands.MessageConverter,
    discord.Colour: commands.ColourConverter,
    discord.Color: commands.ColourConverter,
}


def _strip_optional(annotation: Any) -> tuple[Any, bool]:
    optional = False
    while True:
        origin = get_origin(annotation)
        if origin is Union:
            args = [arg for arg in get_args(annotation) if arg is not type(None)]
            if len(args) == 1:
                annotation = args[0]
                optional = True
                continue
        if origin is app_commands.Transform:
            annotation = annotation.target
            continue
        break
    return annotation, optional


def _resolve_annotation(annotation: Any) -> Any:
    annotation, _ = _strip_optional(annotation)
    origin = get_origin(annotation)
    if origin is not None and origin is not Union:
        args = get_args(annotation)
        if args:
            return args[0]
    return annotation


def _literal_values(annotation: Any) -> Optional[Sequence[Any]]:
    if get_origin(annotation) is Literal:
        return get_args(annotation)
    return None


def _convert_bool(raw: str) -> bool:
    lowered = raw.lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    raise commands.BadArgument("Expected a boolean value (true/false).")


async def _convert_enum(annotation: type[enum.Enum], raw: str) -> enum.Enum:
    for member in annotation:
        if raw.lower() == member.name.lower() or raw.lower() == str(member.value).lower():
            return member
    valid = ", ".join(member.name.lower() for member in annotation)
    raise commands.BadArgument(f"Expected one of: {valid}.")


async def _convert_value(ctx: commands.Context, annotation: Any, raw: str) -> Any:
    annotation = _resolve_annotation(annotation)
    if annotation is inspect.Parameter.empty:
        annotation = str

    literal_values = _literal_values(annotation)
    if literal_values is not None:
        for value in literal_values:
            if raw.lower() == str(value).lower():
                return value
        valid = ", ".join(str(v) for v in literal_values)
        raise commands.BadArgument(f"Expected one of: {valid}.")

    if inspect.isclass(annotation) and issubclass(annotation, enum.Enum):
        return await _convert_enum(annotation, raw)

    converter_cls = _CONVERTER_TYPES.get(annotation)
    if converter_cls is not None:
        return await converter_cls().convert(ctx, raw)

    if annotation is str:
        return raw
    if annotation is int:
        try:
            return int(raw)
        except ValueError:
            raise commands.BadArgument("Expected an integer value.") from None
    if annotation is float:
        try:
            return float(raw)
        except ValueError:
            raise commands.BadArgument("Expected a number.") from None
    if annotation is bool:
        return _convert_bool(raw)
    if annotation is discord.Object:
        try:
            return discord.Object(id=int(raw))
        except ValueError:
            raise commands.BadArgument("Expected a numeric ID.") from None

    return raw


@dataclass
class PrefixArgumentSpec:
    parameter: inspect.Parameter
    slash_parameter: app_commands.Parameter | None

    def __post_init__(self) -> None:
        self.name = self.parameter.name
        default = self.parameter.default
        if default is inspect.Parameter.empty:
            default = getattr(self.slash_parameter, "default", MISSING)
        self.default = default
        self.annotation = self.parameter.annotation
        annotation, optional = _strip_optional(self.annotation)
        self.base_annotation = annotation
        self.optional = optional or self.default is not MISSING
        self.required = self.default is MISSING and not self.optional
        choices = getattr(self.slash_parameter, "choices", None) or []
        self._choice_map: dict[str, Any] = {}
        for choice in choices:
            value = getattr(choice, "value", getattr(choice, "name", choice))
            self._choice_map[str(value).lower()] = value
            name = getattr(choice, "name", None)
            if name is not None:
                self._choice_map[name.lower()] = value
        self.consume_rest = False

    @property
    def display_name(self) -> str:
        original = getattr(self.slash_parameter, "name", self.name)
        return original.replace("_", " ")

    def should_consume_rest(self) -> bool:
        return self.consume_rest

    def default_value(self) -> Any:
        if self.default is MISSING:
            return None
        return self.default

    async def convert(self, ctx: commands.Context, raw: Optional[str]) -> Any:
        if raw is None:
            if self.default is not MISSING:
                return self.default
            if self.optional:
                return None
            raise commands.BadArgument(f"Missing required argument: {self.display_name}.")

        lookup_key = raw.lower()
        if self._choice_map:
            if lookup_key not in self._choice_map:
                valid = ", ".join(sorted(set(self._choice_map)))
                raise commands.BadArgument(
                    f"Invalid choice for {self.display_name}. Valid options: {valid}."
                )
            mapped = self._choice_map[lookup_key]
            if not isinstance(mapped, str):
                return mapped
            raw = mapped

        try:
            return await _convert_value(ctx, self.base_annotation, raw)
        except commands.BadArgument:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise commands.BadArgument(
                f"Failed to convert argument {self.display_name}: {exc}"
            ) from exc


class PrefixAppCommand(commands.Command):
    def __init__(
        self,
        callback,
        *,
        param_specs: Sequence[PrefixArgumentSpec],
        **kwargs: Any,
    ) -> None:
        super().__init__(callback, **kwargs)
        self._param_specs = list(param_specs)
        for index, spec in enumerate(self._param_specs):
            if (
                index == len(self._param_specs) - 1
                and _resolve_annotation(spec.base_annotation) is str
                and not spec._choice_map
            ):
                spec.consume_rest = True

    async def _parse_arguments(self, ctx: commands.Context) -> None:  # type: ignore[override]
        converted: list[Any] = [ctx]
        total = len(self._param_specs)
        view = ctx.view
        for index, spec in enumerate(self._param_specs):
            view.skip_ws()
            if view.eof:
                raw_value: Optional[str] = None
            elif spec.should_consume_rest() and index == total - 1:
                remainder = view.read_rest()
                raw_value = remainder.strip() if remainder is not None else ""
                view.index = len(view.buffer)
            else:
                raw_value = view.get_quoted_word()
            if raw_value == "":
                raw_token: Optional[str] = ""
            else:
                raw_token = raw_value
            value = await spec.convert(ctx, raw_token)
            converted.append(value)
        view.skip_ws()
        if not view.eof:
            raise commands.BadArgument("Too many arguments provided.")
        ctx.args = tuple(converted)
        ctx.kwargs = {}


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
            if "content" in kwargs:
                raise TypeError("content specified both positionally and by keyword")
            if len(args) > 1:
                raise TypeError("send_message accepts at most one positional argument")
            kwargs["content"] = args[0]
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
            if "content" in kwargs:
                raise TypeError("content specified both positionally and by keyword")
            if len(args) > 1:
                raise TypeError("edit_message accepts at most one positional argument")
            kwargs["content"] = args[0]
        if self._message:
            await self._message.edit(**kwargs)
        else:
            await respond(self._ctx, **kwargs)

    async def edit_original_response(self, *args, **kwargs):
        if args:
            if "content" in kwargs:
                raise TypeError("content specified both positionally and by keyword")
            if len(args) > 1:
                raise TypeError("edit_original_response accepts at most one positional argument")
            kwargs["content"] = args[0]
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
    slash_params = params[1:]
    slash_metadata = list(getattr(command_obj, "parameters", [])) if command_obj else []
    param_specs = []
    for index, param in enumerate(slash_params):
        meta = slash_metadata[index] if index < len(slash_metadata) else None
        param_specs.append(PrefixArgumentSpec(param, meta))

    checks = list(getattr(func, "__discord_app_commands_checks__", []))

    async def wrapper(ctx: commands.Context, *converted):
        interaction = PrefixInteractionAdapter(ctx)
        for check in checks:
            try:
                result = check(interaction)
                if inspect.isawaitable(result):
                    await result
            except app_commands.AppCommandError as exc:
                raise commands.CheckFailure(str(exc)) from exc
        try:
            return await func(interaction, *converted)
        except app_commands.AppCommandError as exc:
            raise commands.CommandError(str(exc)) from exc

    wrapper.__name__ = f"{func.__name__}_prefix"
    if command_obj is not None and command_obj.description:
        wrapper.__doc__ = command_obj.description
    else:
        wrapper.__doc__ = func.__doc__

    command = PrefixAppCommand(
        wrapper,
        name=name or func.__name__,
        help=wrapper.__doc__,
        param_specs=param_specs,
    )
    bot.add_command(command)
    return command


async def respond(
    ctx: commands.Context,
    *args,
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

    if args:
        if content is not None:
            raise TypeError("content specified both positionally and by keyword")
        if len(args) > 1:
            raise TypeError("respond accepts at most one positional argument")
        content = args[0]

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
