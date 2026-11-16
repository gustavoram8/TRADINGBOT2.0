# 19 · EL BOT VIEJO Y TODO LO DEMÁS QUE HAY EN EL REPO

## Por qué el repo se llama TRADINGBOT2.0

El repositorio nació (abril 2026) como un **bot de trading ICT** llamado
internamente **"Chuky Bot"**. Tradeable (entonces "Scalpel") se añadió un mes
después como una carpeta aparte, `scalpel/`, y terminó siendo el proyecto. El
bot quedó en la raíz, sin tocar.

**Son dos proyectos distintos que comparten repositorio y servidor.** No
comparten código.

## 🔴 LA TRAMPA: un push a `main` redespliega el bot viejo

`.github/workflows/deploy.yml` se dispara con **cualquier push a `main`** y, si
los secretos de GitHub siguen configurados, entra al VPS y:

1. va a `/opt/tradingbot` y hace `git reset --hard origin/main`;
2. reinstala y recompila el panel del bot;
3. **copia su config de nginx y la activa** (es la que no tenía `server_name` y
   respondía por cualquier nombre; ya secuestró el dominio una vez);
4. recarga nginx;
5. **arranca/reinicia los procesos del bot** (PM2 y systemd).

Es decir: deshace el apagado del 30-jul y puede interferir con el sitio.

**Por eso:**
- **Nunca** hacer push ni merge a `main`.
- Si algún día se quiere que `main` refleje Tradeable, **primero** hay que
  desactivar ese workflow (GitHub → Actions) — decisión del dueño, porque es
  parte de su proyecto del bot.
- ⚠️ Sin verificar: si los secretos `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
  siguen puestos en GitHub. Si lo están, además son una llave SSH al servidor
  guardada en GitHub.

## El bot en el VPS

- **Carpeta:** `/opt/tradingbot`. **Apagado el 2026-07-30, no borrado.**
- Se apagó porque su sitio de nginx capturaba el dominio nuevo y porque un
  proceso (`tradingbot-frontend`) llevaba más de 1.800 reinicios en bucle
  quemando CPU.
- Qué se hizo: quitar el enlace de `sites-enabled/tradingbot` (el archivo sigue
  en `sites-available`), `pm2 stop all && pm2 save && pm2 kill`,
  `systemctl disable pm2-root`. Respaldo:
  `/root/.pm2/dump.pm2.backup-2026-07-30`.
- **Revivirlo:** `systemctl enable --now pm2-root && pm2 resurrect && pm2 start all`
  (y volver a enlazar su sitio de nginx, con cuidado de darle `server_name`).
- 🔴 **Regla permanente del dueño: ese proyecto es suyo y no se toca ni se borra.**

## Qué es cada cosa en la raíz del repo

### Del bot viejo (no tocar)
| Ruta | Qué es |
|---|---|
| `main.py` | Orquestador: descarga datos, backtest, walk-forward, Monte Carlo, verificación de consistencia para una prop firm, reporte GO/NO-GO |
| `backtest.py`, `server.py`, `reset_daily.py` | Backtest, servidor de API, reinicio diario |
| `strategy/`, `indicators/`, `risk/`, `validation/`, `reporting/`, `data/`, `config/`, `api_server/` | El motor en Python (estrategia ICT, FVG, liquidez, estructura, gestión de riesgo…) |
| `dashboard/`, `.streamlit/` | Panel en Streamlit |
| `app/`, `components/`, `lib/`, `store/`, `package.json`, `next.config.mjs`, `tailwind.config.ts`, `tsconfig.json`, `postcss.config.mjs`, `instrumentation.ts`, `vercel.json`, `.env.local.example` | Panel web en Next.js 14 + React 18 (`"name": "chuky-bot"`) |
| `requirements.txt` (raíz) | Dependencias **del bot** (backtrader, yfinance, pandas, streamlit, fastapi…). ⚠️ No confundir con `scalpel/requirements.txt` |
| `deploy/nginx-tradingbot.conf`, `nginx.conf.example`, `deploy/dominio.sh` | Config de nginx del bot / utilidades |
| `.github/workflows/deploy.yml` | **El workflow peligroso** (arriba) |
| `generate_report.py`, `generate_mobile_report.py`, `reports/`, `scripts/` | Generadores de informes |
| `docs/Manual_Usuario_Chuky_Bot.pdf`, `docs/generate_user_manual.py` | Manual del bot |
| `Trading_Research_Report_2025_2026.pdf`, `Trading_Research_Mobile_iPhone.pdf`, `ICT - GATILLOS DE ENTRADA (EJEMPLOS) (1).pdf` | Material de investigación y referencia de ICT |

💡 Nota: el bot ya tenía en `indicators/` implementaciones de FVG, liquidez y
estructura **sobre datos de precio reales**. El Analizador 2.0 las reescribió
para series medidas en píxeles (`tools/hechos_grafico.py`); no se reutilizó
código, pero las ideas son las mismas.

### De Tradeable
| Ruta | Qué es |
|---|---|
| `scalpel/` | El sitio |
| `tools/` | Pruebas, utilidades del VPS, arte, contenido y laboratorio |
| `docs/` | Acuerdo, resultados del banco, capturas, columnas |
| `deploy/nginx/`, `deploy/coming_soon/` | Configs de nginx del dominio y página de espera |
| `CONTEXTO_TRADEABLE/` | Este expediente |
| `CLAUDE.md`, `CLAUDE_ARCHIVE.md`, `LANZAMIENTO.md` | Notas de trabajo |
| `backup_db.py`, `monitor.py`, `daily_audit_summary.py` | Tareas programadas del VPS |
| `migrate_to_postgres.py`, `grant_legend.py` | Scripts puntuales (migración de junio; otorgar un rango) |
| `COPYRIGHT_REGISTRATION_GUIDE.md` | Guía para registrar el copyright |
| `LEGAL_REVIEW_*.md`, `CHATGPT_TC_*.md`, `legal_*_review.html` | Revisiones legales de junio–julio |
| `Trader_Acelerator_*.pdf`, `Scalpel_*.pdf`, `scalpel_costos_operativos.csv` | Documentos tempranos con nombres viejos (**desactualizados**) |
| `rank_badges_preview*.html`, `legend_badge_preview.html` | Maquetas de medallas |
| `out/` | Salidas generadas (ignorada por git, salvo un par de archivos) |

## Si algún día se quiere ordenar

La separación limpia sería sacar Tradeable a un repositorio propio (o mover el
bot a otro), con `main` como rama real y sin el workflow del bot. **No se ha
hecho y no es urgente**; es una decisión del dueño. Mientras tanto, las tres
reglas bastan: trabajar en `gallant-volta`, no tocar `main`, no tocar el bot.
