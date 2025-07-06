DB_PATH = "users.db"
ADMIN_ROLE_ID = 1351479405699928108
MOD_ROLE_ID = 1352179673374916691
SHEHER_ROLE_ID = 1351546875492302859
HEHIM_ROLE_ID = 1351546766855634984
CHANNEL_LOCK_ROLE_ID = 1356577214325460992
MAX_COINS = 9223372036854775807
DAILY_REWARD = 20
WELCOME_CHANNEL_ID = 1351487186557734942
LOG_CHANNEL_ID = 1364226902289813514
STAT_PRICE = 66
QUEST_COOLDOWN_HOURS = 3
FISHING_COOLDOWN_MINUTES = 30
WEEKLY_REWARD = 50
SUPERPOWER_COST = 80_000
SUPERPOWER_COOLDOWN_HOURS = 24
STAT_NAMES = ["intelligence", "strength", "stealth"]
import re

TRIGGER_RESPONSES = {
    re.compile(r"(?i)t[\W_]*[a4@][\W_]*[o0][\W_]*m[\W_]*[a4@]"): (
        "Our beautiful majestic Emperor TAOMA™! Long live our beloved King 👑"
    ),
    re.compile(r"(?i)シャドウ.?ストーム"): (
        "Our beautiful majestic Emperor シャドウストーム! Long live our beloved King 👑"
    ),
    re.compile(r"(?i)goodyb"): (
        "Our beautiful majestic Emperor goodyb! Long live our beloved King 👑"
    ),
}

ROLE_THRESHOLDS = {
    "intelligence": ("Neuromancer", 50),
    "strength": ("Warriour", 100),
    "stealth": ("Ninja", 100),
}
