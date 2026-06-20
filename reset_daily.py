#!/usr/bin/env python3
"""
Trader Accelerator — One-off Daily Challenge reset (manual testing helper).

Clears a single user's DailyQuizState gate so they can play today's Daily
Challenge again. It does NOT alter any game logic, grant spins, or touch the
streak/roulette — it only nulls the "already played today" + served-question
fields so the normal flow re-opens for that one user.

Usage (on the VPS, with the venv python so Flask is importable):
  cd /var/www/TRADINGBOT2.0
  venv/bin/python3 reset_daily.py maurotradesve

Run it once, play the challenge, then run it again to play a second time.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scalpel'))

from app import app, db, User, DailyQuizState  # noqa: E402


def main():
    ident = sys.argv[1] if len(sys.argv) > 1 else 'maurotradesve'
    with app.app_context():
        user = (User.query.filter_by(username=ident).first()
                or User.query.filter_by(email=ident).first())
        if not user:
            print(f"No user found for '{ident}' (try username or email).")
            sys.exit(1)
        st = DailyQuizState.query.filter_by(user_id=user.id).first()
        if not st:
            print(f"{user.username} has no Daily Challenge state yet — "
                  "nothing to reset (just open it normally).")
            return
        st.last_played = None
        st.served_for = None
        st.question_served_at = None
        db.session.commit()
        print(f"Daily Challenge gate reset for {user.username} "
              f"(streak kept at {st.streak}, spins kept at {st.spins_available}). "
              "Open the challenge again to play.")


if __name__ == '__main__':
    main()
