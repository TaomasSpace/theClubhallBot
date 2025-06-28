import sqlite3

SCALE_COINS = 1_000_000_000
SCALE_STATS = 1000


def rebalance():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, money, stat_points, intelligence, strength, stealth FROM users where money > 1000000000000"
    )
    for user_id, money, sp, intel, stren, stealth in cursor.fetchall():
        cursor.execute(
            "UPDATE users SET money=?, stat_points=?, intelligence=?, strength=?, stealth=? WHERE user_id=?",
            (
                money // SCALE_COINS,
                sp // SCALE_STATS,
                max(1, intel // SCALE_STATS),
                max(1, stren // SCALE_STATS),
                max(1, stealth // SCALE_STATS),
                user_id,
            ),
        )

    cursor.execute("UPDATE server SET max_coins = max_coins / ?", (SCALE_COINS,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    rebalance()
    print("Database rebalanced.")
