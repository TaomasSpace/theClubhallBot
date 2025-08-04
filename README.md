# Clubhall Bot

Utility bot for Discord.

## Database Rebalancing

A maintenance script lives in `scripts/rebalance_db.py` to shrink coin totals and stats.
Run it with:

```bash
python scripts/rebalance_db.py
```

The script automatically locates `users.db` in the project root so it can be run from any directory.

**Important:** back up your `users.db` database before running the script.

## Setup Wizard

Run `/setup-wizard` on your server to walk through a complete configuration.
The wizard explains every step, lets you skip anything, and sets up channels,
roles, anti-nuke options, command permissions, and more for future use.
