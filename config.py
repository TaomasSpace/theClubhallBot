DB_PATH = "users.db"
DAILY_REWARD = 20
STAT_PRICE = 66
QUEST_COOLDOWN_HOURS = 3
FISHING_COOLDOWN_MINUTES = 30
WEEKLY_REWARD = 50
SUPERPOWER_COST = 80_000
SUPERPOWER_COOLDOWN_HOURS = 24
STAT_NAMES = ["intelligence", "strength", "stealth"]

ROLE_THRESHOLDS = {
    "intelligence": ("Neuromancer", 50),
    "strength": ("Warriour", 100),
    "stealth": ("Ninja", 100),
}

# Fixed fishing rod shop: level -> (price, multiplier)
# Edit these values to change available rods.
ROD_SHOP: dict[int, tuple[int, float]] = {
    1: (500, 1.10),
    2: (2500, 1.25),
    3: (10000, 1.50),
    4: (35000, 1.75),
    5: (100000, 2.00),
}
