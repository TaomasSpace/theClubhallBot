import asyncio

import discord
from discord import app_commands, ui
from discord.ext import commands
from datetime import datetime, timedelta
from random import random, choice, shuffle
from collections import Counter

CARD_DECK: list[tuple[str, int]] = []
_rank_codes = [
    ("1", 11),  # Ace
    ("2", 2),
    ("3", 3),
    ("4", 4),
    ("5", 5),
    ("6", 6),
    ("7", 7),
    ("8", 8),
    ("9", 9),
    ("A", 10),  # Ten
    ("B", 10),  # Jack
    ("D", 10),  # Queen
    ("E", 10),  # King
]
for suit in "ABCD":  # spades, hearts, diamonds, clubs
    for code, value in _rank_codes:
        CARD_DECK.append((chr(int(f"1F0{suit}{code}", 16)), value))

_rank_map = {
    "1": 14,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "A": 10,
    "B": 11,
    "D": 12,
    "E": 13,
}
_suit_map = {"A": "S", "B": "H", "C": "D", "D": "C"}


def _parse_card(emoji: str) -> tuple[int, str]:
    code = f"{ord(emoji):05X}"
    return _rank_map[code[4]], _suit_map[code[3]]


def _hand_name(rank_type: int) -> str:
    names = [
        "High Card",
        "One Pair",
        "Two Pair",
        "Three of a Kind",
        "Straight",
        "Flush",
        "Full House",
        "Four of a Kind",
        "Straight Flush",
    ]
    return names[rank_type]


def _evaluate_hand(cards: list[tuple[int, str]]) -> tuple:
    ranks = sorted((r for r, _ in cards), reverse=True)
    counts = Counter(ranks)
    suits = Counter(s for _, s in cards)
    flush = next((s for s, c in suits.items() if c >= 5), None)
    unique = sorted(set(ranks), reverse=True)
    if 14 in unique:
        unique.append(1)
    straight_high = None
    for i in range(len(unique) - 4):
        seq = unique[i : i + 5]
        if seq[0] - seq[4] == 4:
            straight_high = seq[0]
            break
    if flush:
        flush_cards = [r for r, s in cards if s == flush]
        flush_cards.sort(reverse=True)
        fu = sorted(set(flush_cards), reverse=True)
        if 14 in fu:
            fu.append(1)
        for i in range(len(fu) - 4):
            seq = fu[i : i + 5]
            if seq[0] - seq[4] == 4:
                return (8, seq[0])
        return (5, flush_cards[:5])
    if 4 in counts.values():
        quad = max(r for r, c in counts.items() if c == 4)
        kicker = max(r for r in ranks if r != quad)
        return (7, quad, kicker)
    if 3 in counts.values() and 2 in counts.values():
        tri = max(r for r, c in counts.items() if c == 3)
        pair = max(r for r, c in counts.items() if c == 2)
        return (6, tri, pair)
    if straight_high:
        return (4, straight_high)
    if 3 in counts.values():
        tri = max(r for r, c in counts.items() if c == 3)
        kick = [r for r in ranks if r != tri][:2]
        return (3, tri, kick[0], kick[1])
    pairs = sorted([r for r, c in counts.items() if c == 2], reverse=True)
    if len(pairs) >= 2:
        kicker = max(r for r in ranks if r not in pairs)
        return (2, pairs[0], pairs[1], kicker)
    if len(pairs) == 1:
        pair = pairs[0]
        kick = [r for r in ranks if r != pair][:3]
        return (1, pair, kick[0], kick[1], kick[2])
    return (0, ranks[:5])

from config import (
    WEEKLY_REWARD,
    DAILY_REWARD,
    SUPERPOWER_COST,
    SUPERPOWER_COOLDOWN_HOURS,
)
from db.DBHelper import (
    register_user,
    safe_add_coins,
    get_money,
    set_money,
    set_max_coins,
    get_top_users,
    get_last_weekly,
    set_last_weekly,
    get_last_claim,
    set_last_claim,
    get_timestamp,
    set_timestamp,
    get_anime_title,
    set_anime_title,
)
from utils import has_command_permission


class RequestView(ui.View):
    def __init__(self, sender_id: int, receiver_id: int, amount: int):
        super().__init__(timeout=60)
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount

    @ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message(
                "This request isn't for you.", ephemeral=True
            )
            return
        sender_balance = get_money(str(self.sender_id))
        receiver_balance = get_money(str(self.receiver_id))
        if receiver_balance < self.amount:
            await interaction.response.send_message(
                "You don't have enough clubhall coins to accept this request.",
                ephemeral=True,
            )
            return
        set_money(str(self.receiver_id), receiver_balance - self.amount)
        set_money(str(self.sender_id), sender_balance + self.amount)
        await interaction.response.edit_message(
            content=f"✅ Request accepted. {self.amount} clubhall coins sent!",
            view=None,
        )

    @ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message(
                "This request isn't for you.", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content="❌ Request declined.", view=None
        )


class DuelRequestView(ui.View):
    def __init__(self, challenger_id: int, opponent_id: int, amount: int):
        super().__init__(timeout=60)
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.amount = amount

    @ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "This duel request isn't for you.", ephemeral=True
            )
            return
        opponent_balance = get_money(str(self.opponent_id))
        if opponent_balance < self.amount:
            await interaction.response.send_message(
                "You don't have enough clubhall coins to accept this duel.",
                ephemeral=True,
            )
            return
        view = RPSView(self.challenger_id, self.opponent_id, self.amount)
        view.message = interaction.message
        await interaction.response.edit_message(
            content=f"<@{self.challenger_id}> vs <@{self.opponent_id}> — choose your move!",
            view=view,
        )

    @ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "This duel request isn't for you.", ephemeral=True
            )
            return
        await interaction.response.edit_message(content="❌ Duel declined.", view=None)


class RPSView(ui.View):
    def __init__(self, p1_id: int, p2_id: int, bet: int):
        super().__init__(timeout=120)
        self.p1_id = p1_id
        self.p2_id = p2_id
        self.bet = bet
        self.choices: dict[int, str | None] = {p1_id: None, p2_id: None}
        self.message: discord.Message | None = None

    async def _choose(self, interaction: discord.Interaction, choice: str):
        if interaction.user.id not in self.choices:
            await interaction.response.send_message(
                "This duel isn't for you.", ephemeral=True
            )
            return
        if self.choices[interaction.user.id] is not None:
            await interaction.response.send_message(
                "You already chose.", ephemeral=True
            )
            return
        self.choices[interaction.user.id] = choice
        await interaction.response.send_message(f"You chose {choice}.", ephemeral=True)
        if all(self.choices.values()):
            await self._finish()

    async def _finish(self):
        c1 = self.choices[self.p1_id]
        c2 = self.choices[self.p2_id]
        winner: int | None = None
        if c1 != c2:
            beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
            if beats[c1] == c2:
                winner = self.p1_id
            else:
                winner = self.p2_id
        text = f"<@{self.p1_id}> chose **{c1}**, <@{self.p2_id}> chose **{c2}**."
        if winner is None:
            text += "\nIt's a draw!"
        else:
            loser = self.p2_id if winner == self.p1_id else self.p1_id
            loser_balance = get_money(str(loser))
            transfer = min(self.bet, loser_balance)
            set_money(str(loser), loser_balance - transfer)
            safe_add_coins(str(winner), transfer)
            text += f"\n<@{winner}> wins {transfer} coins!"
        self.clear_items()
        if self.message:
            await self.message.edit(content=text, view=None)
        self.stop()

    @ui.button(label="🪨 Rock", style=discord.ButtonStyle.secondary)
    async def rock(self, interaction: discord.Interaction, button: ui.Button):
        await self._choose(interaction, "rock")

    @ui.button(label="📄 Paper", style=discord.ButtonStyle.secondary)
    async def paper(self, interaction: discord.Interaction, button: ui.Button):
        await self._choose(interaction, "paper")

    @ui.button(label="✂️ Scissors", style=discord.ButtonStyle.secondary)
    async def scissors(self, interaction: discord.Interaction, button: ui.Button):
        await self._choose(interaction, "scissors")

    async def on_timeout(self) -> None:
        if self.message and any(v is None for v in self.choices.values()):
            await self.message.edit(content="⌛ Duel timed out.", view=None)
        self.stop()


class BlackjackView(ui.View):
    def __init__(self, user_id: int, bet: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.bet = bet
        self.player = [self._draw(), self._draw()]
        self.dealer = [self._draw(), self._draw()]
        self.message: discord.Message | None = None
        self.finished = False

    def _draw(self) -> tuple[str, int]:
        return choice(
            [
                ("🂱", 11),  # Ace of hearts
                ("🂲", 2),
                ("🂳", 3),
                ("🂴", 4),
                ("🂵", 5),
                ("🂶", 6),
                ("🂷", 7),
                ("🂸", 8),
                ("🂹", 9),
                ("🂺", 10),
                ("🂻", 10),  # Jack
                ("🂽", 10),  # Queen
                ("🂾", 10),  # King
            ]
        )

    def _total(self, hand: list[tuple[str, int]]) -> int:
        total = sum(v for _, v in hand)
        aces = sum(1 for _, v in hand if v == 11)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def _hand_str(self, hand: list[tuple[str, int]], hide_second: bool = False) -> str:
        if hide_second:
            return f"{hand[0][0]} 🂠"
        return " ".join(c for c, _ in hand)

    def _render(self, reveal: bool = False) -> str:
        dealer_val = self._total(self.dealer) if reveal else "?"
        dealer_hand = self._hand_str(self.dealer, hide_second=not reveal)
        player_val = self._total(self.player)
        player_hand = self._hand_str(self.player)
        return (
            f"**Dealer**: {dealer_hand} ({dealer_val})\n"
            f"**You**: {player_hand} ({player_val})\n"
            f"Bet: {self.bet} clubhall coins"
        )

    async def _finish(self, interaction: discord.Interaction, busted: bool = False):
        if self.finished:
            return
        self.finished = True
        while self._total(self.dealer) < 17:
            self.dealer.append(self._draw())

        player_total = self._total(self.player)
        dealer_total = self._total(self.dealer)
        if busted or player_total > 21:
            outcome = "lose"
        elif dealer_total > 21 or player_total > dealer_total:
            outcome = "win"
        elif dealer_total == player_total:
            outcome = "push"
        else:
            outcome = "lose"

        balance = get_money(str(self.user_id))
        if outcome == "win":
            safe_add_coins(str(self.user_id), self.bet)
            result_text = f"🎉 You won {self.bet} coins!"
        elif outcome == "push":
            result_text = "It's a draw."
        else:
            set_money(str(self.user_id), balance - self.bet)
            result_text = f"💀 You lost {self.bet} coins."

        self.clear_items()
        await interaction.response.edit_message(
            content=self._render(reveal=True) + f"\n{result_text}", view=None
        )
        self.stop()

    @ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This game isn't for you.", ephemeral=True
            )
            return
        self.player.append(self._draw())
        if self._total(self.player) > 21:
            await self._finish(interaction, busted=True)
        else:
            await interaction.response.edit_message(content=self._render(), view=self)

    @ui.button(label="Stand", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This game isn't for you.", ephemeral=True
            )
            return
        await self._finish(interaction)


class PokerJoinView(ui.View):
    def __init__(self, bot: commands.Bot, host_id: int, bet: int):
        super().__init__(timeout=30)
        self.bot = bot
        self.bet = bet
        self.players: dict[int, str] = {host_id: ""}
        self.message: discord.Message | None = None

    def render(self) -> str:
        joined = " ".join(f"<@{pid}>" for pid in self.players)
        return (
            f"Poker starting soon! Bet: {self.bet} coins\n"
            f"Players: {joined}\nPress Join to participate."
        )

    @ui.button(label="Join", style=discord.ButtonStyle.primary)
    async def join(self, interaction: discord.Interaction, button: ui.Button):
        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        if interaction.user.id in self.players:
            await interaction.response.send_message(
                "You're already in the game.", ephemeral=True
            )
            return
        if get_money(uid) < self.bet:
            await interaction.response.send_message(
                "Not enough coins to join.", ephemeral=True
            )
            return
        self.players[interaction.user.id] = interaction.user.display_name
        await interaction.response.send_message("Joined!", ephemeral=True)
        if self.message:
            await self.message.edit(content=self.render(), view=self)

    async def on_timeout(self) -> None:
        if not self.message:
            return
        await self.message.edit(content="Dealing cards...", view=None)
        await start_poker_game(self.message.channel, self.players, self.bet)


async def start_poker_game(
    channel: discord.abc.Messageable, players: dict[int, str], bet: int
) -> None:
    deck = CARD_DECK.copy()
    shuffle(deck)
    hands: dict[int, list[str]] = {}
    community = [deck.pop()[0] for _ in range(5)]
    active: dict[int, str] = {}
    pot = 0
    for pid, name in list(players.items()):
        uid = str(pid)
        balance = get_money(uid)
        if balance < bet:
            continue
        set_money(uid, balance - bet)
        pot += bet
        active[pid] = name
        hands[pid] = [deck.pop()[0], deck.pop()[0]]
    if not active:
        await channel.send("No players had enough coins for the game.")
        return

    ranks: dict[int, tuple] = {}
    for pid in active:
        cards = [
            _parse_card(c) for c in hands[pid] + community
        ]
        ranks[pid] = _evaluate_hand(cards)

    best = max(ranks.values())
    winners = [pid for pid, r in ranks.items() if r == best]
    prize = pot // len(winners)
    for pid in winners:
        safe_add_coins(str(pid), prize)

    text = f"Community: {' '.join(community)}\n"
    for pid, name in active.items():
        text += f"<@{pid}>: {' '.join(hands[pid])}\n"
    win_names = ', '.join(f"<@{pid}>" for pid in winners)
    text += f"Winner: {win_names} with {_hand_name(best[0])}! (+{prize} coins)"
    await channel.send(text)



def setup(bot: commands.Bot):
    @bot.tree.command(name="money", description="Check your clubhall coin balance")
    async def money(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        register_user(user_id, interaction.user.display_name)
        await interaction.response.send_message(
            f"You have {get_money(user_id)} clubhall coins.", ephemeral=True
        )

    @bot.tree.command(
        name="balance", description="Check someone else's clubhall coin balance"
    )
    async def balance(interaction: discord.Interaction, user: discord.Member):
        register_user(str(user.id), user.display_name)
        money_amt = get_money(str(user.id))
        await interaction.response.send_message(
            f"{user.display_name} has {money_amt} clubhall coins.", ephemeral=False
        )

    @bot.tree.command(
        name="give", description="Give coins to a user (Admin/Owner only)"
    )
    async def give(interaction: discord.Interaction, user: discord.Member, amount: int):
        if not has_command_permission(interaction.user, "give", "admin"):
            await interaction.response.send_message(
                "You don't have permission to give clubhall coins.",
                ephemeral=True,
            )
            return
        register_user(str(user.id), user.display_name)
        added = safe_add_coins(str(user.id), amount)
        if added == 0:
            await interaction.response.send_message(
                "Clubhall coin limit reached. No coins added.", ephemeral=True
            )
        elif added < amount:
            await interaction.response.send_message(
                f"Partial success: Only {added} coins added due to server limit.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"{added} clubhall coins added to {user.display_name}."
            )

    @bot.tree.command(
        name="remove",
        description="Remove clubhall coins from a user (Admin/Owner only)",
    )
    async def remove(
        interaction: discord.Interaction, user: discord.Member, amount: int
    ):
        if not has_command_permission(interaction.user, "remove", "admin"):
            await interaction.response.send_message(
                "You don't have permission to remove clubhall coins.",
                ephemeral=True,
            )
            return
        current = get_money(str(user.id))
        set_money(str(user.id), max(0, current - amount))
        await interaction.response.send_message(
            f"{amount} clubhall coins removed from {user.display_name}."
        )

    @bot.tree.command(name="donate", description="Send coins to another user")
    async def donate(
        interaction: discord.Interaction, user: discord.Member, amount: str
    ):
        sender_id = str(interaction.user.id)
        receiver_id = str(user.id)
        if sender_id == receiver_id:
            await interaction.response.send_message(
                "You can't donate coins on yourself.", ephemeral=True
            )
            return
        register_user(sender_id, interaction.user.display_name)
        register_user(receiver_id, user.display_name)
        sender_balance = get_money(sender_id)

        if interaction.user.id == 756537363509018736 and amount.lower() == "taoma":
            receiver_balance = get_money(receiver_id)
            amount_int = max(0, (sender_balance - receiver_balance) // 2 + 1)
            amount_int = min(amount_int, sender_balance)
        else:
            try:
                amount_int = int(amount)
            except Exception:
                await interaction.response.send_message(
                    "Invalid amount.", ephemeral=True
                )
                return

        if amount_int <= 0:
            await interaction.response.send_message(
                "Amount must be greater than 0.", ephemeral=True
            )
            return
        if amount_int > sender_balance:
            await interaction.response.send_message(
                "You don't have enough clubhall coins.", ephemeral=True
            )
            return
        set_money(sender_id, sender_balance - amount_int)
        safe_add_coins(receiver_id, amount_int)
        await interaction.response.send_message(
            f"💸 You donated **{amount_int}** clubhall coins on {user.display_name}!",
            ephemeral=False,
        )

    @bot.tree.command(
        name="setlimit", description="Set the maximum clubhall coins limit (Owner only)"
    )
    async def setlimit(interaction: discord.Interaction, new_limit: int):
        if not has_command_permission(interaction.user, "setlimit", "admin"):
            await interaction.response.send_message(
                "Only the owner can change the limit.", ephemeral=True
            )
            return
        set_max_coins(new_limit)
        await interaction.response.send_message(f"New coin limit set to {new_limit}.")

    @bot.tree.command(
        name="request", description="Request clubhall coins from another user"
    )
    async def request(
        interaction: discord.Interaction, user: discord.Member, amount: int, reason: str
    ):
        sender_id = interaction.user.id
        receiver_id = user.id
        if sender_id == receiver_id:
            await interaction.response.send_message(
                "You can't request clubhall coins from yourself.", ephemeral=True
            )
            return
        register_user(str(sender_id), interaction.user.display_name)
        register_user(str(receiver_id), user.display_name)
        view = RequestView(sender_id, receiver_id, amount)
        await interaction.response.send_message(
            f"{user.mention}, {interaction.user.display_name} requests **{amount}** clubhall coins for: _{reason}_",
            view=view,
        )

    @bot.tree.command(name="topcoins", description="Show the richest players")
    @app_commands.describe(count="How many spots to display (1–25)?")
    async def topcoins(interaction: discord.Interaction, count: int = 10):
        count = max(1, min(count, 25))
        top = get_top_users(count)
        if not top:
            await interaction.response.send_message("No data yet 🤷‍♂️")
            return
        lines = [
            f"**#{i + 1:02d}**  {name} – **{coins}** 💰"
            for i, (name, coins) in enumerate(top)
        ]
        embed = discord.Embed(
            title=f"🏆 Top {count} Coin Holders",
            description="\n".join(lines),
            colour=discord.Colour.gold(),
        )
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(
        name="weekly", description="Claim your weekly clubhall coins (7d cooldown)"
    )
    async def weekly(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        register_user(user_id, interaction.user.display_name)
        now = datetime.utcnow()
        last = get_last_weekly(user_id)
        if last and now - last < timedelta(days=7):
            remaining = timedelta(days=7) - (now - last)
            days, seconds = divmod(int(remaining.total_seconds()), 86400)
            hours, seconds = divmod(seconds, 3600)
            minutes = seconds // 60
            await interaction.response.send_message(
                f"⏳ You can claim again in **{days} days {hours} hours {minutes} minutes**.",
                ephemeral=True,
            )
            return
        added = safe_add_coins(user_id, WEEKLY_REWARD)
        set_last_weekly(user_id, now)
        if added > 0:
            await interaction.response.send_message(
                f"✅ {added} Coins added! You now have **{get_money(user_id)}** 💰.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "⚠️ Server coin limit reached. No weekly coins could be added.",
                ephemeral=True,
            )

    @bot.tree.command(
        name="daily", description="Claim your daily coins (24 h cooldown)"
    )
    async def daily(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        register_user(user_id, interaction.user.display_name)
        now = datetime.utcnow()
        last = get_last_claim(user_id)
        if last and now - last < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last)
            hours, seconds = divmod(int(remaining.total_seconds()), 3600)
            minutes = seconds // 60
            await interaction.response.send_message(
                f"⏳ You can claim again in **{hours} hours {minutes} minutes**.",
                ephemeral=True,
            )
            return
        added = safe_add_coins(user_id, DAILY_REWARD)
        set_last_claim(user_id, now)
        if added > 0:
            await interaction.response.send_message(
                f"✅ {added} Coins added! You now have **{get_money(user_id)}** 💰.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "⚠️ Server coin limit reached. No daily coins could be added.",
                ephemeral=True,
            )

    @bot.tree.command(
        name="superpower",
        description="Roll a random superpower for 80k coins (24 h cooldown)",
    )
    async def superpower(interaction: discord.Interaction):
        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        balance = get_money(uid)
        if balance < SUPERPOWER_COST:
            await interaction.response.send_message(
                f"❌ You need {SUPERPOWER_COST} coins.", ephemeral=True
            )
            return
        now = datetime.utcnow()
        last = get_timestamp(uid, "last_superpower")
        if last and now - last < timedelta(hours=SUPERPOWER_COOLDOWN_HOURS):
            remain = timedelta(hours=SUPERPOWER_COOLDOWN_HOURS) - (now - last)
            hrs, sec = divmod(int(remain.total_seconds()), 3600)
            mins = sec // 60
            await interaction.response.send_message(
                f"🕒 Next roll in {hrs}h {mins}m.", ephemeral=True
            )
            return
        set_money(uid, balance - SUPERPOWER_COST)
        rarities = [
            ("Crappy-power", 0.40),
            ("Somewhat useful", 0.30),
            ("That's decent", 0.15),
            ("Damn you're almost as cool as Anonym", 0.10),
            ("Legendary (Anonym level power)", 0.05),
        ]
        roll = random()
        cumulative = 0.0
        rarity = rarities[-1][0]
        for name, weight in rarities:
            cumulative += weight
            if roll < cumulative:
                rarity = name
                break
        powers = {
            "Crappy-power": [
                "Make water slightly colder",
                "Summon a single mosquito",
                "Change TV to channel 3",
                "Emit a faint squeak",
                "Teleport two inches",
                "Turn coffee lukewarm",
            ],
            "Somewhat useful": [
                "Find missing socks",
                "Instantly dry small puddles",
                "Talk to houseplants",
                "Always win at rock-paper-scissors",
                "Keep cookies from burning",
                "See through fog",
            ],
            "That's decent": [
                "Predict tomorrow's weather",
                "Phase through glass",
                "Supercharged jump",
                "Create short-lived force fields",
                "Control flavor of water",
                "Recharge batteries by touch",
            ],
            "Damn you're almost as cool as Anonym": [
                "Invisibility for ten seconds",
                "Time-skip one minute",
                "Summon digital clones",
                "Reverse gravity on objects",
                "Superhuman reflexes",
                "Mind-link with animals",
            ],
            "Legendary (Anonym level power)": [
                "Teleport anywhere instantly",
                "Command the elements",
                "Stop time briefly",
                "Heal any injury",
                "Alter reality",
                "Immortal resilience",
            ],
        }
        power = choice(powers[rarity])
        set_timestamp(uid, "last_superpower", now)

        role_name = f"{power} ({rarity})"
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            try:
                role = await guild.create_role(
                    name=role_name, reason="Superpower reward"
                )
            except discord.Forbidden:
                role = None
        if role:
            try:
                await interaction.user.add_roles(role, reason="Rolled superpower")
            except discord.Forbidden:
                pass

        await interaction.response.send_message(
            f"{interaction.user.display_name} rolled **{power}**! ({rarity})"
        )

    @bot.tree.command(
        name="animetitle",
        description=(
            "Roll a random anime character title. Rerolls cost 10% of your"
            " coins (minimum 500k)."
        ),
    )
    async def animetitle(interaction: discord.Interaction):
        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        guild = interaction.guild

        titles = [
            "The Black Swordsman (Guts - Berserk)",
            "Pirate King (Monkey D. Luffy - One Piece)",
            "Hokage (Naruto Uzumaki - Naruto)",
            "Symbol of Peace (All Might - My Hero Academia)",
            "Titan Slayer (Mikasa Ackerman - Attack on Titan)",
            "Fullmetal Alchemist (Edward Elric - FMA)",
            "Soul Reaper (Ichigo Kurosaki - Bleach)",
            "Dragon of the Darkness Flame (Hiei - Yu Yu Hakusho)",
            "King of Games (Yugi Muto - Yu-Gi-Oh!)",
            "Master of the Cursed Energy (Satoru Gojo - Jujutsu Kaisen)",
            "Ghoul Investigator (Ken Kaneki - Tokyo Ghoul)",
            "Flame Hashira (Kyojuro Rengoku - Demon Slayer)",
            "Spirit Detective (Yusuke Urameshi - Yu Yu Hakusho)",
            "Seventh Hokage (Naruto Uzumaki - Naruto)",
            "Blue Exorcist (Rin Okumura - Blue Exorcist)",
            "The Railgun (Mikoto Misaka - Index)",
            "Toon Sorcerer (Asta - Black Clover)",
            "Goddess of Death (Ryuk - Death Note)",
            "Ultra Instinct (Goku - Dragon Ball)",
            "Straw Hat (Monkey D. Luffy - One Piece)",
            "Red-Haired Emperor (Shanks - One Piece)",
            "Flame Alchemist (Roy Mustang - FMA)",
            "Blue-Haired Swordsman (Kirito - SAO)",
            "Magical Girl (Madoka Kaname - Madoka Magica)",
            "Vampire Queen (Seras Victoria - Hellsing)",
            "Wandering Samurai (Kenshin Himura - Rurouni Kenshin)",
            "Esper Ace (Tatsumaki - One Punch Man)",
            "Cyborg Hero (Genos - One Punch Man)",
            "Gurren Pilot (Simon - Gurren Lagann)",
            "Absolute Sword (Yuuki - SAO)",
            "Ninja President (Boruto - Naruto)",
            "Blue Flame Dragon (Shoto Todoroki - MHA)",
            "White Reaper (Toshiro Hitsugaya - Bleach)",
            "Lightning Beast (Killua Zoldyck - Hunter x Hunter)",
            "Chimera King (Meruem - Hunter x Hunter)",
            "Fire Fist (Portgas D. Ace - One Piece)",
            "Copy Ninja (Kakashi Hatake - Naruto)",
            "Quinx Leader (Haise Sasaki - Tokyo Ghoul:re)",
            "Shadow Monarch (Sung Jin-Woo - Solo Leveling)",
            "Red Comet (Char Aznable - Gundam)",
            "Demon Queen (Milim Nava - Slime)",
            "The Strongest Hero (Saitama - One Punch Man)",
            "Dragon Maid (Tohru - Miss Kobayashi's Dragon Maid)",
            "Card Master (Sakura Kinomoto - Cardcaptor Sakura)",
            "Angel of Death (Lucy - Elfen Lied)",
            "Sword Saint (Saber - Fate)",
            "Ice Devil (Gray Fullbuster - Fairy Tail)",
            "Black Clover Wizard (Asta - Black Clover)",
            "Violet Evergarden (Violet - Violet Evergarden)",
            "Magic Emperor (Yami Sukehiro - Black Clover)",
            "Chunin Prodigy (Shikamaru Nara - Naruto)",
            "Water Pillar (Giyu Tomioka - Demon Slayer)",
            "Great Saiyaman (Gohan - Dragon Ball) ",
            "Death Scythe (Maka Albarn - Soul Eater)",
            "Goddess Reborn (Aqua - Konosuba)",
            "Supreme Kai (Shin - Dragon Ball Z)",
            "Pro-Hero Rookie (Izuku Midoriya - MHA)",
            "Demon Barber (Grell Sutcliff - Black Butler)",
            "Lord Frieza (Frieza - Dragon Ball Z)",
            "Time Wizard (Jotaro Kujo - JoJo)",
            "Galaxy Police (Kiyone - Tenchi Muyo)",
            "The Violet Devil (Shinobu Kocho - Demon Slayer)",
            "Lucky Master (Rintarou Okabe - Steins;Gate)",
            "Devil Hunter (Denji - Chainsaw Man)",
            "Magic Knight (Lelouch Lamperouge - Code Geass)",
            "Black Reaper (Hei - Darker than Black)",
            "Metal Alchemist (Alphonse Elric - FMA)",
            "Pink Shinobi (Sakura Haruno - Naruto)",
            "Ghost Princess (Perona - One Piece)",
            "Spirit Gunner (Yusuke Urameshi - Yu Yu Hakusho)",
            "Speedwagon Foundation (Robert E.O. Speedwagon - JoJo)",
            "Hero of Justice (Emiya Shirou - Fate/Stay Night)",
            "Maiden of Rebirth (Neon Genesis Evangelion - Rei Ayanami)",
            "Trickster Mage (Megumin - Konosuba)",
            "Silent Swordsman (Zoro - One Piece)",
            "Flower Hashira (Shinobu Kocho - Demon Slayer)",
            "Black Bull Captain (Yami Sukehiro - Black Clover)",
            "Fairy Queen (Titania Erza - Fairy Tail)",
            "Kitsune Illusionist (Kurama - Naruto)",
            "Wing Hero (Hawks - MHA)",
            "Red Riot (Eijiro Kirishima - MHA)",
            "Metal Knight (Genos - One Punch Man)",
            "Storm Dragon (Veldora - Slime)",
            "Goddess of War (Valkyrie Brunhilde - Record of Ragnarok)",
            "Demon Sister (Satella - Re:Zero)",
            "Gun Gale Shooter (Sinon - SAO)",
            "Railgun Ace (Accelerator - Index)",
            "Moon Princess (Usagi Tsukino - Sailor Moon)",
            "Genius Hacker (Kaminari Denki - MHA)",
            "Shinigami Prince (Sebastian Michaelis - Black Butler)",
            "Sun Breather (Tanjiro Kamado - Demon Slayer)",
            "Psycho Soldier (Mob - Mob Psycho 100)",
            "Spirit Fox (Shippo - Inuyasha)",
            "Homunculus Survivor (Riza Hawkeye - FMA)",
            "Chaos Swordsman (Inosuke Hashibira - Demon Slayer)",
            "Wind Master (Kazuma - Konosuba)",
            "Queen's Blade (Esdeath - Akame ga Kill!)",
            "Golem Rider (Noelle Silva - Black Clover)",
            "The Other One (Rem - Re:Zero)",
            "Zero's Successor (Kamijo Touma - Index)",
            "Machine God (Diane - Seven Deadly Sins)",
            "Shield Hero (Naofumi Iwatani - Shield Hero)",
            "Stone World Genius (Senku Ishigami - Dr. Stone)",
            "Night Raid Assassin (Akame - Akame ga Kill!)",
            "Pudding Princess (Pudding - One Piece)",
            "Spiral Warrior (Kamina - Gurren Lagann)",
            "Endless Swords (Archer - Fate)",
            "Ice Queen (Esdeath - Akame ga Kill!)",
            "Dreaming Detective (Conan Edogawa - Detective Conan)",
            "NerveGear Survivor (Asuna - SAO)",
            "Goddess of Victory (Bishamon - Noragami)",
            "Martial Artist (Baki Hanma - Baki)",
            "Netherworld Butler (Sebastian - Black Butler)",
            "Alchemist Hunter (Scar - FMA)",
            "Holy Maiden (Jeanne d'Arc - Fate/Apocrypha)",
            "Magic Swordsman (Ragna - Ragna Crimson)",
            "The Great Wizard (Merlin - Seven Deadly Sins)",
            "Saiyan Prince (Vegeta - Dragon Ball Z)",
            "Crystal Sorceress (Juvia Lockser - Fairy Tail)",
            "Revived Hero (Meliodas - Seven Deadly Sins)",
        ]

        current = get_anime_title(uid)
        balance = get_money(uid)

        if current:
            cost = max(int(balance * 0.1), 500_000)
            if balance < cost:
                await interaction.response.send_message(
                    f"❌ You need {cost} coins to change your title.",
                    ephemeral=True,
                )
                return
            set_money(uid, balance - cost)
            role = discord.utils.get(guild.roles, name=current)
            if role:
                try:
                    await interaction.user.remove_roles(role, reason="Anime title reroll")
                except discord.Forbidden:
                    pass

        title = choice(titles)
        role = discord.utils.get(guild.roles, name=title)
        if role is None:
            try:
                role = await guild.create_role(name=title, reason="Anime title reward")
            except discord.Forbidden:
                role = None
        if role:
            try:
                await interaction.user.add_roles(role, reason="Anime title reward")
            except discord.Forbidden:
                pass
        set_anime_title(uid, title)

        await interaction.response.send_message(
            f"{interaction.user.display_name} received the title **{title}**!"
        )

    @bot.tree.command(
        name="gamble", description="Gamble your coins for a chance to win more!"
    )
    async def gamble(interaction: discord.Interaction, amount: int):
        user_id = str(interaction.user.id)
        register_user(user_id, interaction.user.display_name)
        if amount < 2:
            await interaction.response.send_message(
                "🎲 Minimum bet is 2 clubhall coins.", ephemeral=True
            )
            return
        balance = get_money(user_id)
        if amount > balance:
            await interaction.response.send_message(
                "❌ You don't have enough clubhall coins!", ephemeral=True
            )
            return
        await interaction.response.send_message(
            "🎲 Rolling the dice...", ephemeral=False
        )
        await asyncio.sleep(2)
        roll = random()
        if roll < 0.05:
            multiplier = 3
            message = "💎 JACKPOT! 3x WIN!"
        elif roll < 0.30:
            multiplier = 2
            message = "🔥 Double win!"
        elif roll < 0.60:
            multiplier = 1
            message = "😐 You broke even."
        else:
            multiplier = 0
            message = "💀 You lost everything..."
        new_amount = amount * multiplier
        set_money(user_id, balance - amount + new_amount)
        emoji_result = {3: "💎", 2: "🔥", 1: "😐", 0: "💀"}
        await interaction.edit_original_response(
            content=(
                f"{emoji_result[multiplier]} **{interaction.user.display_name}**, you bet **{amount}** coins.\n"
                f"{message}\n"
                f"You now have **{get_money(user_id)}** clubhall coins."
            )
        )

    @bot.tree.command(name="casino", description="pay to win")
    @app_commands.describe(bet="How much you want to bet")
    async def casino(inter: discord.Interaction, bet: int):
        uid = str(inter.user.id)
        register_user(uid, inter.user.display_name)
        balance = get_money(uid)
        if bet <= 0:
            await inter.response.send_message(
                "❌ Try number more than 0", ephemeral=True
            )
        if bet > balance:
            await inter.response.send_message("❌ Not enough coins.", ephemeral=True)
            return
        if random() > 0.5:
            set_money(uid, balance + bet)
            await inter.response.send_message(
                f"🎉 Congratulation! You won {bet} clubhall coins."
            )
            return
        set_money(uid, balance - bet)
        await inter.response.send_message(
            f"❌ Congratulation! You lose {bet} clubhall coins."
        )
        return

    @bot.tree.command(
        name="duel",
        description="Challenge another player to rock-paper-scissors for coins",
    )
    @app_commands.describe(bet="How many coins to wager")
    async def duel(
        interaction: discord.Interaction, opponent: discord.Member, bet: int
    ):
        if opponent.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't duel yourself.", ephemeral=True
            )
            return
        challenger_id = str(interaction.user.id)
        opponent_id = str(opponent.id)
        register_user(challenger_id, interaction.user.display_name)
        register_user(opponent_id, opponent.display_name)
        challenger_balance = get_money(challenger_id)
        if bet <= 0:
            await interaction.response.send_message(
                "Bet must be greater than 0.", ephemeral=True
            )
            return
        if bet > challenger_balance:
            await interaction.response.send_message(
                "You don't have enough coins.", ephemeral=True
            )
            return
        view = DuelRequestView(interaction.user.id, opponent.id, bet)
        await interaction.response.send_message(
            f"{opponent.mention}, {interaction.user.display_name} challenges you to a duel for **{bet}** coins!",
            view=view,
        )

    @bot.tree.command(name="blackjack", description="Play blackjack against the bot")
    @app_commands.describe(bet="How much you want to bet")
    async def blackjack(interaction: discord.Interaction, bet: int):
        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        balance = get_money(uid)
        if bet <= 0:
            await interaction.response.send_message(
                "❌ Bet must be greater than 0.", ephemeral=True
            )
            return
        if bet > balance:
            await interaction.response.send_message(
                "❌ Not enough coins.", ephemeral=True
            )
            return
        view = BlackjackView(interaction.user.id, bet)
        await interaction.response.send_message(view._render(), view=view)
        view.message = await interaction.original_response()

    @bot.tree.command(name="poker", description="Multiplayer Texas Hold'em style poker")
    @app_commands.describe(bet="Coins each player wagers")
    async def poker(interaction: discord.Interaction, bet: int):
        uid = str(interaction.user.id)
        register_user(uid, interaction.user.display_name)
        if bet <= 0:
            await interaction.response.send_message(
                "Bet must be greater than 0.", ephemeral=True
            )
            return
        if get_money(uid) < bet:
            await interaction.response.send_message(
                "Not enough coins.", ephemeral=True
            )
            return
        view = PokerJoinView(bot, interaction.user.id, bet)
        view.players[interaction.user.id] = interaction.user.display_name
        await interaction.response.send_message(view.render(), view=view)
        view.message = await interaction.original_response()

    return (
        money,
        balance,
        give,
        remove,
        donate,
        setlimit,
        request,
        topcoins,
        weekly,
        daily,
        superpower,
        animetitle,
        gamble,
        casino,
        duel,
        blackjack,
        poker,
    )
