# -*- coding: utf-8 -*-
"""¿Arranca la app contra una base de PRODUCCIÓN a la que le faltan columnas?

    python3 tools/test_boot_postgres.py            # busca un PostgreSQL local
    DATABASE_URL=postgresql+psycopg2://… python3 tools/test_boot_postgres.py

Existe porque `test_boot_migracion.py` corre sobre SQLite, y SQLite **acepta
cosas que PostgreSQL rechaza**. Los dos fallos que tumbaron el sitio no se
podían ver de otra forma:

  · `BOOLEAN NOT NULL DEFAULT 0` → PostgreSQL: "default expression is of type
    integer". La columna no se crea, el modelo la declara igual, y a partir de
    ahí TODA consulta a esa tabla revienta. El síntoma no es un error de
    migración: es una página de error en el sitio.
  · `ALTER TABLE user …` sin comillas → `user` es palabra reservada. Y
    `DATETIME` no existe en PostgreSQL.

La prueba imita el deploy real: crea el esquema, le QUITA a mano las columnas
que en producción no existían todavía, arranca `init_db()` y comprueba que
vuelven TODAS y que las tablas se pueden leer.

Si no hay PostgreSQL a mano no falla: avisa y se salta (así no rompe a quien
solo tenga SQLite), pero entonces NO ha probado nada — no vale como visto bueno.
"""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Columnas que se le añadieron a la base DESPUÉS de que existiera la tabla. Son
# justo las que un deploy tiene que crear al vuelo, y por tanto las que pueden
# reventar el arranque. Al añadir una columna nueva al modelo: sumarla aquí.
QUITAR = {
    '"user"': ['email_verified', 'verification_code', 'verification_expires',
               'is_banned', 'banned_at', 'ban_reason', 'terms_accepted_at',
               'terms_version', 'plan_cycle', 'plan_started_at',
               'plan_expires_at', 'cancel_at_period_end', 'birth_date',
               'totp_secret', 'totp_confirmed_at', 'totp_backup', 'alt_id',
               'active_camo', 'owned_camos', 'active_frame', 'active_cursor',
               'referred_by_code', 'referred_at', 'muted_until',
               'last_review_prompt_at'],
    '"order"': ['is_test', 'celebrated_at', 'provider_ref', 'pay_status',
                'paid_amount', 'pay_currency', 'tx_hash', 'alerted_at'],
    'plan_subscription': ['pending_plan', 'pending_price', 'pending_at'],
    'sale_breakdown': ['reserve_amt', 'reserve_pct', 'available_profit'],
    'testimonial': ['insider'],
    'promo_code': ['restrict_user_id', 'owner_user_id'],
    'forum_post': ['community_id'],
    'daily_quiz_state': ['best_streak', 'best_streak_at'],
}


def url_de_pruebas():
    """La base contra la que probar. Nunca la de producción."""
    dada = os.environ.get('PG_TEST_URL') or os.environ.get('DATABASE_URL', '')
    if dada.startswith('postgres'):
        return dada
    # Un PostgreSQL local levantado a mano para esto.
    for puerto in (5433, 5432):
        u = 'postgresql+psycopg2://postgres@127.0.0.1:%d/tabot_boot' % puerto
        try:
            import psycopg2
            c = psycopg2.connect(host='127.0.0.1', port=puerto, user='postgres',
                                 dbname='postgres', connect_timeout=3)
        except Exception:
            continue
        c.autocommit = True
        cur = c.cursor()
        cur.execute('DROP DATABASE IF EXISTS tabot_boot')
        cur.execute('CREATE DATABASE tabot_boot')
        c.close()
        return u
    return ''


def main():
    url = url_de_pruebas()
    if not url:
        print('⚠️  SIN PostgreSQL a mano — esta prueba NO se ejecutó.')
        print('    No cuenta como aprobada: los fallos que busca son'
              ' invisibles en SQLite.')
        return 0
    if 'tabot_boot' not in url and os.environ.get('PG_TEST_URL') is None:
        print('🔴 Me niego a tocar %s — usa PG_TEST_URL con una base de usar y '
              'tirar.' % url.rsplit('/', 1)[-1])
        return 1

    os.environ['DATABASE_URL'] = url
    sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
    import app as A                                   # noqa: E402
    from sqlalchemy import text                       # noqa: E402

    ok = fallos = 0

    def check(cond, txt):
        nonlocal ok, fallos
        if cond:
            ok += 1
            print('  ok    ', txt)
        else:
            fallos += 1
            print('  FALLA ', txt)

    with A.app.app_context():
        motor = A.db.engine.url.get_backend_name()
        print('\nmotor: %s' % motor)
        check(motor.startswith('postgres'), 'se está probando en PostgreSQL')
        A.db.create_all()

        print('\n1 · se deja la base como estaba antes de estas columnas')
        quitadas = 0
        with A.db.engine.begin() as c:
            for tabla, cols in QUITAR.items():
                for col in cols:
                    c.execute(text('ALTER TABLE %s DROP COLUMN IF EXISTS %s'
                                   % (tabla, col)))
                    quitadas += 1
        print('     %d columnas quitadas' % quitadas)

        def columnas(tabla):
            with A.db.engine.connect() as c:
                return {r[0] for r in c.execute(text(
                    'SELECT column_name FROM information_schema.columns '
                    'WHERE table_name = :t'), {'t': tabla.strip('"')})}

        faltan = {t: [c for c in cols if c not in columnas(t)]
                  for t, cols in QUITAR.items()}
        check(sum(len(v) for v in faltan.values()) == quitadas,
              'la base quedó de verdad sin ellas')

        print('\n2 · arranca la app, como en el deploy')
        try:
            A.init_db()
            arrancó = True
        except Exception as exc:
            arrancó = False
            print('     💥 %s' % str(exc)[:200])
        check(arrancó, '🔴 init_db() termina sin reventar')

        print('\n3 · ¿volvieron TODAS las columnas?')
        for tabla, cols in QUITAR.items():
            hay = columnas(tabla)
            perdidas = [c for c in cols if c not in hay]
            check(not perdidas, '%-20s %s' % (
                tabla, 'completa' if not perdidas
                else '🔴 FALTAN: %s' % ', '.join(perdidas)))

        print('\n4 · y las tablas se pueden LEER (esto es lo que ve el cliente)')
        for nombre, modelo in (('User', A.User), ('Order', A.Order),
                               ('PlanSubscription', A.PlanSubscription),
                               ('SaleBreakdown', A.SaleBreakdown),
                               ('Testimonial', A.Testimonial),
                               ('PromoCode', A.PromoCode)):
            try:
                n = modelo.query.count()
                check(True, '%-18s %d fila(s)' % (nombre, n))
            except Exception as exc:
                check(False, '%-18s 🔴 %s' % (nombre, str(exc)[:90]))

        print('\n5 · arrancar dos veces seguidas no rompe nada')
        try:
            A.init_db()
            check(True, 'la migración es idempotente')
        except Exception as exc:
            check(False, '🔴 el segundo arranque falla: %s' % str(exc)[:120])

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
