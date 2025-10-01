import discord
from discord import app_commands
from discord.ext import commands

from .hybrid_helpers import add_prefix_command
from permissions import describe_permission

# Custom explanations for commands. Add entries here to provide
# longer or more detailed descriptions than the default command
# summary. Keys are command names, values are explanation strings.
COMMAND_EXPLANATIONS: dict[str, str] = {
    "explain": (
        "Shows detailed information about a command, including what it does, "
        "its parameters and the role needed to run it."
    ),
    "steal": (
        "Attempts to steal coins from another user. You must have at least 3 stealth points. "
        "If you succeed, you get a portion of the target's coins. If you fail, you get nothing. "
        "Has a cooldown of 45 minutes. You cannot steal from yourself or very poor users. "
        "Make sure you have registered and upgraded your stealth stat before using this."
    ),
    "hack": (
        "Tries to hack the bank to gain coins. You need at least 3 intelligence points to attempt this. "
        "Success is based on your intelligence level. If it fails, you lose some coins. "
        "Cooldown is 45 minutes. Always make sure your intelligence stat is high enough before trying."
    ),
    "fight": (
        "Challenges another user to a coin fight. You need at least 3 strength points to use this. "
        "The winner is based on comparing strength stats. The loser gives some coins to the winner. "
        "You cannot fight yourself and must wait 45 minutes between uses. "
        "Upgrade your strength to increase your chance of winning."
    ),
    "test": (
        "Runs a diagnostic test for all bot commands and reports which ones are working. "
        "Only accessible to admins. Useful for checking if the bot is functioning properly after updates."
    ),
    "setstatpoints": (
        "Sets the amount of unspent stat points a user has. Only usable by the bot owner or admins. "
        "This command is helpful for manually adjusting a user’s progress or correcting data."
    ),
    "lastdate": (
        "Displays the last active date of a specific user. "
        "Only usable by members with the moderation role (ID 1380267391598071859). "
        "Useful for activity tracking or moderation."
    ),
    "setstat": (
        "Sets a specific stat (intelligence, strength, or stealth) to a new value for a user. "
        "Admin-only. Used to manually adjust user stats, e.g., for testing or corrections."
    ),
    "addshoprole": (
        "Adds a new role to the role shop, making it available for users to purchase with coins. "
        "Admins can define the name, price, and color. Optionally, the role can be positioned relative to another role."
    ),
    "shop": (
        "Displays a list of all purchasable roles from the role shop, including their coin cost. "
        "Useful for users to see what they can buy."
    ),
    "buyrole": (
        "Allows users to buy a shop role using coins. "
        "The role must be listed in the shop. The user must have enough balance to purchase it."
    ),
    "manageprisonmember": (
        "Sends a user to prison (restricting access) or frees them from it. "
        "You can specify a duration or cancel an existing prison timer. Only for the moderation role (ID 1380267391598071859). "
        "Useful for soft moderation or fun punishment features."
    ),
    "antinukeconfig": (
        "Configures anti-nuke settings for your server. You choose a category (like delete_roles, kick, ban), "
        "set a threshold (number of actions before punishment), select a punishment (timeout, strip, kick, ban), "
        "optionally set duration (for timeout), and enable or disable the protection. "
        "Only members with the admin role (ID 1351479405699928108) can use this command."
    ),
    "antinukeignoreuser": (
        "Toggles whether a specific user is marked as safe from anti-nuke checks. "
        "If the user is already marked safe, they are removed. Only usable by the admin role (ID 1351479405699928108)."
    ),
    "antinukeignorerole": (
        "Toggles whether a specific role is marked as safe from anti-nuke checks. "
        "If the role is already marked safe, it is removed. Only usable by the admin role (ID 1351479405699928108)."
    ),
    "antinukelog": (
        "Sets the channel where anti-nuke actions are logged. "
        "Only the admin role (ID 1351479405699928108) can use this. Important to review automatic punishments."
    ),
    "antinukesettings": (
        "Displays the current anti-nuke settings and safe users/roles for your server. "
        "Only the admin role (ID 1351479405699928108) can access this. Helps verify what protections are active."
    ),
    "customrole": (
        "Creates or updates your personal booster role. "
        "You must be a server booster to use this. You can choose the name and color (in hex format). "
        "If you already have a role, it will be updated instead of creating a new one."
    ),
    "grantrole": (
        "Allows a booster to give their custom booster role to another user. "
        "You must already have a custom role to use this command. "
        "You cannot give it to yourself. Useful for sharing your perks with friends."
    ),
    "request": (
        "Sends a request to another user, asking them to send you a specific amount of coins. "
        "The other user can accept or decline within 60 seconds. "
        "You must specify the amount, and the recipient must have enough coins to accept."
    ),
    "duel": (
        "Challenges another user to a duel where both players bet coins. "
        "If the other user accepts, both must pick rock, paper, or scissors. "
        "The winner takes the coins. If it's a tie, no one wins. Duel times out in 60 seconds."
    ),
    "blackjack": (
        "Starts a game of Blackjack where you play against the bot dealer. "
        "You bet coins, draw cards, and try to get close to 21 without going over. "
        "If you win, you earn your bet; if you lose, you forfeit your bet."
    ),
    "poker": (
        "Starts a multiplayer poker game. Other users can join during the countdown. "
        "Each player bets coins and receives cards. The user with the best hand wins the pot. "
        "You need enough coins to join or start the game."
    ),
    "daily": (
        "Claims your daily reward in coins. Can only be used once every 24 hours. "
        "Make sure to use it regularly to maximize your earnings."
    ),
    "weekly": (
        "Claims your weekly coin reward. Can only be used once every 7 days. "
        "Yields a higher amount than the daily reward."
    ),
    "balance": (
        "Shows your current coin balance. Use this to check if you can afford items or games."
    ),
    "leaderboard": (
        "Displays the top richest users on the server. "
        "Good for checking who has the highest balance and competing with others."
    ),
    "forcelowercase": (
        "Toggles a setting that forces a specific user's messages to appear in lowercase. "
        "Only members with the moderation role (ID 1380267391598071859) can use this. It's a fun moderation tool or prank."
    ),
    "punch": (
        "Sends a random anime-style punch GIF showing you punching another user. "
        "Only for fun and visuals. Cannot be used on yourself."
    ),
    "stab": (
        "Sends a random anime-style stabbing GIF. 50% chance to succeed. "
        "Sometimes plays special GIFs if you try to stab yourself. "
        "Purely for entertainment. May fail if target has higher permissions than the bot."
    ),
    "goon": (
        "Sends a 'goon' themed animation directed at another user. Intended for humorous or exaggerated interactions. "
        "Mostly used for fun and memes."
    ),
    "stats": (
        "Displays your current stats: intelligence, strength, stealth, and any unspent stat points. "
        "You can also view another user's stats by mentioning them."
    ),
    "quest": (
        "Completes a small quest to earn 1–3 stat points. "
        "Usable every 3 hours. Helps you grow your character over time."
    ),
    "buypoints": (
        "Lets you buy stat points using your coins. "
        "Each point has a fixed price. Use this to improve your stats faster."
    ),
    "allocate": (
        "Spends unspent stat points to increase a specific stat (intelligence, strength, or stealth). "
        "You must have enough points and provide a valid stat name. Your stats affect other features like fight, hack, or steal."
    ),
    "fishing": (
        "A fun command that lets you 'go fishing'. You receive a random fishing GIF. "
        "Sometimes rewards you with stat points or just funny animations."
    ),
    "setupwizard": (
        "Starts an interactive setup process to configure the server features like welcome messages, "
        "leave messages, booster settings, logging, and anti-nuke. "
        "You will be guided through modals to input channels, messages, roles, and configurations. "
        "Recommended to run this after adding the bot to your server. Requires the admin role (ID 1351479405699928108)."
    ),
    "dance": (
        "Sends a random anime dance GIF with a fun message. "
        "No input required. Great for expressing yourself or just being silly."
    ),
    "kiss": (
        "Sends a kiss GIF showing affection toward another user. "
        "You must mention who you want to kiss. Purely visual and fun."
    ),
    "blush": (
        "Sends a GIF of you blushing. You can optionally include another user as the reason for blushing. "
        "If no user is mentioned, it just shows you blushing alone."
    ),
    "woah": (
        "Sends a 'woah' GIF to show you're amazed or surprised. No input needed. "
        "Just a fun visual reaction."
    ),
    "tickle": (
        "Sends a tickling GIF toward another user. It's a playful command for fun interactions."
    ),
    "slap": (
        "Sends a slap GIF showing you slapping another user. Sometimes a GIF might not load. "
        "Intended for humorous, light-hearted interactions."
    ),
    "lick": (
        "Licks another member and shows a corresponding anime GIF. "
        "Used for very silly or affectionate roleplay. Only works if you mention a user."
    ),
    "good": (
        "Tells another user they are a 'good boy', 'good girl', or 'good child', depending on their roles. "
        "Includes a pat GIF. Can fail if roles aren’t configured properly."
    ),
}


def setup(bot: commands.Bot):
    @bot.tree.command(
        name="explain", description="Explain a bot command and its permissions"
    )
    @app_commands.describe(command="Command to explain")
    async def explain(interaction: discord.Interaction, command: str):
        cmd = bot.tree.get_command(command)
        if cmd is None:
            await interaction.response.send_message("Unknown command.", ephemeral=True)
            return

        guild = interaction.guild
        role_mention = describe_permission(guild, command)

        params_lines: list[str] = []
        for param in cmd.parameters:
            name = getattr(param, "name", "")
            if name in ("self", "interaction"):
                continue
            desc = getattr(param, "description", None) or "No description"
            params_lines.append(f"`{name}`: {desc}")
        params_info = "\n".join(params_lines) if params_lines else "None"

        explanation = COMMAND_EXPLANATIONS.get(cmd.name, cmd.description)

        await interaction.response.send_message(
            f"**/{cmd.name}**\n{explanation}\n"
            f"**Parameters:**\n{params_info}\n"
            f"**Required Role:** {role_mention}",
            ephemeral=True,
        )

    add_prefix_command(bot, explain)

    @explain.autocomplete("command")
    async def explain_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        commands_list = []
        for c in bot.tree.get_commands():
            if current.lower() in c.name.lower():
                commands_list.append(app_commands.Choice(name=c.name, value=c.name))
        return commands_list[:25]
