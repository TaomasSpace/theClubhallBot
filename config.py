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


ROD_SHOP: dict[int, tuple[int, float]] = {
    1: (500, 1.50),
    2: (1_200, 1.80),
    3: (2_800, 2.10),
    4: (6_000, 2.40),
    5: (12_500, 2.70),
    6: (26_000, 3.00),
    7: (55_000, 3.30),
    8: (120_000, 3.60),
    9: (250_000, 3.90),
    10: (520_000, 4.20),
    11: (1_100_000, 4.50),
    12: (2_300_000, 4.80),
    13: (4_800_000, 5.10),
    14: (10_000_000, 5.40),
    15: (21_000_000, 5.70),
    16: (45_000_000, 6.00),
    17: (95_000_000, 6.30),
    18: (200_000_000, 6.60),
    19: (420_000_000, 6.90),
    20: (900_000_000, 7.20),
}
