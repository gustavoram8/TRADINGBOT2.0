#!/usr/bin/env python3
"""
Trader Acelerator — Health Monitor
Runs every hour via cron. Checks site health and sends WhatsApp alerts
if any threshold is exceeded.

Cron setup (run as root on VPS):
  crontab -e
  0 * * * * /usr/bin/python3 /var/www/TRADINGBOT2.0/monitor.py >> /var/log/ta_monitor.log 2>&1
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
import shutil
from datetime import datetime, timezone

# ── Config (set as env vars in supervisor or export before running) ──
SITE_URL   = os.environ.get("SITE_URL",   "http://127.0.0.1:5001")
WA_PHONE   = os.environ.get("WA_PHONE",  "")
WA_APIKEY  = os.environ.get("WA_APIKEY", "")

# ── Thresholds ──
MAX_DB_MB      = 400    # warn if DB > 400 MB
MAX_USERS      = 450    # warn if users > 450 (approaching 500)
MAX_RESP_MS    = 3000   # warn if response time > 3s
DISK_WARN_PCT  = 85     # warn if disk usage > 85%


def send_whatsapp(message):
    if not WA_PHONE or not WA_APIKEY:
        print("WhatsApp not configured — skipping alert.")
        return
    try:
        encoded = urllib.parse.quote(message)
        url = (f"https://api.callmebot.com/whatsapp.php"
               f"?phone={WA_PHONE}&text={encoded}&apikey={WA_APIKEY}")
        urllib.request.urlopen(url, timeout=10)
        print(f"WhatsApp alert sent: {message[:60]}...")
    except Exception as e:
        print(f"WhatsApp alert failed: {e}")


def check_site():
    alerts = []
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    # ── 1. Site reachability + response time ──
    try:
        start = __import__('time').time()
        req = urllib.request.urlopen(f"{SITE_URL}/health", timeout=10)
        elapsed_ms = int((__import__('time').time() - start) * 1000)
        data = json.loads(req.read().decode())

        if data.get('status') != 'ok':
            alerts.append(f"⚠️ Health endpoint returned status: {data.get('status')}")

        # ── 2. Response time ──
        if elapsed_ms > MAX_RESP_MS:
            alerts.append(f"🐢 Slow response: {elapsed_ms}ms (limit {MAX_RESP_MS}ms)")

        # ── 3. DB size ──
        db_mb = data.get('db_size_mb', 0)
        if db_mb > MAX_DB_MB:
            alerts.append(f"🗄️ DB size: {db_mb}MB (limit {MAX_DB_MB}MB) — consider PostgreSQL migration")

        # ── 4. User count approaching limit ──
        users = data.get('users_total', 0)
        if users > MAX_USERS:
            alerts.append(f"👥 Users: {users} — approaching 500 user threshold!")

        print(f"[{now}] OK — {elapsed_ms}ms | {users} users | DB {db_mb}MB")

    except urllib.error.URLError as e:
        alerts.append(f"🔴 SITE DOWN — cannot reach {SITE_URL}: {e.reason}")
    except Exception as e:
        alerts.append(f"🔴 Monitor error: {str(e)[:100]}")

    # ── 5. Disk space ──
    try:
        usage = shutil.disk_usage("/")
        pct = int(usage.used / usage.total * 100)
        if pct > DISK_WARN_PCT:
            alerts.append(f"💾 Disk usage: {pct}% (limit {DISK_WARN_PCT}%)")
    except Exception as e:
        print(f"Disk check failed: {e}")

    # ── Send alerts if any ──
    if alerts:
        msg = f"🚨 *Trader Acelerator Monitor*\n{now}\n\n" + "\n".join(alerts)
        print(f"ALERT: {msg}")
        send_whatsapp(msg)
    else:
        print(f"[{now}] All systems OK.")


if __name__ == '__main__':
    check_site()
