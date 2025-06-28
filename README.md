# Clubhall Bot

Utility bot for Discord.

## Database Rebalancing

A maintenance script lives in `scripts/rebalance_db.py` to shrink coin totals and stats.
Run it from the project root with:


```bash
python scripts/rebalance_db.py
```

**Important:** back up your `users.db` database before running the script.
