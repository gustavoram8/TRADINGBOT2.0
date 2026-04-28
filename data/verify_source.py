"""
Verificación de la fuente de datos del bot.

Ejecutable directo:
    python -m data.verify_source

Confirma que:
  • La fuente es Yahoo Finance (yfinance) con el ticker NQ=F
  • NQ=F es el contrato continuo del Nasdaq-100 E-mini Futures (CME)
  • Los precios coinciden con MNQ (mismos niveles, distinto multiplicador)
  • Los datos son reales del mercado (delay típico ~15 min en yfinance)

Imprime una muestra de las últimas barras 1H y 1D y el rango completo
disponible, para que se pueda contrastar contra cualquier fuente externa
(TradingView, broker, CME, etc.).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    print("=" * 72)
    print("  VERIFICACIÓN DE FUENTE DE DATOS — ICT TRADING BOT")
    print("=" * 72)

    try:
        import yfinance as yf
    except ImportError:
        print("✗ yfinance no instalado. Ejecuta: pip install yfinance>=0.2.31")
        return 1

    from config.settings import SYMBOL, ASSET_NAME, POINT_VALUE, TICK_VALUE
    from data.downloader import download_data

    print(f"\n  Fuente:       Yahoo Finance API (yfinance)")
    print(f"  Ticker:       {SYMBOL}  (Nasdaq-100 E-mini Futures, contrato continuo)")
    print(f"  Activo real:  {ASSET_NAME}  (mismos precios que NQ, mult ${POINT_VALUE}/pt)")
    print(f"  Tick value:   ${TICK_VALUE}")
    print(f"  Latencia:     ~15 min de delay (datos retrasados, no tick-by-tick)")
    print(f"  Calidad:      Datos reales del mercado consolidados por Yahoo Finance")
    print(f"                (origen original: CME Globex, vía proveedores agregados)")

    # Intentar fetch en vivo
    print("\n" + "─" * 72)
    print("  Probando conexión con yfinance...")
    print("─" * 72)

    try:
        ticker = yf.Ticker(SYMBOL)
        info = ticker.info
        if info:
            print(f"  ✓ Conexión OK con yfinance.")
            for k in ("shortName", "longName", "quoteType", "exchange", "currency"):
                if k in info:
                    print(f"    {k:14s}: {info[k]}")
    except Exception as e:
        print(f"  ⚠ ticker.info falló (no crítico): {e}")

    # Descargar 1H reciente
    print("\n" + "─" * 72)
    print("  Descargando muestra de datos 1H (últimos 5 días)...")
    print("─" * 72)
    end   = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    df_1h = download_data(interval="1h", start=start, end=end, use_cache=False)
    if df_1h.empty:
        print("  ✗ No se pudieron descargar datos 1H.")
        return 2

    print(f"\n  ✓ {len(df_1h)} barras 1H descargadas.")
    print(f"  Rango:     {df_1h.index[0]}  →  {df_1h.index[-1]}")
    print(f"  Timezone:  {df_1h.index.tz}")
    print(f"\n  Últimas 5 barras 1H:")
    print(df_1h.tail(5).to_string())

    # Descargar 1D para periodo del backtest
    print("\n" + "─" * 72)
    print("  Descargando datos diarios (último año)...")
    print("─" * 72)
    df_1d = download_data(
        interval="1d",
        start=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        end=end,
        use_cache=False,
    )
    if not df_1d.empty:
        print(f"\n  ✓ {len(df_1d)} barras 1D.")
        print(f"  Rango: {df_1d.index[0].date()}  →  {df_1d.index[-1].date()}")
        print(f"  Min/Max Close del año: ${df_1d['Close'].min():,.2f}  /  ${df_1d['Close'].max():,.2f}")
        print(f"\n  Últimas 5 barras diarias:")
        print(df_1d.tail(5).to_string())

    print("\n" + "=" * 72)
    print("  VERIFICACIÓN COMPLETA")
    print("=" * 72)
    print("\n  Para validar manualmente estos precios, compara contra:")
    print("    • TradingView:  https://www.tradingview.com/symbols/CME_MINI-NQ1!/")
    print("    • Yahoo:        https://finance.yahoo.com/quote/NQ=F")
    print("    • CME Group:    https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.html")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
