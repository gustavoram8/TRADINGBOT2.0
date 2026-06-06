# CLAUDE.md — Scalpel / Trader Accelerator

> **IMPORTANTE:** Este repo tiene DOS proyectos. Solo trabajamos en el **frontend Next.js (Scalpel)**. NO tocar archivos Python del trading bot (`main.py`, `server.py`, `backtest.py`, `strategy/`, `indicators/`, etc.)

---

## Qué es este proyecto

**Scalpel / Trader Accelerator** — Web app con IA para traders de futuros MNQ/NAS100.  
Permite correr backtests de estrategias ICT, analizar resultados, gestionar riesgo y chatear con un AI Analyst (Gemini) que interpreta los datos del trader.

- Nombre interno en package.json: `chuky-bot`
- Branding en sidebar: **CHUKY BOT · ICT · MNQ**
- Apunta a cuenta funded de $50k en MNQ Futures

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Framework | Next.js 14.2.5 (App Router) |
| UI | React 18, Tailwind CSS v3, Lucide React |
| Charts | Recharts, Lightweight Charts v4 |
| Estado global | Zustand |
| IA | Google Gemini (`@google/generative-ai`) |
| Estilos utils | clsx, tailwind-merge |
| Deploy | Vercel (`vercel.json`) |

---

## Estructura del Proyecto (Next.js — lo que nos importa)

```
/
├── app/
│   ├── page.tsx              # Overview / Dashboard principal
│   ├── layout.tsx            # Root layout con Sidebar
│   ├── globals.css           # Variables CSS, tema dark, clases custom
│   ├── ai/page.tsx           # AI Analyst — chat con Gemini
│   ├── backtest/             # Backtest Lab
│   ├── chart/                # Price Chart (Lightweight Charts)
│   ├── trades/               # Tabla de trades
│   ├── risk/                 # Risk Center
│   ├── validation/           # Validation
│   ├── configurator/         # Bot Builder
│   ├── journal/              # Trade Journal
│   ├── reports/              # Reports
│   └── api/
│       ├── chat/             # POST /api/chat — llama a Gemini con contexto
│       ├── backtest/         # API route para ejecutar backtest Python
│       └── sleep/            # Utility route
├── components/
│   ├── sidebar.tsx           # Sidebar colapsable (desktop + mobile drawer)
│   ├── candlestick-background.tsx  # Fondo animado de velas
│   └── charts/
│       ├── equity-curve.tsx
│       └── pnl-chart.tsx
├── lib/
│   ├── types.ts              # Interfaces TypeScript principales
│   ├── api.ts                # Cliente HTTP hacia el backend Python
│   ├── mock-data.ts          # Datos mock para desarrollo
│   └── utils.ts              # fmtUSD, fmtPct, pnlColor, cn
├── store/                    # Zustand store (backtestResult, chatHistory, etc.)
└── config/                   # Configuraciones de estrategias
```

---

## Variables de Entorno

```bash
# .env.local (nunca en git)
GEMINI_API_KEY=...         # Google Gemini API — requerido para /ai y /api/chat
```

En Vercel: configurar `GEMINI_API_KEY` en Environment Variables.

---

## Páginas y Navegación (Sidebar)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `/` | Overview | KPIs, equity curve, últimos trades |
| `/backtest` | Backtest Lab | Configurar y ejecutar backtests |
| `/chart` | Price Chart | Gráfico de velas interactivo |
| `/trades` | Trades | Tabla completa de trades |
| `/risk` | Risk Center | Trailing drawdown, límites funded |
| `/validation` | Validation | Checklist de consistencia |
| `/configurator` | Bot Builder | Configurar parámetros de estrategia |
| `/journal` | Trade Journal | Bitácora de trades |
| `/ai` | AI Analyst | Chat con Gemini usando contexto del backtest |
| `/reports` | Reports | Reportes exportables |

---

## Diseño / Tema

- **Dark theme** con variables CSS en `globals.css`
- Colores principales: `brand-blue`, `fin-green`, `fin-red`, `fin-gold`
- Clases custom: `.card`, `.kpi-card`, `.btn-primary`, `.btn-secondary`, `.badge-green`, `.badge-red`, `.badge-blue`
- Font mono para valores numéricos

---

## AI Analyst (Gemini)

- Ruta: `/ai` → llama a `POST /api/chat`
- Construye contexto con métricas del backtest + últimos 10 trades + config
- Historial del chat en Zustand (`chatHistory`)
- Quick questions predefinidas sobre rendimiento ICT
- El AI se presenta como "Chuky AI"

---

## Archivos Python (NO TOCAR)

Los siguientes son del trading bot automatizado — proyecto separado:
- `main.py`, `server.py`, `backtest.py`
- `strategy/`, `indicators/`, `risk/`, `data/`, `reporting/`, `validation/`
- `requirements.txt`, `.streamlit/`

---

## Comandos

```bash
npm run dev      # Desarrollo local en localhost:3000
npm run build    # Build de producción
npm run lint     # ESLint
```

---

## Notas de Sesiones Anteriores

- El proyecto empezó como un dashboard de backtesting para cuenta funded MNQ
- Se integró Gemini como AI Analyst con contexto ICT
- El sidebar incluye collapse en desktop y drawer en mobile
- Los datos de backtest fluyen via Zustand store desde el Backtest Lab
- Deploy en Vercel con `GEMINI_API_KEY` como env var
- **Siempre hacer push de cambios a GitHub** — las sesiones remotas de Claude Code son efímeras y se pierde todo lo local que no se pushee
