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
    old_balance = get_money(user_id)
    set_money(user_id, old_balance + amount)
    return amount


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


def _set_guild_value(guild_id: int, column: str, value: Optional[str]) -> None:
    _execute(
        f"INSERT INTO server (guild_id, {column}) VALUES (?, ?) "
        f"ON CONFLICT(guild_id) DO UPDATE SET {column}=excluded.{column}",
        (str(guild_id), value),
    )


def _get_guild_value(guild_id: int, column: str) -> Optional[str]:
    row = _fetchone(
        f"SELECT {column} FROM server WHERE guild_id = ?",
        (str(guild_id),),
    )
    return row[0] if row and row[0] else None


def set_welcome_channel(guild_id: int, cid: int) -> None:
    _set_guild_value(guild_id, "welcome_channel_id", str(cid))


def get_welcome_channel(guild_id: int) -> Optional[int]:
    val = _get_guild_value(guild_id, "welcome_channel_id")
    return int(val) if val else None


def set_leave_channel(guild_id: int, cid: int) -> None:
    _set_guild_value(guild_id, "leave_channel_id", str(cid))


def get_leave_channel(guild_id: int) -> Optional[int]:
    val = _get_guild_value(guild_id, "leave_channel_id")
    return int(val) if val else None


def set_welcome_message(guild_id: int, msg: str) -> None:
    _set_guild_value(guild_id, "welcome_message", msg)


def get_welcome_message(guild_id: int) -> Optional[str]:
    return _get_guild_value(guild_id, "welcome_message")


def set_leave_message(guild_id: int, msg: str) -> None:
    _set_guild_value(guild_id, "leave_message", msg)


def get_leave_message(guild_id: int) -> Optional[str]:
    return _get_guild_value(guild_id, "leave_message")


def set_booster_channel(guild_id: int, cid: int) -> None:
    _set_guild_value(guild_id, "booster_channel_id", str(cid))


def get_booster_channel(guild_id: int) -> Optional[int]:
    val = _get_guild_value(guild_id, "booster_channel_id")
    return int(val) if val else None


def set_booster_message(guild_id: int, msg: str) -> None:
    _set_guild_value(guild_id, "booster_message", msg)


def get_booster_message(guild_id: int) -> Optional[str]:
    return _get_guild_value(guild_id, "booster_message")


def set_log_channel(guild_id: int, cid: int) -> None:
    _set_guild_value(guild_id, "log_channel_id", str(cid))


def get_log_channel(guild_id: int) -> Optional[int]:
    val = _get_guild_value(guild_id, "log_channel_id")
    return int(val) if val else None


def set_role(guild_id: int, name: str, role_id: int) -> None:
    old_id = get_role(guild_id, name)
    _execute(
        "INSERT OR REPLACE INTO roles (guild_id, name, role_id) VALUES (?, ?, ?)",
        (str(guild_id), name, str(role_id)),
    )
    if old_id is not None and old_id != role_id:
        _execute(
            "UPDATE command_permissions SET role_id = ? WHERE guild_id = ? AND role_id = ?",
            (str(role_id), str(guild_id), str(old_id)),
        )


def get_role(guild_id: int, name: str) -> Optional[int]:
    row = _fetchone(
        "SELECT role_id FROM roles WHERE guild_id = ? AND name = ?",
        (str(guild_id), name),
    )
    return int(row[0]) if row and row[0] else None


def remove_role(guild_id: int, name: str) -> None:
    role_id = get_role(guild_id, name)
    if role_id is None:
        return
    _execute(
        "DELETE FROM roles WHERE guild_id = ? AND name = ?",
        (str(guild_id), name),
    )
    _execute(
        "UPDATE command_permissions SET role_id = NULL WHERE guild_id = ? AND role_id = ?",
        (str(guild_id), str(role_id)),
    )


def _fetchall(query: str, params: tuple = ()) -> list[tuple]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()


def get_roles(guild_id: int) -> dict[str, int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, role_id FROM roles WHERE guild_id = ?",
        (str(guild_id),),
    )
    rows = cursor.fetchall()
    conn.close()
    return {name: int(rid) for name, rid in rows}


def set_command_permission(guild_id: int, command: str, role_id: int) -> None:
    _execute(
        "INSERT OR REPLACE INTO command_permissions (guild_id, command, role_id) VALUES (?, ?, ?)",
        (str(guild_id), command, str(role_id)),
    )


def get_command_permission(guild_id: int, command: str) -> Optional[int]:
    row = _fetchone(
        "SELECT role_id FROM command_permissions WHERE guild_id = ? AND command = ?",
        (str(guild_id), command),
    )
    return int(row[0]) if row and row[0] is not None else None


def remove_command_permission(guild_id: int, command: str) -> None:
    _execute(
        "DELETE FROM command_permissions WHERE guild_id = ? AND command = ?",
        (str(guild_id), command),
    )


def get_command_permissions(guild_id: int) -> dict[str, int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT command, role_id FROM command_permissions WHERE guild_id = ?",
        (str(guild_id),),
    )
    rows = cursor.fetchall()
    conn.close()
    return {cmd: int(rid) for cmd, rid in rows if rid is not None}


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


def get_custom_role(guild_id: int, user_id: str):
    row = _fetchone(
        "SELECT role_id FROM custom_roles WHERE guild_id = ? AND user_id = ?",
        (str(guild_id), user_id),
    )
    return int(row[0]) if row else None


def set_custom_role(guild_id: int, user_id: str, role_id: int):
    _execute(
        "INSERT OR REPLACE INTO custom_roles (guild_id, user_id, role_id) VALUES (?, ?, ?)",
        (str(guild_id), user_id, role_id),
    )


def delete_custom_role(guild_id: int, user_id: str):
    _execute(
        "DELETE FROM custom_roles WHERE guild_id = ? AND user_id = ?",
        (str(guild_id), user_id),
    )


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


def add_filtered_word(guild_id: int, word: str):
    _execute(
        "INSERT OR IGNORE INTO filtered_words (guild_id, word) VALUES (?, ?)",
        (str(guild_id), word.lower()),
    )


def remove_filtered_word(guild_id: int, word: str):
    _execute(
        "DELETE FROM filtered_words WHERE guild_id = ? AND word = ?",
        (str(guild_id), word.lower()),
    )


def get_filtered_words(guild_id: int) -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT word FROM filtered_words WHERE guild_id = ?", (str(guild_id),)
    )
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


# ---------- trigger response helpers ----------


def add_trigger_response(trigger: str, response: str, guild_id: int):
    _execute(
        "INSERT OR REPLACE INTO trigger_responses (guild_id, trigger, response) VALUES (?, ?, ?)",
        (str(guild_id), trigger.lower(), response),
    )


def remove_trigger_response(trigger: str, guild_id: int):
    _execute(
        "DELETE FROM trigger_responses WHERE guild_id = ? AND trigger = ?",
        (str(guild_id), trigger.lower()),
    )


def get_trigger_responses(guild_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT trigger, response FROM trigger_responses WHERE guild_id = ?",
        (str(guild_id),),
    )
    rows = cursor.fetchall()
    conn.close()
    return {trigger: response for trigger, response in rows}


# ---------- anti nuke helpers ----------


def get_anti_nuke_setting(
    category: str, guild_id: int
) -> Optional[Tuple[int, int, str, Optional[int]]]:

    row = _fetchone(
        "SELECT enabled, threshold, punishment, duration FROM anti_nuke_settings WHERE guild_id = ? AND category = ?",
        (str(guild_id), category),
    )
    return row if row else None


def set_anti_nuke_setting(
    category: str,
    enabled: int,
    threshold: int,
    punishment: str,
    duration: Optional[int],
    guild_id: int,
) -> None:
    _execute(
        "INSERT OR REPLACE INTO anti_nuke_settings (guild_id, category, enabled, threshold, punishment, duration) VALUES (?, ?, ?, ?, ?, ?)",
        (str(guild_id), category, enabled, threshold, punishment, duration),
    )


def add_safe_user(guild_id: int, uid: int) -> None:
    _execute(
        "INSERT OR IGNORE INTO anti_nuke_safe_users (guild_id, user_id) VALUES (?, ?)",
        (str(guild_id), str(uid)),
    )


def remove_safe_user(guild_id: int, uid: int) -> None:
    _execute(
        "DELETE FROM anti_nuke_safe_users WHERE guild_id = ? AND user_id = ?",
        (str(guild_id), str(uid)),
    )


def get_safe_users(guild_id: int) -> List[int]:

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM anti_nuke_safe_users WHERE guild_id = ?",
        (str(guild_id),),
    )
    rows = cursor.fetchall()
    conn.close()
    return [int(r[0]) for r in rows]


def add_safe_role(guild_id: int, rid: int) -> None:
    _execute(
        "INSERT OR IGNORE INTO anti_nuke_safe_roles (guild_id, role_id) VALUES (?, ?)",
        (str(guild_id), str(rid)),
    )


def remove_safe_role(guild_id: int, rid: int) -> None:
    _execute(
        "DELETE FROM anti_nuke_safe_roles WHERE guild_id = ? AND role_id = ?",
        (str(guild_id), str(rid)),
    )


def get_safe_roles(guild_id: int) -> List[int]:

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role_id FROM anti_nuke_safe_roles WHERE guild_id = ?",
        (str(guild_id),),
    )
    rows = cursor.fetchall()
    conn.close()
    return [int(r[0]) for r in rows]


def set_anti_nuke_log_channel(guild_id: int, cid: int) -> None:
    _execute(
        "INSERT OR REPLACE INTO anti_nuke_log_channel (guild_id, channel_id) VALUES (?, ?)",
        (str(guild_id), str(cid)),
    )


def get_anti_nuke_log_channel(guild_id: int) -> Optional[int]:
    row = _fetchone(
        "SELECT channel_id FROM anti_nuke_log_channel WHERE guild_id = ?",
        (str(guild_id),),
    )
    return int(row[0]) if row else None
