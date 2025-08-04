import sqlite3
from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    def _recreate(table: str, create_sql: str, required_cols: set[str]):
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {col[1] for col in cursor.fetchall()}
        if not existing or not required_cols.issubset(existing):
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            cursor.execute(create_sql)

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

    _recreate(
        "server",
        """
        CREATE TABLE IF NOT EXISTS server (
            guild_id TEXT PRIMARY KEY,
            welcome_channel_id TEXT,
            leave_channel_id TEXT,
            welcome_message TEXT,
            leave_message TEXT,
            booster_channel_id TEXT,
            booster_message TEXT,
            log_channel_id TEXT
        )
        """,
        {
            "guild_id",
            "welcome_channel_id",
            "leave_channel_id",
            "welcome_message",
            "leave_message",
            "booster_channel_id",
            "booster_message",
            "log_channel_id",
        },
    )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS shop_roles (
        role_id     TEXT PRIMARY KEY,
        price       INTEGER NOT NULL
    )
    """
    )
    _recreate(
        "roles",
        """
        CREATE TABLE IF NOT EXISTS roles (
            guild_id TEXT,
            name     TEXT,
            role_id  TEXT,
            PRIMARY KEY (guild_id, name)
        )
        """,
        {"guild_id", "name", "role_id"},
    )
    _recreate(
        "command_permissions",
        """
        CREATE TABLE IF NOT EXISTS command_permissions (
            guild_id TEXT,
            command TEXT,
            role_id TEXT,
            PRIMARY KEY (guild_id, command)
        )
        """,
        {"guild_id", "command", "role_id"},
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

    cursor.execute("PRAGMA table_info(dates)")
    columns = {col[1] for col in cursor.fetchall()}
    if "registered_date" not in columns:
        cursor.execute("ALTER TABLE dates ADD COLUMN registered_date TEXT")

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

    _recreate(
        "filtered_words",
        """
        CREATE TABLE IF NOT EXISTS filtered_words (
            guild_id TEXT,
            word TEXT,
            PRIMARY KEY (guild_id, word)
        )
        """,
        {"guild_id", "word"},
    )

    _recreate(
        "trigger_responses",
        """
        CREATE TABLE IF NOT EXISTS trigger_responses (
            guild_id TEXT,
            trigger TEXT,
            response TEXT NOT NULL,
            PRIMARY KEY (guild_id, trigger)
        )
        """,
        {"guild_id", "trigger", "response"},
    )

    _recreate(
        "anti_nuke_settings",
        """
        CREATE TABLE IF NOT EXISTS anti_nuke_settings (
            guild_id TEXT,
            category TEXT,
            enabled INTEGER DEFAULT 0,
            threshold INTEGER DEFAULT 1,
            punishment TEXT DEFAULT 'kick',
            duration INTEGER,
            PRIMARY KEY (guild_id, category)
        )
        """,
        {"guild_id", "category", "enabled", "threshold", "punishment", "duration"},
    )

    _recreate(
        "anti_nuke_safe_users",
        """
        CREATE TABLE IF NOT EXISTS anti_nuke_safe_users (
            guild_id TEXT,
            user_id TEXT,
            PRIMARY KEY (guild_id, user_id)
        )
        """,
        {"guild_id", "user_id"},
    )

    _recreate(
        "anti_nuke_safe_roles",
        """
        CREATE TABLE IF NOT EXISTS anti_nuke_safe_roles (
            guild_id TEXT,
            role_id TEXT,
            PRIMARY KEY (guild_id, role_id)
        )
        """,
        {"guild_id", "role_id"},
    )

    _recreate(
        "anti_nuke_log_channel",
        """
        CREATE TABLE IF NOT EXISTS anti_nuke_log_channel (
            guild_id TEXT PRIMARY KEY,
            channel_id TEXT
        )
        """,
        {"guild_id", "channel_id"},
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
