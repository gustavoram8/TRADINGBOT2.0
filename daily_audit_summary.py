#!/usr/bin/env python3
"""
Trader Accelerator — Daily Audit Summary
Runs once a day via cron. Sends an email digest of the last 24h of
AuditEvent rows (orders, plan grants/expirations, promo codes, Synapse PDF
issuance/downloads, and outbound emails), highlighting any failures.

This is a digest on top of the immediate per-failure alerts already sent by
record_audit_event() — it exists so a quiet day (or a day where everything
"sort of" worked) still produces a paper trail in your inbox.

Cron setup (run as the deploy user on the VPS):
  crontab -e
  0 8 * * * cd /var/www/TRADINGBOT2.0 && /usr/bin/python3 daily_audit_summary.py >> /var/log/ta_audit_summary.log 2>&1
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scalpel'))

from app import app, db, AuditEvent, mail  # noqa: E402
from flask_mail import Message  # noqa: E402


def build_summary():
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = (AuditEvent.query
            .filter(AuditEvent.created_at >= since)
            .order_by(AuditEvent.created_at.asc())
            .all())

    counts = {}
    failures = []
    for r in rows:
        key = (r.event_type, r.success)
        counts[key] = counts.get(key, 0) + 1
        if not r.success:
            failures.append(r)

    lines = [f"Trader Accelerator — Daily Audit Summary",
             f"Period: last 24h (since {since.strftime('%Y-%m-%d %H:%M UTC')})",
             "", f"Total events: {len(rows)}", ""]

    if not rows:
        lines.append("No audit events in the last 24h.")
    else:
        lines.append("By type:")
        seen_types = sorted({k[0] for k in counts})
        for t in seen_types:
            ok = counts.get((t, True), 0)
            bad = counts.get((t, False), 0)
            line = f"  - {t}: {ok} ok"
            if bad:
                line += f", {bad} FAILED"
            lines.append(line)

    if failures:
        lines.append("")
        lines.append(f"⚠️ {len(failures)} failure(s) — details:")
        for f in failures:
            lines.append(
                f"  [{f.created_at.strftime('%Y-%m-%d %H:%M UTC')}] "
                f"{f.event_type} (user_id={f.user_id}): {f.detail or ''}"
            )
    else:
        lines.append("")
        lines.append("✅ No failures in the last 24h.")

    return "\n".join(lines), len(failures)


def main():
    with app.app_context():
        body, fail_count = build_summary()
        admin_inbox = app.config.get('MAIL_USERNAME', 'mauroramirezmij@gmail.com')

        if not app.config.get('MAIL_PASSWORD'):
            print("MAIL_APP_PASSWORD not configured — printing summary instead of emailing.")
            print(body)
            return

        subject = "Trader Accelerator — Daily Audit Summary"
        if fail_count:
            subject += f" ({fail_count} failures)"

        msg = Message(subject, recipients=[admin_inbox])
        msg.body = body
        mail.send(msg)
        print(f"Summary sent to {admin_inbox} ({fail_count} failures).")


if __name__ == '__main__':
    main()
