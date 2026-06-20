#!/usr/bin/env python3
"""
Trader Accelerator — Database Backup
Runs once a day via cron. Detects the production database from DATABASE_URL
(in scalpel/.env or the environment):

  - PostgreSQL → dumps with pg_dump (custom format, compressed)
  - SQLite (or no DATABASE_URL) → consistent copy via the online backup API

Keeps the last BACKUP_KEEP_DAYS backups, deleting older ones.

Cron setup (run as the deploy user on the VPS):
  crontab -e
  30 7 * * * cd /var/www/TRADINGBOT2.0 && /usr/bin/python3 backup_db.py >> /var/log/ta_backup.log 2>&1

Restoring a PostgreSQL backup:
  pg_restore --clean --if-exists -d "$DATABASE_URL" backups/scalpel_YYYY-MM-DD.dump

Restoring a SQLite backup (stop the app first):
  supervisorctl stop traderaccelerator
  cp backups/scalpel_YYYY-MM-DD.db scalpel/scalpel.db
  supervisorctl start traderaccelerator
"""

import os
import sqlite3
import subprocess
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, 'scalpel', 'scalpel.db')
ENV_PATH = os.path.join(BASE_DIR, 'scalpel', '.env')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
BACKUP_KEEP_DAYS = 14


def get_database_url():
    """DATABASE_URL from the environment, falling back to scalpel/.env."""
    url = os.environ.get('DATABASE_URL', '')
    if not url and os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            line = line.strip()
            if line.startswith('DATABASE_URL='):
                url = line.split('=', 1)[1].strip().strip('"').strip("'")
                break
    return url


def backup_postgres(url):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    dest_path = os.path.join(BACKUP_DIR, f'scalpel_{today}.dump')

    # pg_dump speaks libpq URIs but not SQLAlchemy driver suffixes
    # (postgresql+psycopg2:// → postgresql://)
    if '+' in url.split('://', 1)[0]:
        url = url.split('+', 1)[0] + '://' + url.split('://', 1)[1]

    result = subprocess.run(
        ['pg_dump', '--format=custom', '--file', dest_path, url],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f'pg_dump failed: {result.stderr.strip()}')

    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
    print(f"PostgreSQL backup written: {dest_path} ({size_mb:.2f} MB)")


def backup_sqlite():
    if not os.path.exists(SQLITE_PATH):
        print(f"No database found at {SQLITE_PATH} — nothing to back up.")
        return

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    dest_path = os.path.join(BACKUP_DIR, f'scalpel_{today}.db')

    src = sqlite3.connect(SQLITE_PATH)
    dst = sqlite3.connect(dest_path)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()

    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
    print(f"SQLite backup written: {dest_path} ({size_mb:.2f} MB)")


def prune_old_backups():
    if not os.path.isdir(BACKUP_DIR):
        return

    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - BACKUP_KEEP_DAYS * 86400

    for name in os.listdir(BACKUP_DIR):
        if not (name.startswith('scalpel_') and (name.endswith('.db') or name.endswith('.dump'))):
            continue
        path = os.path.join(BACKUP_DIR, name)
        if os.path.getmtime(path) < cutoff:
            os.remove(path)
            print(f"Removed old backup: {name}")


if __name__ == '__main__':
    os.makedirs(BACKUP_DIR, exist_ok=True)
    url = get_database_url()
    if url.startswith('postgres'):
        backup_postgres(url)
    else:
        backup_sqlite()
    prune_old_backups()
