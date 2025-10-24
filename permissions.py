"""Static command permission configuration.

This module centralises the mapping between commands and the roles allowed to
use them. The goal is to avoid database lookups for permissions and to make the
rules easy to audit in version control.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import discord

# Role identifiers
ADMIN_ROLE_ID = 1_351_479_405_699_928_108
MOD_ROLE_ID = 1_380_267_391_598_071_859
VILTRUMITE_ROLE_ID = 1_387_453_778_445_340_872


@dataclass(frozen=True)
class PermissionRule:
    role_ids: frozenset[int] = frozenset()
    allow_boosters: bool = False
    allow_everyone: bool = False


ALLOW_EVERYONE = PermissionRule(allow_everyone=True)

COMMAND_PERMISSION_RULES: Mapping[str, PermissionRule] = dict(
    {
        "test": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "setstatpoints": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "lastdate": PermissionRule(role_ids=frozenset({MOD_ROLE_ID})),
        "setstat": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "addshoprole": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "chatrevive": PermissionRule(role_ids=frozenset({MOD_ROLE_ID})),
        "manageprisonmember": PermissionRule(role_ids=frozenset({MOD_ROLE_ID})),
        "manageviltrumite": PermissionRule(role_ids=frozenset({VILTRUMITE_ROLE_ID})),
        "addcolorreactionrole": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "imitate": PermissionRule(
            role_ids=frozenset({MOD_ROLE_ID}), allow_boosters=True
        ),
        "giveaway": PermissionRule(role_ids=frozenset({MOD_ROLE_ID})),
        "lock": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "unlock": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "addfilterword": PermissionRule(role_ids=frozenset({MOD_ROLE_ID})),
        "removefilterword": PermissionRule(role_ids=frozenset({MOD_ROLE_ID})),
        "addtrigger": PermissionRule(role_ids=frozenset({MOD_ROLE_ID})),
        "removetrigger": PermissionRule(role_ids=frozenset({MOD_ROLE_ID})),
        "setwelcomechannel": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "setwelcomemsg": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "setleavechannel": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "setleavemsg": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "setboostchannel": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "setboostmsg": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "setlogchannel": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "serversettings": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "createrole": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "give": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "remove": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "logmessages": PermissionRule(role_ids=frozenset({MOD_ROLE_ID})),
        "setup-wizard": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "forcelowercase": PermissionRule(role_ids=frozenset({MOD_ROLE_ID})),
        "antinukeconfig": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "antinukeignoreuser": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "antinukeignorerole": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "antinukelog": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
        "antinukesettings": PermissionRule(role_ids=frozenset({ADMIN_ROLE_ID})),
    }
)

# Prefix aliases share the same rules
COMMAND_PERMISSION_RULES = {
    **COMMAND_PERMISSION_RULES,
    "setupwizard": COMMAND_PERMISSION_RULES["setup-wizard"],
}


def get_permission_rule(command: str) -> PermissionRule:
    return COMMAND_PERMISSION_RULES.get(command, ALLOW_EVERYONE)


def describe_permission(guild: discord.Guild | None, command: str) -> str:
    rule = get_permission_rule(command)
    if rule.allow_everyone:
        return "No specific role required"

    parts: list[str] = []
    if rule.role_ids:
        if guild is not None:
            role_mentions = []
            for rid in rule.role_ids:
                role = guild.get_role(rid)
                role_mentions.append(role.mention if role else f"Role ID {rid}")
        else:
            role_mentions = [f"Role ID {rid}" for rid in rule.role_ids]
        parts.append(" or ".join(role_mentions))

    if rule.allow_boosters:
        parts.append("Server Booster")

    return " or ".join(parts) if parts else "No specific role required"
