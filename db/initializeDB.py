import sqlite3
from config import DB_PATH, MAX_COINS


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(dates)")
    columns = {col[1] for col in cursor.fetchall()}
    if "registered_date" not in columns:
        cursor.execute("ALTER TABLE dates ADD COLUMN registered_date TEXT")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            money INTEGER DEFAULT 0,
            last_claim TEXT,
            last_quest TEXT,
            stat_points INTEGER DEFAULT 0,
            intelligence INTEGER DEFAULT 1,
            strength INTEGER DEFAULT 1,
            stealth INTEGER DEFAULT 1
        )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS reaction_roles (
        message_id TEXT,
        emoji TEXT,
        role_id TEXT,
        PRIMARY KEY (message_id, emoji)
    )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS server (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            max_coins INTEGER
        )
    """
    )
    cursor.execute("SELECT max_coins FROM server WHERE id = 1")
    row = cursor.fetchone()

    if row is None:
        cursor.execute(
            "INSERT INTO server (id, max_coins) VALUES (?, ?)",
            (1, MAX_COINS),
        )
    elif row[0] < MAX_COINS:
        cursor.execute(
            "UPDATE server SET max_coins = ? WHERE id = 1",
            (MAX_COINS,),
        )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS shop_roles (
        role_id     TEXT PRIMARY KEY,
        price       INTEGER NOT NULL
    )
    """
    )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS fishing_rods (
        user_id TEXT PRIMARY KEY,
        rod_level INTEGER DEFAULT 0
    )
    """
    )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS rod_shop (
        level INTEGER PRIMARY KEY,
        price INTEGER NOT NULL,
        multiplier REAL NOT NULL
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS custom_roles (
        user_id TEXT PRIMARY KEY,
        role_id TEXT NOT NULL
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS anime_titles (
        user_id TEXT PRIMARY KEY,
        role_name TEXT NOT NULL
    )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dates (
            user_id TEXT PRIMARY KEY,
            registered_date TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS giveaways (
            message_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            end_time TEXT,
            prize TEXT,
            winners INTEGER,
            finished INTEGER DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS filtered_words (
            word TEXT PRIMARY KEY
        )
        """
    )

    cursor.execute("PRAGMA table_info(users)")
    existing = {col[1] for col in cursor.fetchall()}
    for col, default in [
        ("last_quest", ""),
        ("last_fishing", ""),
        ("last_superpower", ""),
        ("stat_points", 0),
        ("last_weekly", ""),
        ("intelligence", 1),
        ("strength", 1),
        ("stealth", 1),
    ]:
        if col not in existing:
            if col in ("last_quest", "last_weekly", "last_fishing", "last_superpower"):
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
            else:
                cursor.execute(
                    f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT {default}"
                )

    conn.commit()
    conn.close()
