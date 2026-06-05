#!/usr/bin/env python3
"""
One-time migration script: SQLite → PostgreSQL
Run ONCE from the VPS after setting DATABASE_URL.

Usage:
  cd /var/www/TRADINGBOT2.0
  python3 migrate_to_postgres.py
"""
import os, sys

SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'scalpel', 'scalpel.db')
PG_URL      = os.environ.get('DATABASE_URL', '')

if not PG_URL or not PG_URL.startswith('postgresql'):
    print("❌ Set DATABASE_URL to your PostgreSQL URL before running this script.")
    sys.exit(1)

if not os.path.exists(SQLITE_PATH):
    print(f"❌ SQLite DB not found at {SQLITE_PATH}")
    sys.exit(1)

print("Starting migration SQLite → PostgreSQL...")

import sqlite3
import psycopg2
from urllib.parse import urlparse

# Parse PG connection
r = urlparse(PG_URL)
pg = psycopg2.connect(
    host=r.hostname, port=r.port or 5432,
    dbname=r.path.lstrip('/'),
    user=r.username, password=r.password
)
pg.autocommit = False
pgc = pg.cursor()

# First create all tables via SQLAlchemy
os.environ['DATABASE_URL'] = PG_URL
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scalpel'))
from app import app, db
with app.app_context():
    db.create_all()
    print("✅ Tables created in PostgreSQL.")

# Now copy data table by table
sq = sqlite3.connect(SQLITE_PATH)
sq.row_factory = sqlite3.Row
sqc = sq.cursor()

TABLES = [
    'user', 'usage_log', 'analysis_project',
    'forum_post', 'forum_comment', 'forum_reaction',
    'saved_post', 'mod_warning', 'ban_suggestion',
    'browser_fingerprint', 'banned_fingerprint',
    'synapse_download_token', 'prop_firm',
    'order', 'promo_code', 'expense',
]

for table in TABLES:
    try:
        sqc.execute(f'SELECT * FROM "{table}"')
        rows = sqc.fetchall()
        if not rows:
            print(f"  {table}: empty, skipping.")
            continue

        cols = [d[0] for d in sqc.description]
        placeholders = ','.join(['%s'] * len(cols))
        col_list = ','.join([f'"{c}"' for c in cols])
        sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

        # SQLite stores booleans as 0/1 integers; PostgreSQL needs True/False
        bool_cols = set()
        pgc.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name=%s AND data_type='boolean'
        """, (table,))
        bool_cols = {r[0] for r in pgc.fetchall()}

        def fix_row(row):
            return tuple(
                bool(v) if col in bool_cols and v is not None else v
                for col, v in zip(cols, row)
            )

        data = [fix_row(row) for row in rows]
        pgc.executemany(sql, data)
        pg.commit()
        print(f"  ✅ {table}: {len(rows)} rows migrated.")
    except Exception as e:
        pg.rollback()
        print(f"  ⚠️  {table}: {e}")

sq.close()
pg.close()
print("\n✅ Migration complete. Verify data, then restart the app.")
