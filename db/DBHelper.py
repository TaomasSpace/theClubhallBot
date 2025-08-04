import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from config import DB_PATH, STAT_NAMES


def _fetchone(query: str, params=()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return row


def _execute(query: str, params=()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()


# ---------- user registration ----------

def register_user(user_id: str, username: str):
    user_exists = _fetchone("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if user_exists:
        _execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    else:
        _execute(
            "INSERT INTO users (user_id, username, money) VALUES (?,?,?)",
            (user_id, username, 5),
        )
    if not _fetchone("SELECT 1 FROM dates WHERE user_id = ?", (user_id,)):
        _execute(
            "INSERT INTO dates (user_id, registered_date) VALUES (?,?)",
            (user_id, str(datetime.now(timezone.utc))),
        )


# ---------- coins ----------

def get_rod_multiplier(level: int) -> float:
    row = _fetchone("SELECT multiplier FROM rod_shop WHERE level = ?", (level,))
    return row[0] if row else 1.0


def get_money(user_id: str) -> int:
    row = _fetchone("SELECT money FROM users WHERE user_id = ?", (user_id,))
    return row[0] if row else 0


def set_money(user_id: str, amount: int):
    _execute("UPDATE users SET money = ? WHERE user_id = ?", (amount, user_id))


def safe_add_coins(user_id: str, amount: int) -> int:
    if amount <= 0:
        return 0

    current_total = get_total_money()
    max_total = get_max_coins()
    free_space = max_total - current_total

    if free_space <= 0:
        return 0

    addable = min(amount, free_space)
    old_balance = get_money(user_id)
    set_money(user_id, old_balance + addable)
    return addable


def add_rod_to_shop(level: int, price: int, multiplier: float):
    _execute(
        "INSERT OR REPLACE INTO rod_shop (level, price, multiplier) VALUES (?, ?, ?)",
        (level, price, multiplier),
    )


def get_all_rods_from_shop() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT level, price, multiplier FROM rod_shop")
    rows = cursor.fetchall()
    conn.close()
    return {level: (price, multiplier) for level, price, multiplier in rows}


def get_total_money():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(money) FROM users")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result[0] else 0


def get_top_users(limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, money FROM users ORDER BY money DESC LIMIT ?", (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_last_claim(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT last_claim FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row and row[0] else None


def set_last_claim(user_id: str, ts: datetime):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_claim = ? WHERE user_id = ?", (ts.isoformat(), user_id)
    )
    conn.commit()
    conn.close()


# ---------- stats & stat‑points ----------

def get_stats(user_id: str):
    row = _fetchone(
        "SELECT intelligence, strength, stealth, stat_points FROM users WHERE user_id = ?",
        (user_id,),
    )
    if not row:
        return {s: 1 for s in STAT_NAMES} | {"stat_points": 0}
    return dict(zip(STAT_NAMES + ["stat_points"], row))


def add_stat_points(user_id: str, delta: int):
    _execute(
        "UPDATE users SET stat_points = stat_points + ? WHERE user_id = ?",
        (delta, user_id),
    )


def increase_stat(user_id: str, stat: str, amount: int):
    if stat not in STAT_NAMES:
        raise ValueError("invalid stat")
    _execute(
        f"UPDATE users SET {stat} = {stat} + ?, stat_points = stat_points - ? WHERE user_id = ?",
        (amount, amount, user_id),
    )


def get_rod_level(user_id: str) -> int:
    row = _fetchone("SELECT rod_level FROM fishing_rods WHERE user_id = ?", (user_id,))
    return row[0] if row else 0


def set_rod_level(user_id: str, level: int):
    if _fetchone("SELECT 1 FROM fishing_rods WHERE user_id = ?", (user_id,)):
        _execute(
            "UPDATE fishing_rods SET rod_level = ? WHERE user_id = ?", (level, user_id)
        )
    else:
        _execute(
            "INSERT INTO fishing_rods (user_id, rod_level) VALUES (?, ?)",
            (user_id, level),
        )


# ---------- timing helpers ----------

def get_timestamp(user_id: str, column: str):
    row = _fetchone(f"SELECT {column} FROM users WHERE user_id = ?", (user_id,))
    return datetime.fromisoformat(row[0]) if row and row[0] else None


def set_timestamp(user_id: str, column: str, ts: datetime):
    _execute(
        f"UPDATE users SET {column} = ? WHERE user_id = ?", (ts.isoformat(), user_id)
    )


def get_last_weekly(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT last_weekly FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row and row[0] else None


def set_last_weekly(user_id: str, ts: datetime):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_weekly = ? WHERE user_id = ?", (ts.isoformat(), user_id)
    )
    conn.commit()
    conn.close()


# ---------- server helpers ----------

def get_max_coins():
    return _fetchone("SELECT max_coins FROM server WHERE id = 1")[0]


def set_max_coins(limit: int):
    _execute("UPDATE server SET max_coins = ? WHERE id = 1", (limit,))


# ---------- shop helpers ----------

def add_shop_role(role_id: int, price: int):
    _execute(
        "INSERT OR REPLACE INTO shop_roles (role_id, price) VALUES (?,?)",
        (role_id, price),
    )


def remove_shop_role(role_id: int):
    _execute("DELETE FROM shop_roles WHERE role_id = ?", (role_id,))


def get_shop_roles():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role_id, price FROM shop_roles")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_custom_role(user_id: str):
    row = _fetchone("SELECT role_id FROM custom_roles WHERE user_id = ?", (user_id,))
    return int(row[0]) if row else None


def set_custom_role(user_id: str, role_id: int):
    _execute(
        "INSERT OR REPLACE INTO custom_roles (user_id, role_id) VALUES (?, ?)",
        (user_id, role_id),
    )


def delete_custom_role(user_id: str):
    _execute("DELETE FROM custom_roles WHERE user_id = ?", (user_id,))


# ---------- anime title helpers ----------

def get_anime_title(user_id: str):
    row = _fetchone("SELECT role_name FROM anime_titles WHERE user_id = ?", (user_id,))
    return row[0] if row else None


def set_anime_title(user_id: str, role_name: str):
    _execute(
        "INSERT OR REPLACE INTO anime_titles (user_id, role_name) VALUES (?, ?)",
        (user_id, role_name),
    )


def delete_anime_title(user_id: str):
    _execute("DELETE FROM anime_titles WHERE user_id = ?", (user_id,))


# ---------- giveaway helpers ----------

def create_giveaway(
    message_id: str, channel_id: str, end_time: datetime, prize: str, winners: int
):
    _execute(
        "INSERT OR REPLACE INTO giveaways (message_id, channel_id, end_time, prize, winners, finished) VALUES (?, ?, ?, ?, ?, 0)",
        (message_id, channel_id, end_time.isoformat(), prize, winners),
    )


def finish_giveaway(message_id: str):
    _execute("UPDATE giveaways SET finished = 1 WHERE message_id = ?", (message_id,))


def get_active_giveaways():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT message_id, channel_id, end_time, prize, winners FROM giveaways WHERE finished = 0"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_date(user_id: str, name: str):
    if _fetchone("SELECT * FROM dates WHERE user_id = ?", (user_id,)):
        _execute(
            "UPDATE dates SET registered_date  = ? WHERE user_id = ?",
            (
                str(datetime.now(timezone.utc)),
                user_id,
            ),
        )
    else:
        register_user(user_id, name)


def get_lastdate(user_id: str):
    row = _fetchone("SELECT registered_date FROM dates WHERE user_id = ?", (user_id,))
    return row[0] if row else "No date found"


# ---------- filtered words helpers ----------

def add_filtered_word(word: str):
    _execute(
        "INSERT OR IGNORE INTO filtered_words (word) VALUES (?)",
        (word.lower(),),
    )


def remove_filtered_word(word: str):
    _execute("DELETE FROM filtered_words WHERE word = ?", (word.lower(),))


def get_filtered_words() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM filtered_words")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


# ---------- trigger response helpers ----------

def add_trigger_response(trigger: str, response: str):
    _execute(
        "INSERT OR REPLACE INTO trigger_responses (trigger, response) VALUES (?, ?)",
        (trigger.lower(), response),
    )


def remove_trigger_response(trigger: str):
    _execute("DELETE FROM trigger_responses WHERE trigger = ?", (trigger.lower(),))


def get_trigger_responses() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT trigger, response FROM trigger_responses")
    rows = cursor.fetchall()
    conn.close()
    return {trigger: response for trigger, response in rows}

# ---------- anti nuke helpers ----------

def get_anti_nuke_setting(category: str) -> Optional[Tuple[int, int, str, Optional[int]]]:

    row = _fetchone(
        "SELECT enabled, threshold, punishment, duration FROM anti_nuke_settings WHERE category = ?",
        (category,),
    )
    return row if row else None


def set_anti_nuke_setting(
    category: str, enabled: int, threshold: int, punishment: str, duration: Optional[int]

) -> None:
    _execute(
        "INSERT OR REPLACE INTO anti_nuke_settings (category, enabled, threshold, punishment, duration) VALUES (?, ?, ?, ?, ?)",
        (category, enabled, threshold, punishment, duration),
    )


def add_safe_user(uid: int) -> None:
    _execute(
        "INSERT OR IGNORE INTO anti_nuke_safe_users (user_id) VALUES (?)",
        (str(uid),),
    )


def remove_safe_user(uid: int) -> None:
    _execute("DELETE FROM anti_nuke_safe_users WHERE user_id = ?", (str(uid),))


def get_safe_users() -> List[int]:

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM anti_nuke_safe_users")
    rows = cursor.fetchall()
    conn.close()
    return [int(r[0]) for r in rows]


def add_safe_role(rid: int) -> None:
    _execute(
        "INSERT OR IGNORE INTO anti_nuke_safe_roles (role_id) VALUES (?)",
        (str(rid),),
    )


def remove_safe_role(rid: int) -> None:
    _execute("DELETE FROM anti_nuke_safe_roles WHERE role_id = ?", (str(rid),))


def get_safe_roles() -> List[int]:

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role_id FROM anti_nuke_safe_roles")
    rows = cursor.fetchall()
    conn.close()
    return [int(r[0]) for r in rows]


def set_anti_nuke_log_channel(cid: int) -> None:
    _execute(
        "INSERT OR REPLACE INTO anti_nuke_log_channel (channel_id) VALUES (?)",
        (str(cid),),
    )


def get_anti_nuke_log_channel() -> Optional[int]:
    row = _fetchone("SELECT channel_id FROM anti_nuke_log_channel LIMIT 1")
    return int(row[0]) if row else None

