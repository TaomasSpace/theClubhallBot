import sqlite3
import sys
from pathlib import Path

# ensure project root is on the Python path when running as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from config import DB_PATH

# ensure we always point at the correct database regardless of the
# working directory in which this script is executed
DB_FILE = ROOT / DB_PATH


SCALE_COINS = 1_000_000
SCALE_STATS = 1000


def rebalance():
    if not DB_FILE.exists():
        raise SystemExit(f"Database not found at {DB_FILE}")
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, money, stat_points, intelligence, strength, stealth FROM users"
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

    conn.commit()
    conn.close()


if __name__ == "__main__":
    rebalance()
    print("Database rebalanced.")
