# -*- coding: utf-8 -*-
"""Ventanas festivas: calendario exacto acordado con el dueño (2026-08-02)."""
import os, sys, tempfile
from datetime import datetime, timedelta, timezone

os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'v.db')
sys.path.insert(0, 'scalpel')
from app import festive_window, FESTIVE_TZ, FESTIVE_WINDOWS, _easter_md   # noqa

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('  %s %s %s' % ('ok  ' if ok else 'FALLA', n, extra if not ok else ''))

VET = FESTIVE_TZ
HOY = datetime(2026, 8, 2, 16, 0, tzinfo=timezone.utc)   # 2 de agosto de 2026

print('\n1 · próxima apertura de cada festividad, vista desde el 2-ago-2026')
esperado = {
    'newyear':   '2027-01-01', 'valentine': '2027-02-14', 'lucky':   '2027-03-17',
    'easter':    '2027-03-28', 'fourth':    '2027-07-04', 'hallow':  '2026-10-31',
    'muertos':   '2026-11-02', 'frost':     '2026-12-21', 'santa':   '2026-12-25',
}
for slug, fecha in esperado.items():
    abierto, cuando = festive_window(slug, HOY)
    check('%-10s -> %s' % (slug, fecha),
          not abierto and cuando and cuando.strftime('%Y-%m-%d') == fecha,
          str(cuando))

print('\n2 · la medianoche es la de VENEZUELA (UTC-4)')
check('offset de la zona = UTC-4', VET.utcoffset(None) == timedelta(hours=-4))
# 25-dic 00:00 VET == 25-dic 04:00 UTC
check('cerrado a las 03:59 UTC del 25 (aún es 23:59 del 24 en Venezuela)',
      not festive_window('santa', datetime(2026, 12, 25, 3, 59, tzinfo=timezone.utc))[0])
check('ABIERTO a las 04:00 UTC del 25 (medianoche en Venezuela)',
      festive_window('santa', datetime(2026, 12, 25, 4, 0, tzinfo=timezone.utc))[0])
check('sigue ABIERTO 23h59 después',
      festive_window('santa', datetime(2026, 12, 26, 3, 59, tzinfo=timezone.utc))[0])
check('CERRADO a las 24h exactas',
      not festive_window('santa', datetime(2026, 12, 26, 4, 0, tzinfo=timezone.utc))[0])

print('\n3 · se repite igual el año siguiente')
check('navidad 2027 abre el 25-dic-2027',
      festive_window('santa', datetime(2027, 12, 25, 5, 0, tzinfo=timezone.utc))[0])
check('tras navidad 2026, la próxima es la de 2027',
      festive_window('santa', datetime(2027, 1, 5, tzinfo=timezone.utc))[1]
      .strftime('%Y-%m-%d') == '2027-12-25')
check('4 de julio 2027 abre de verdad',
      festive_window('fourth', datetime(2027, 7, 4, 5, 0, tzinfo=timezone.utc))[0])
check('y en 2028 vuelve a tocar',
      festive_window('fourth', datetime(2027, 8, 1, tzinfo=timezone.utc))[1]
      .strftime('%Y-%m-%d') == '2028-07-04')

print('\n4 · año nuevo, el caso que cruza de año')
check('31-dic 20:00 VET: todavía cerrado',
      not festive_window('newyear', datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc))[0])
check('1-ene 00:00 VET (04:00 UTC): abierto',
      festive_window('newyear', datetime(2027, 1, 1, 4, 0, tzinfo=timezone.utc))[0])

print('\n5 · pascua se calcula sola')
for y, md in ((2026, (4, 5)), (2027, (3, 28)), (2028, (4, 16)), (2029, (4, 1))):
    check('pascua %d = %02d-%02d' % (y, md[1], md[0]), _easter_md(y) == md, str(_easter_md(y)))

print('\n6 · las 9 festividades tienen regla y nada más la tiene')
check('9 festividades', len(FESTIVE_WINDOWS) == 9, str(len(FESTIVE_WINDOWS)))
check('un marco libre nunca se bloquea', festive_window('gambit', HOY) == (True, None))

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
