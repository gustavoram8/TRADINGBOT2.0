#!/usr/bin/env python3
"""
Trader Acelerator — Database Backup
Runs once a day via cron. Makes a consistent copy of scalpel.db using
SQLite's online backup API (safe to run while the app is writing to the
database) and keeps the last BACKUP_KEEP_DAYS copies, deleting older ones.

Cron setup (run as the deploy user on the VPS):
  crontab -e
  30 7 * * * cd /var/www/TRADINGBOT2.0 && /usr/bin/python3 backup_db.py >> /var/log/ta_backup.log 2>&1

Restoring a backup (stop the app first):
  supervisorctl stop traderacelerator
  cp backups/scalpel_YYYY-MM-DD.db scalpel/scalpel.db
  supervisorctl start traderacelerator
"""

import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'scalpel', 'scalpel.db')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
BACKUP_KEEP_DAYS = 14


def make_backup():
    if not os.path.exists(DB_PATH):
        print(f"No database found at {DB_PATH} — nothing to back up.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    dest_path = os.path.join(BACKUP_DIR, f'scalpel_{today}.db')

    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest_path)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()

    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
    print(f"Backup written: {dest_path} ({size_mb:.2f} MB)")


def prune_old_backups():
    if not os.path.isdir(BACKUP_DIR):
        return

    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - BACKUP_KEEP_DAYS * 86400

    for name in os.listdir(BACKUP_DIR):
        if not (name.startswith('scalpel_') and name.endswith('.db')):
            continue
        path = os.path.join(BACKUP_DIR, name)
        if os.path.getmtime(path) < cutoff:
            os.remove(path)
            print(f"Removed old backup: {name}")


if __name__ == '__main__':
    make_backup()
    prune_old_backups()
