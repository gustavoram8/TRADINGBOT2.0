#!/usr/bin/env python3
"""One-off admin tool: grant a single account enough XP to reach a given rank
(default: Trading Legend, rank 8).

This does NOT alter any progression logic, rank structure, XP thresholds,
rewards, caps, or the XP config. It only:
  1. Reads the existing RANK_THRESHOLDS to find the XP needed for the target rank.
  2. Tops up ONE user's lifetime `xp` to that threshold (no-op if already there).
  3. Recomputes `rank` with the existing rank_for_xp() helper.
  4. Writes an auditable XPLog row (source='admin_grant') so the grant is logged.

Usage (run on the VPS with the venv python, from the repo root):
    venv/bin/python3 grant_legend.py <username> [target_rank]

Examples:
    venv/bin/python3 grant_legend.py maurotradesve         # -> Trading Legend (8)
    venv/bin/python3 grant_legend.py maurotradesve 8
"""
import sys
from datetime import datetime, timezone

from scalpel.app import (app, db, User, XPLog, RANK_THRESHOLDS, RANK_NAMES,
                         rank_for_xp, record_audit_event)


def main():
    if len(sys.argv) < 2:
        print("usage: grant_legend.py <username> [target_rank 1-8]")
        sys.exit(1)
    username = sys.argv[1]
    target_rank = int(sys.argv[2]) if len(sys.argv) > 2 else len(RANK_THRESHOLDS)  # default = top
    if not (1 <= target_rank <= len(RANK_THRESHOLDS)):
        print(f"target_rank must be between 1 and {len(RANK_THRESHOLDS)}")
        sys.exit(1)

    needed = RANK_THRESHOLDS[target_rank - 1]

    with app.app_context():
        user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        if not user:
            print(f"No user found with username '{username}'.")
            sys.exit(1)

        current_xp = user.xp or 0
        current_rank = user.rank or 1
        print(f"User: {user.username} (id={user.id})  plan={user.plan}")
        print(f"  before: xp={current_xp}  rank={current_rank} "
              f"({RANK_NAMES[current_rank - 1]})")

        if current_xp >= needed:
            print(f"  already at or above {needed} XP — nothing to do.")
            # Still make sure the cached rank is consistent.
            fixed = rank_for_xp(current_xp)
            if fixed != current_rank:
                user.rank = fixed
                db.session.commit()
                print(f"  (rank cache corrected to {fixed})")
            return

        delta = needed - current_xp
        # Auditable ledger row. 'admin_grant' is a brand-new source string, so it
        # does not collide with any capped/dedup source and changes no existing logic.
        db.session.add(XPLog(
            user_id=user.id, source='admin_grant', amount=delta, ref=None,
            day=datetime.now(timezone.utc).strftime('%Y-%m-%d')))
        user.xp = current_xp + delta
        user.rank = rank_for_xp(user.xp)
        db.session.commit()

        record_audit_event('rank_up', user_id=user.id,
                            detail=f'admin_grant -> {RANK_NAMES[user.rank - 1]} (xp={user.xp})')

        print(f"  granted: +{delta} XP (source=admin_grant)")
        print(f"  after:  xp={user.xp}  rank={user.rank} "
              f"({RANK_NAMES[user.rank - 1]})")


if __name__ == '__main__':
    main()
