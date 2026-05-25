#!/usr/bin/env python3
# -*- coding: utf-8 -*-

html_content = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
  font-size: 13pt;
  line-height: 1.75;
  color: #1a1a2e;
  background: #ffffff;
}

@page {
  size: A5 portrait;
  margin: 14mm 12mm 14mm 12mm;
}

.page-break { page-break-after: always; break-after: page; }
.no-break { page-break-inside: avoid; break-inside: avoid; }

/* ---- COVER ---- */
.cover {
  min-height: 100vh;
  background: linear-gradient(160deg, #0f0c29 0%, #302b63 55%, #1e1b4b 100%);
  padding: 50px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.cover-badge {
  display: inline-block;
  background: rgba(129, 140, 248, 0.2);
  border: 1px solid rgba(129, 140, 248, 0.4);
  color: #a5b4fc;
  font-size: 9pt;
  font-weight: 700;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  padding: 7px 18px;
  border-radius: 50px;
  margin-bottom: 30px;
}

.cover h1 {
  font-size: 32pt;
  font-weight: 900;
  color: #ffffff;
  line-height: 1.15;
  margin-bottom: 16px;
  letter-spacing: -0.5px;
}

.cover h1 span { color: #818cf8; }

.cover-sub {
  font-size: 11pt;
  color: #94a3b8;
  font-weight: 300;
  margin-bottom: 40px;
  line-height: 1.6;
}

.cover-line {
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, #818cf8, #c084fc);
  margin: 0 auto 30px;
  border-radius: 2px;
}

.cover-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  width: 100%;
  margin-bottom: 36px;
}

.cstat {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 14px 10px;
  text-align: center;
}

.cstat .n {
  font-size: 20pt;
  font-weight: 800;
  color: #818cf8;
  display: block;
}

.cstat .l {
  font-size: 7.5pt;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-top: 3px;
}

.cover-meta {
  font-size: 8pt;
  color: #475569;
  letter-spacing: 0.5px;
}

/* ---- TOC ---- */
.toc-page {
  padding: 12px 4px;
}

.eyebrow {
  font-size: 8pt;
  font-weight: 700;
  color: #818cf8;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.page-title {
  font-size: 22pt;
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 6px;
  letter-spacing: -0.3px;
}

.page-intro {
  font-size: 10.5pt;
  color: #64748b;
  margin-bottom: 28px;
  line-height: 1.6;
}

.toc-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
}

.toc-item.main { border-bottom: 1.5px solid #e2e8f0; }

.toc-num {
  font-size: 9pt;
  font-weight: 800;
  color: #818cf8;
  min-width: 24px;
}

.toc-text {
  font-size: 11pt;
  font-weight: 600;
  color: #1e1b4b;
  flex: 1;
}

.toc-item.opp-item .toc-text {
  font-size: 10.5pt;
  font-weight: 500;
  color: #334155;
}

/* ---- SECTION LAYOUT ---- */
.section-page { padding: 4px 4px; }

.section-header {
  margin-bottom: 24px;
  padding-bottom: 14px;
  border-bottom: 2px solid #e2e8f0;
}

.section-title {
  font-size: 22pt;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.15;
  letter-spacing: -0.3px;
}

.section-intro {
  font-size: 10.5pt;
  color: #475569;
  margin-top: 10px;
  line-height: 1.7;
}

h2 {
  font-size: 14pt;
  font-weight: 700;
  color: #1e1b4b;
  margin-top: 28px;
  margin-bottom: 10px;
  padding-left: 10px;
  border-left: 3px solid #818cf8;
}

h3 {
  font-size: 11.5pt;
  font-weight: 700;
  color: #312e81;
  margin-top: 18px;
  margin-bottom: 8px;
}

p { margin-bottom: 10px; color: #334155; font-size: 11pt; }

/* ---- CALLOUT ---- */
.callout {
  background: #f8f7ff;
  border-left: 3px solid #818cf8;
  border-radius: 0 8px 8px 0;
  padding: 14px 16px;
  margin: 16px 0;
}
.callout.red { background: #fff5f5; border-left-color: #f87171; }
.callout.green { background: #f0fdf4; border-left-color: #4ade80; }
.callout.amber { background: #fffbeb; border-left-color: #fbbf24; }
.callout p { margin: 0; font-size: 10.5pt; }

/* ---- STAT BOXES ---- */
.stat-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 16px 0;
}

.stat-box {
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
  border-radius: 10px;
  padding: 16px;
  page-break-inside: avoid;
}

.stat-box .n {
  font-size: 22pt;
  font-weight: 800;
  color: #a5b4fc;
  display: block;
  line-height: 1.1;
}

.stat-box .l {
  font-size: 9.5pt;
  color: #94a3b8;
  margin-top: 4px;
}

.stat-box.light {
  background: #f8f7ff;
  border: 1.5px solid #e0e7ff;
}
.stat-box.light .n { color: #4f46e5; }
.stat-box.light .l { color: #64748b; }

/* ---- TABLES ---- */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0;
  font-size: 9.5pt;
}
thead tr { background: #1e1b4b; color: white; }
thead th {
  padding: 9px 10px;
  text-align: left;
  font-weight: 600;
  font-size: 8.5pt;
}
tbody tr:nth-child(even) { background: #f8f7ff; }
tbody td {
  padding: 8px 10px;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: top;
  font-size: 9.5pt;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 50px;
  font-size: 7.5pt;
  font-weight: 700;
}
.badge.red { background: #fee2e2; color: #dc2626; }
.badge.green { background: #dcfce7; color: #16a34a; }
.badge.amber { background: #fef3c7; color: #d97706; }
.badge.blue { background: #dbeafe; color: #2563eb; }

/* ---- LISTS ---- */
ul.checklist, ul.cross-list {
  list-style: none;
  padding: 0;
  margin: 8px 0 14px;
}
ul.checklist li, ul.cross-list li {
  padding: 5px 0 5px 22px;
  position: relative;
  font-size: 10.5pt;
  color: #374151;
  border-bottom: 1px solid #f1f5f9;
}
ul.checklist li::before { content: "✦"; position: absolute; left: 0; color: #818cf8; font-size: 8pt; top: 6px; }
ul.cross-list li::before { content: "✕"; position: absolute; left: 0; color: #f87171; font-size: 8pt; top: 6px; }

/* ---- QUOTE ---- */
.quote-block {
  border-left: 3px solid #c084fc;
  padding: 12px 16px;
  background: #faf5ff;
  border-radius: 0 8px 8px 0;
  margin: 16px 0;
  font-style: italic;
  font-size: 10.5pt;
  color: #4b5563;
}
.quote-src { font-style: normal; font-size: 8pt; color: #9ca3af; margin-top: 6px; font-weight: 600; }

/* ---- HIGHLIGHT BOX ---- */
.highlight-box {
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
  border-radius: 12px;
  padding: 20px;
  margin: 16px 0;
  page-break-inside: avoid;
}
.highlight-box h3 { color: #a5b4fc; font-size: 11.5pt; margin-top: 0; margin-bottom: 8px; }
.highlight-box p { color: #cbd5e1; font-size: 10pt; margin: 0; }

/* ---- OPPORTUNITY CARDS ---- */
.opp-card {
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  margin: 20px 0;
  page-break-inside: avoid;
  break-inside: avoid;
}

.opp-header { margin-bottom: 14px; }

.opp-rank-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.opp-rank {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: white;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  font-size: 14pt;
  font-weight: 800;
  text-align: center;
  line-height: 38px;
  flex-shrink: 0;
}

.opp-title {
  font-size: 13.5pt;
  font-weight: 800;
  color: #1e1b4b;
  letter-spacing: -0.2px;
}

.opp-tagline {
  font-size: 9.5pt;
  color: #64748b;
  margin-bottom: 14px;
  font-style: italic;
}

.opp-meta-stack {
  background: #f8f7ff;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 14px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.meta-item .ml {
  font-size: 7.5pt;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  font-weight: 700;
  display: block;
}
.meta-item .mv {
  font-size: 10pt;
  font-weight: 700;
  color: #1e1b4b;
}

.opp-body p { font-size: 10.5pt; }

.sub-section {
  margin-top: 12px;
  background: #f8f7ff;
  border-radius: 8px;
  padding: 12px 14px;
  page-break-inside: avoid;
}
.sub-section h4 {
  font-size: 8.5pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: #64748b;
  margin-bottom: 6px;
}
.sub-section ul {
  list-style: none;
  padding: 0;
}
.sub-section ul li {
  padding: 4px 0 4px 16px;
  position: relative;
  font-size: 9.5pt;
  color: #374151;
  border-bottom: 1px solid #e2e8f0;
}
.sub-section ul li::before {
  content: "›";
  position: absolute;
  left: 0;
  color: #818cf8;
  font-weight: 700;
}
.sub-section ul li:last-child { border-bottom: none; }

.opp-score {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}
.score-label { font-size: 8pt; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.8px; white-space: nowrap; }
.score-bar-wrap { flex: 1; background: #e2e8f0; border-radius: 10px; height: 7px; overflow: hidden; }
.score-bar { height: 100%; border-radius: 10px; background: linear-gradient(90deg, #4f46e5, #7c3aed); }
.score-num { font-size: 11pt; font-weight: 800; color: #4f46e5; white-space: nowrap; }

.divider { height: 1.5px; background: linear-gradient(90deg, #818cf8, transparent); margin: 20px 0; border-radius: 2px; }

/* Platform card */
.platform-card {
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  margin: 10px 0;
  page-break-inside: avoid;
}
.platform-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.platform-name { font-size: 11pt; font-weight: 700; color: #1e1b4b; }
.rating-bad { background: #fee2e2; color: #dc2626; font-size: 8pt; font-weight: 700; padding: 3px 10px; border-radius: 50px; }
.rating-ok  { background: #fef3c7; color: #b45309; font-size: 8pt; font-weight: 700; padding: 3px 10px; border-radius: 50px; }
.platform-card p { font-size: 9.5pt; color: #475569; margin: 0; }
</style>
</head>
<body>

<!-- ==================== COVER ==================== -->
<div class="cover page-break">
  <div class="cover-badge">Investigación de Mercado · Mayo 2026</div>
  <h1>El Mundo del<br/><span>Trading</span><br/>2025–2026</h1>
  <p class="cover-sub">Mapa exhaustivo de problemas, brechas y oportunidades de producto en el ecosistema del trading retail global</p>
  <div class="cover-line"></div>
  <div class="cover-stats">
    <div class="cstat"><span class="n">6</span><span class="l">Áreas investigadas</span></div>
    <div class="cstat"><span class="n">150+</span><span class="l">Fuentes consultadas</span></div>
    <div class="cstat"><span class="n">10</span><span class="l">Oportunidades identificadas</span></div>
    <div class="cstat"><span class="n">$51.8B</span><span class="l">VC en fintech 2025</span></div>
  </div>
  <div class="cover-line"></div>
  <p class="cover-meta">Documento Confidencial · Uso Estratégico Interno</p>
</div>

<!-- ==================== TOC ==================== -->
<div class="toc-page page-break">
  <div class="eyebrow">Navegación</div>
  <div class="page-title">Índice</div>
  <p class="page-intro">Investigación en 6 dimensiones del ecosistema trading retail global</p>

  <div class="toc-item main"><span class="toc-num">01</span><span class="toc-text">Resumen Ejecutivo</span></div>
  <div class="toc-item main"><span class="toc-num">02</span><span class="toc-text">El Ecosistema del Trading Retail Hoy</span></div>
  <div class="toc-item main"><span class="toc-num">03</span><span class="toc-text">Los 8 Grandes Problemas del Trader</span></div>
  <div class="toc-item main"><span class="toc-num">04</span><span class="toc-text">Análisis de Plataformas y Sus Fallas</span></div>
  <div class="toc-item main"><span class="toc-num">05</span><span class="toc-text">Educación y Psicología del Trader</span></div>
  <div class="toc-item main"><span class="toc-num">06</span><span class="toc-text">Algo Trading: La Promesa Rota</span></div>
  <div class="toc-item main"><span class="toc-num">07</span><span class="toc-text">Impuestos y Compliance</span></div>
  <div class="toc-item main"><span class="toc-num">08</span><span class="toc-text">Tendencias Emergentes 2025–2026</span></div>
  <div class="toc-item main" style="padding:10px 0; border-bottom: 2px solid #818cf8;">
    <span class="toc-num" style="color:#4f46e5; font-size:11pt; font-weight:900;">09</span>
    <span class="toc-text" style="font-size:13pt; color:#1e1b4b; font-weight:900;">Las 10 Oportunidades de Producto</span>
  </div>
  <div class="toc-item opp-item"><span class="toc-num" style="color:#64748b; font-size:8pt;">#1</span><span class="toc-text">AI Coach Conductual Personalizado — 9.5/10</span></div>
  <div class="toc-item opp-item"><span class="toc-num" style="color:#64748b; font-size:8pt;">#2</span><span class="toc-text">Signal Intelligence Hub Unificado — 9.0/10</span></div>
  <div class="toc-item opp-item"><span class="toc-num" style="color:#64748b; font-size:8pt;">#3</span><span class="toc-text">TaxTrader AI: Compliance en Tiempo Real — 8.8/10</span></div>
  <div class="toc-item opp-item"><span class="toc-num" style="color:#64748b; font-size:8pt;">#4</span><span class="toc-text">BacktestPro: Backtesting Honesto Sin Código — 8.5/10</span></div>
  <div class="toc-item opp-item"><span class="toc-num" style="color:#64748b; font-size:8pt;">#5</span><span class="toc-text">PortfolioX: El Bloomberg del Trader Retail — 8.3/10</span></div>
  <div class="toc-item opp-item"><span class="toc-num" style="color:#64748b; font-size:8pt;">#6</span><span class="toc-text">0DTE Master: Plataforma Nativa para Opciones del Día — 8.2/10</span></div>
  <div class="toc-item opp-item"><span class="toc-num" style="color:#64748b; font-size:8pt;">#7</span><span class="toc-text">PredictionEdge: Analytics para Prediction Markets — 8.0/10</span></div>
  <div class="toc-item opp-item"><span class="toc-num" style="color:#64748b; font-size:8pt;">#8</span><span class="toc-text">TradingDuolingo: Educación Gamificada Adaptativa — 7.5/10</span></div>
  <div class="toc-item opp-item"><span class="toc-num" style="color:#64748b; font-size:8pt;">#9</span><span class="toc-text">CryptoDeriv Risk Hub — 7.2/10</span></div>
  <div class="toc-item opp-item"><span class="toc-num" style="color:#64748b; font-size:8pt;">#10</span><span class="toc-text">PropTrust: La Prop Firm Transparente — 6.8/10</span></div>
  <div class="toc-item main"><span class="toc-num">10</span><span class="toc-text">Recomendaciones Estratégicas y Conclusión</span></div>
</div>


<!-- ==================== RESUMEN EJECUTIVO ==================== -->
<div class="section-page page-break">
  <div class="section-header">
    <div class="eyebrow">Sección 01</div>
    <div class="section-title">Resumen Ejecutivo</div>
  </div>

  <p>Después de analizar más de 150 fuentes — estudios académicos, datos de reguladores, Reddit, Trustpilot, reportes de VC, legislación vigente y documentación técnica de plataformas — emerge una sola conclusión central e inequívoca.</p>

  <div class="highlight-box no-break">
    <h3>La Tesis Central</h3>
    <p>El mundo del trading retail está experimentando el crecimiento más grande de su historia ($302B en flujos netos en 2025, +53% YoY), pero sus herramientas están sistemáticamente rotas, fragmentadas o son directamente fraudulentas. El 80–90% pierde dinero — no por malas estrategias, sino por falta de herramientas correctas. Cada dólar que pierde un trader retail es una oportunidad de producto sin explotar.</p>
  </div>

  <div class="stat-stack">
    <div class="stat-box"><span class="n">80–90%</span><span class="l">de traders retail pierden dinero en su primer año — documentado en 27 años de estudios globales</span></div>
    <div class="stat-box"><span class="n">$302B</span><span class="l">en flujos netos de retail hacia acciones de EE.UU. en 2025 (+53% vs 2024)</span></div>
    <div class="stat-box"><span class="n">1.9 / 5</span><span class="l">rating de TradingView en Trustpilot — el rey del charting es profundamente odiado</span></div>
  </div>

  <p>Este documento identifica <strong>10 oportunidades de producto concretas</strong>, ordenadas por potencial de impacto y viabilidad. Cada una basada en gaps documentados, no hipotéticos.</p>

  <div class="callout green no-break">
    <p><strong>El patrón repetido:</strong> Ninguna oportunidad requiere inventar tecnología nueva. Todas requieren democratizar herramientas que solo existen para traders institucionales. Bloomberg vale $24,000/año — ¿quién hace la versión de $99/mes?</p>
  </div>
</div>


<!-- ==================== ECOSISTEMA HOY ==================== -->
<div class="section-page page-break">
  <div class="section-header">
    <div class="eyebrow">Sección 02</div>
    <div class="section-title">El Ecosistema del Trading Retail Hoy</div>
    <p class="section-intro">El mercado retail nunca ha sido más grande ni más activo. Y al mismo tiempo, nunca ha habido mayor desajuste entre lo que los traders necesitan y lo que las herramientas entregan.</p>
  </div>

  <h2>Magnitud del Mercado</h2>
  <div class="stat-stack">
    <div class="stat-box light"><span class="n">35%</span><span class="l">del volumen diario de acciones en EE.UU. es retail — récord histórico en abril 2025</span></div>
    <div class="stat-box light"><span class="n">$85.7T</span><span class="l">en volumen de derivados crypto en 2025 (perpetual swaps = 78%)</span></div>
    <div class="stat-box light"><span class="n">60%+</span><span class="l">del volumen de opciones en EE.UU. son contratos 0DTE (vencimiento el mismo día)</span></div>
    <div class="stat-box light"><span class="n">67%</span><span class="l">de inversores retail ya usa herramientas de IA (vs. 38% en 2023)</span></div>
  </div>

  <h2>Tamaños de Mercado por Segmento</h2>
  <table>
    <thead><tr><th>Segmento</th><th>2025</th><th>Proyección</th><th>CAGR</th></tr></thead>
    <tbody>
      <tr><td><strong>Software de trading</strong></td><td>$6.5B</td><td>$15B (2033)</td><td>8.5%</td></tr>
      <tr><td><strong>Algo trading retail</strong></td><td>$3.55B</td><td>$7.18B (2030)</td><td>10.8%</td></tr>
      <tr><td><strong>Educación de trading</strong></td><td>$1.35B</td><td>$3.72B (2033)</td><td>12%</td></tr>
      <tr><td><strong>Social/copy trading</strong></td><td>$3.82B</td><td>$9.1B (2035)</td><td>12%</td></tr>
      <tr><td><strong>NLP / sentimiento</strong></td><td>$2.81B</td><td>$9.67B (2034)</td><td>14.8%</td></tr>
      <tr><td><strong>Prediction markets</strong></td><td>$44B vol.</td><td>Crecimiento 10x</td><td>+1,000% en 2025</td></tr>
    </tbody>
  </table>

  <h2>La Paradoja Central</h2>
  <div class="callout amber no-break">
    <p><strong>El gap real:</strong> Los traders retail no necesitan herramientas <em>diferentes</em> a las institucionales — necesitan las <em>mismas</em> a un precio accesible. Bloomberg $24K/año. Alternative data $50K–$500K/año. Risk management teams. NLP de earnings en tiempo real. Ninguno de estos está disponible a nivel retail. Cada área investigada confirma este mismo hallazgo desde ángulos distintos.</p>
  </div>

  <h3>Lo que tiene el Trader Retail</h3>
  <ul class="cross-list">
    <li>Plataformas con UX de los años 90 (MetaTrader, TWS)</li>
    <li>Backtesting sin modelado realista de slippage</li>
    <li>Datos con 15–20 minutos de retraso en tier gratuito</li>
    <li>Journal en Excel (la mayoría)</li>
    <li>Educación de YouTube gurus sin track record verificable</li>
    <li>Impuestos que reconciliar manualmente entre brokers</li>
  </ul>

  <h3>Lo que tiene el Trader Institucional</h3>
  <ul class="checklist">
    <li>Bloomberg Terminal ($24,000/año)</li>
    <li>Alternative data (satélite, tarjetas de crédito): $50K–$500K/año</li>
    <li>Smart Order Routing hacia dark pools</li>
    <li>Equipos de risk management dedicados</li>
    <li>NLP de earnings calls en tiempo real</li>
    <li>Reconciliación automática cross-asset</li>
  </ul>
</div>


<!-- ==================== 8 GRANDES PROBLEMAS ==================== -->
<div class="section-page page-break">
  <div class="section-header">
    <div class="eyebrow">Sección 03</div>
    <div class="section-title">Los 8 Grandes Problemas del Trader Retail</div>
    <p class="section-intro">Compilados de más de 150 fuentes — 27 años de datos, foros de Reddit, análisis de reguladores, y más de 1,000 reseñas de software.</p>
  </div>

  <h2>Problema #1 — Desventaja Estructural Sistémica</h2>
  <p>Retail compite contra instituciones con acceso a alternative data, Smart Order Routing hacia dark pools (que manejan el 38–42% del volumen en EE.UU.), y algoritmos que ejecutan en microsegundos. El slippage agregado por esta asimetría superó <strong>$2.7 billones globalmente en 2024</strong> (+34% YoY).</p>

  <h2>Problema #2 — Herramientas Fragmentadas y Mediocres</h2>
  <p>Un trader activo usa 4–6 herramientas separadas que no se comunican: broker, charting, journal, impuestos, options flow, Excel para portfolio. Ninguna plataforma principal supera 2/5 en Trustpilot. El mercado está lleno de usuarios resignados, no de fans leales.</p>

  <div class="callout red no-break">
    <p><strong>Dato:</strong> El 42% de quejas en 2025 eran por interfaces móviles deficientes. El 33% por falla de customer support. Solo el 23% de traders activos considera que sus alertas son consistentemente accionables.</p>
  </div>

  <h2>Problema #3 — El 80–90% Pierde: No es la Estrategia</h2>
  <p>Un estudio de 25,000+ traders halló que el <strong>65% tiene win rate mayor al 50%</strong> pero el 82% de ellos pierde dinero. Sus ganadores promedian +1.2% y sus perdedores -2.8%. El problema no es la estrategia — es el comportamiento al ejecutarla. No existe ninguna herramienta que intervenga este problema en tiempo real.</p>

  <div class="quote-block no-break">
    "El 85% de las cuentas que explotan siguen el mismo patrón: ganancias → sobreconfianza → posiciones más grandes → drawdown → pánico → revenge trading → cuenta explotada."
    <div class="quote-src">— Análisis de estudios conductuales, múltiples fuentes académicas</div>
  </div>

  <h2>Problema #4 — La Educación es un Ecosistema de Fraude</h2>
  <p>La FTC encontró que Online Trading Academy vendía cursos de $19,000–$50,000 con <em>"ninguna base para sus afirmaciones de ganancias."</em> YouTube está dominado por gurus cuyo negocio real es vender cursos, no tradear. No existe ninguna plataforma con currículum adaptativo, track records verificados de instructores, y feedback personalizado.</p>

  <h2>Problema #5 — El Algo Trading Retail es un Fracaso</h2>
  <p>El 90% de traders algorítmicos no supera el buy-and-hold. TradingView tiene latencias de webhook de 25–45 segundos, los backtests no modelan slippage real, y el path de idea → estrategia en vivo sigue requiriendo 6–18 meses de aprendizaje técnico.</p>

  <h2>Problema #6 — Los Impuestos Son un Laberinto</h2>
  <p>El Form 1099-DA (nuevo en 2025) solo reporta gross proceeds, sin cost basis. Las wash sale rules aplican a TODAS las cuentas del contribuyente pero ningún broker las rastrea de forma cruzada. No existe una sola plataforma que maneje equities + options + crypto + forex en un sistema unificado de tax tracking en tiempo real.</p>

  <h2>Problema #7 — El Portfolio Real es Invisible</h2>
  <p>El trader activo tiene cuentas en 3–5 plataformas. Nadie le muestra su P&amp;L real consolidado, exposición neta, correlación entre posiciones o riesgo total en tiempo real. Bloomberg hace esto por $24,000/año. No existe versión retail.</p>

  <h2>Problema #8 — El Prop Trading es un Ecosistema de Engaño</h2>
  <p>Entre 2024 y 2025, <strong>80–100 prop firms colapsaron</strong>. El 93% de traders nunca recibe un pago. La mayoría de "funded accounts" son cuentas demo. Las reglas cambian retroactivamente. FundingTicks cerró en enero 2026 aplicando nuevas reglas a cuentas activas sin previo aviso.</p>
</div>


<!-- ==================== PLATAFORMAS ==================== -->
<div class="section-page page-break">
  <div class="section-header">
    <div class="eyebrow">Sección 04</div>
    <div class="section-title">Plataformas Existentes y Sus Fallas</div>
    <p class="section-intro">Los ratings reales, las quejas más documentadas, y los gaps que dejan abiertos.</p>
  </div>

  <div class="platform-card no-break">
    <div class="platform-top">
      <span class="platform-name">TradingView</span>
      <span class="rating-bad">Trustpilot: 1.9/5</span>
    </div>
    <p>El rey del charting retail — y el más odiado. Solo 1 alerta activa en el plan gratuito. El backtester Pine Script no tiene walk-forward, Monte Carlo, ni slippage realista. Alertas con 20–30 segundos de delay (inútil para day trading). Sin trailing stops, sin journal integrado. Precios suben sin mejoras proporcionales. Support solo por chatbot.</p>
  </div>

  <div class="platform-card no-break">
    <div class="platform-top">
      <span class="platform-name">Thinkorswim (Schwab)</span>
      <span class="rating-bad">Degrado severo post-adquisición</span>
    </div>
    <p>Se desconecta cada viernes al cierre. Órdenes ejecutan solo ~50% del tiempo. Sin API Python, sin crypto, sin historial de Greeks descargable, sin journal. Funcionalidad "On Demand" rota hace más de 4 años. Representatives entrenados para desviar responsabilidad.</p>
  </div>

  <div class="platform-card no-break">
    <div class="platform-top">
      <span class="platform-name">Interactive Brokers</span>
      <span class="rating-ok">Poderoso pero hostil</span>
    </div>
    <p>Interfaz descrita como "algo de los años 90." Datos real-time cuestan $125/mes adicionales. App móvil sin paridad con desktop. Curva de aprendizaje de semanas. Retiros sin consentimiento de cuentas de retiro documentados.</p>
  </div>

  <div class="platform-card no-break">
    <div class="platform-top">
      <span class="platform-name">Webull</span>
      <span class="rating-bad">Trustpilot: 1.3/5 · Multa FINRA $1.6M (2025)</span>
    </div>
    <p>Demoras de retiro son la queja #1. Data breach confirmado en 2025. Cierres de cuentas sin aviso. Cotizaciones retrasadas por defecto sin comunicarlo. Órdenes que no ejecutan en condiciones volátiles.</p>
  </div>

  <h2>Herramientas de Journal</h2>
  <table>
    <thead><tr><th>Herramienta</th><th>Gap Crítico</th><th>Precio</th></tr></thead>
    <tbody>
      <tr><td><strong>Edgewonk</strong></td><td>Sin app móvil; solo descargable; integraciones limitadas</td><td>$197/año</td></tr>
      <tr><td><strong>TraderSync</strong></td><td>App móvil 2.7/5; sin framework de psicología; caro</td><td>$360–960/año</td></tr>
      <tr><td><strong>Tradervue</strong></td><td>Sin análisis psicológico; sin MetaTrader sync; sin móvil</td><td>Gratis + paid</td></tr>
    </tbody>
  </table>

  <div class="callout no-break">
    <p><strong>Gap universal de todos los journals:</strong> Identifican el problema ("haces revenge trading") pero ninguno ayuda a resolverlo. Todos son reactivos — ninguno interviene en tiempo real antes del trade.</p>
  </div>

  <h2>Software Fiscal</h2>
  <table>
    <thead><tr><th>Software</th><th>Problema Central</th><th>Lo que NO cubre</th></tr></thead>
    <tbody>
      <tr><td><strong>TaxBit</strong></td><td>Salió del mercado retail en 2023</td><td>Todo el segmento retail</td></tr>
      <tr><td><strong>Koinly</strong></td><td>Mislabels, sync errors, DeFi incompleto</td><td>Equities, options, forex</td></tr>
      <tr><td><strong>TradeLog</strong></td><td>Reconoce que no puede hacer Form 8949 exacto</td><td>Crypto; límite duro de registros</td></tr>
      <tr><td><strong>GainsKeeper</strong></td><td>Errores en cost basis negativo documentados</td><td>Crypto, DeFi, forex</td></tr>
    </tbody>
  </table>
</div>


<!-- ==================== EDUCACIÓN Y PSICOLOGÍA ==================== -->
<div class="section-page page-break">
  <div class="section-header">
    <div class="eyebrow">Sección 05</div>
    <div class="section-title">Educación y Psicología del Trader</div>
    <p class="section-intro">El gap más ignorado y más costoso del ecosistema. Los traders saben qué deben hacer — simplemente no pueden ejecutarlo bajo presión real.</p>
  </div>

  <div class="stat-stack">
    <div class="stat-box"><span class="n">97%</span><span class="l">de day traders que persisten 300+ días pierde dinero (estudio de 300K traders en Brasil)</span></div>
    <div class="stat-box"><span class="n">65%</span><span class="l">de traders tiene win rate mayor al 50% — pero el 82% de ellos aún pierde dinero en total</span></div>
    <div class="stat-box"><span class="n">6.1%</span><span class="l">de underperformance anual vs. S&amp;P 500 por comportamiento (Dalbar, 20 años de datos)</span></div>
  </div>

  <h2>El Gap de Simulación</h2>
  <p>El Chartered Market Technician Association documentó que los traders experimentan <strong>340% más hormonas de estrés durante trading real vs. paper trading.</strong> El cerebro procesa decisiones de forma fundamentalmente diferente cuando no hay dinero real en juego. Ningún simulador reproduce este estado. La transición paper → live tiene la mayor tasa de fracaso de todo el proceso de aprendizaje.</p>

  <h2>Lo que Necesitan vs. Lo que Existe</h2>
  <h3>Lo que necesitan y no tienen:</h3>
  <ul class="cross-list">
    <li>Feedback personalizado basado en su propio historial de trades</li>
    <li>Detección de sesgos conductuales ANTES de entrar al trade</li>
    <li>Simulación con presión emocional real (no paper trading plano)</li>
    <li>Curriculum adaptativo conectado a sus patrones específicos de fallo</li>
    <li>Coaching accesible (menos de $50/mes)</li>
    <li>Conexión entre diagnóstico de problema → remedio concreto</li>
  </ul>

  <h3>Lo que existe actualmente:</h3>
  <ul class="cross-list">
    <li>Cursos estáticos genéricos (Udemy, Investopedia) — sin feedback</li>
    <li>YouTube gurus con P&amp;L no verificado — modelo de negocio: vender cursos</li>
    <li>Journals post-hoc — reactivos, no preventivos</li>
    <li>Coaching profesional a $3,000–$15,000 por programa</li>
    <li>Ninguna herramienta conecta diagnóstico con remedio</li>
  </ul>

  <h2>Mercado de Educación: $1.35B → $3.72B (12% CAGR)</h2>
  <p>Las plataformas de aprendizaje adaptativo crecen al 18% CAGR y han demostrado mejorar el rendimiento del estudiante en el 59% de los estudios. Esta tecnología <strong>no ha sido aplicada a la educación de trading</strong> de ninguna manera significativa en ninguna plataforma existente.</p>
</div>


<!-- ==================== ALGO TRADING ==================== -->
<div class="section-page page-break">
  <div class="section-header">
    <div class="eyebrow">Sección 06</div>
    <div class="section-title">Algo Trading: La Promesa Rota</div>
    <p class="section-intro">El mercado de algo trading retail vale $3.55B y crece al 10.8% anual. Pero el 90% de traders algorítmicos no supera el buy-and-hold en su primer año.</p>
  </div>

  <h2>El Pipeline Roto: De Idea a Ejecución</h2>
  <table>
    <thead><tr><th>Etapa</th><th>El Problema</th><th>Severidad</th></tr></thead>
    <tbody>
      <tr><td><strong>Backtesting</strong></td><td>Sin walk-forward, sin Monte Carlo, sin slippage real; overfitting epidémico</td><td><span class="badge red">Crítica</span></td></tr>
      <tr><td><strong>Datos</strong></td><td>Datos tick prohibitivos; opciones histórico caro; gaps en cobertura</td><td><span class="badge red">Crítica</span></td></tr>
      <tr><td><strong>Codificación</strong></td><td>Requiere Python/C# — excluye al 80% de traders retail</td><td><span class="badge red">Crítica</span></td></tr>
      <tr><td><strong>Broker connectivity</strong></td><td>Webhooks TradingView = 25–45 seg de latencia; inútil para scalping</td><td><span class="badge red">Crítica</span></td></tr>
      <tr><td><strong>Monitoreo en vivo</strong></td><td>Sin dashboard cross-strategy; sin detección de régimen; sin kill switch</td><td><span class="badge red">Crítica</span></td></tr>
    </tbody>
  </table>

  <div class="callout green no-break">
    <p><strong>Dato importante 2026:</strong> Alpaca (la infraestructura API para trading algorítmico, $100M ARR, $52M Series C) implementó un MCP Server que permite conectar agentes de IA como Claude o ChatGPT directamente a ejecución de trades en vivo. Esta es infraestructura nueva que abre posibilidades de productos que hace un año no eran técnicamente posibles.</p>
  </div>

  <h2>El Problema de Copy Trading</h2>
  <p>El mercado de social/copy trading vale $3.82B. Pero eToro tiene quejas masivas de inestabilidad (Trustpilot negativo), Zulutrade tiene bugs no resueltos desde hace más de un año, y el problema estructural es que sus leaderboards están sesgados por supervivencia y no muestran métricas ajustadas por riesgo. El 93% de traders en prop firms nunca recibe un pago.</p>
</div>


<!-- ==================== IMPUESTOS ==================== -->
<div class="section-page page-break">
  <div class="section-header">
    <div class="eyebrow">Sección 07</div>
    <div class="section-title">Impuestos y Compliance</div>
    <p class="section-intro">2025–2026: el mayor cambio regulatorio en fiscal de traders desde décadas. La complejidad explotó — y las herramientas no han seguido el ritmo.</p>
  </div>

  <h2>Los Cambios Regulatorios que Crean Oportunidad</h2>
  <ul class="checklist">
    <li><strong>Formulario 1099-DA (nuevo en 2025):</strong> Solo reporta gross proceeds — sin cost basis. Si el IRS ve ganancias sin base reportada, asume que todo es ganancia.</li>
    <li><strong>Regla de cost basis por wallet:</strong> El IRS eliminó el método universal. Ahora se requiere tracking wallet-por-wallet.</li>
    <li><strong>Eliminación del PDT Rule (junio 2026):</strong> El requisito de $25,000 para day trading fue eliminado. Millones de nuevos day traders necesitan tax tools.</li>
    <li><strong>IRS AI Audit 2026:</strong> Detección de IA específicamente para activos digitales complejos y activos extranjeros.</li>
    <li><strong>CARF (OCDE):</strong> EE.UU. comprometido a implementar marco de reporte crypto para 2029.</li>
  </ul>

  <h2>Los Gaps Sin Solución</h2>
  <div class="stat-stack">
    <div class="stat-box light"><span class="n">0</span><span class="l">plataformas retail que rastrean wash sales cross-account en tiempo real (el IRS lo requiere)</span></div>
    <div class="stat-box light"><span class="n">0</span><span class="l">herramientas que manejan equities + options + crypto + forex en un sistema unificado</span></div>
    <div class="stat-box light"><span class="n">15%</span><span class="l">tasa de error en reconciliación manual de portfolios multi-cuenta</span></div>
  </div>
</div>


<!-- ==================== TENDENCIAS ==================== -->
<div class="section-page page-break">
  <div class="section-header">
    <div class="eyebrow">Sección 08</div>
    <div class="section-title">Tendencias Emergentes 2025–2026</div>
    <p class="section-intro">Las fuerzas que están redibujando el mercado y que definen dónde está la ventana de oportunidad hoy.</p>
  </div>

  <h2>IA en Trading: Lo Real vs. Lo Exagerado</h2>
  <h3>Genuinamente útil:</h3>
  <ul class="checklist">
    <li>Backtesting asistido por IA (TrendSpider)</li>
    <li>Screeners AI (Trade Ideas: 4.5/5 en StockBrokers.com)</li>
    <li>Strategy builders no-code (Composer: $5.35M levantado)</li>
    <li>Enforcement de disciplina (rules-based execution)</li>
    <li>NLP de earnings calls (mercado $8.6B → $80B al 25% CAGR)</li>
  </ul>
  <h3>Overhyped / No funciona:</h3>
  <ul class="cross-list">
    <li>Bots de trading "que generan retornos" (fraude documentado)</li>
    <li>ChatGPT para señales de trading (no tiene datos real-time)</li>
    <li>AI general-purpose para investing (80% sin cambio o peor)</li>
  </ul>

  <h2>Mercados de Predicción: El Mercado que Explotó</h2>
  <div class="stat-stack">
    <div class="stat-box"><span class="n">$44B</span><span class="l">en volumen de predicción markets en 2025 (+1,000% YoY)</span></div>
    <div class="stat-box"><span class="n">$11B</span><span class="l">valoración de Kalshi — levantó $1B en Q1 2026 (Coatue)</span></div>
    <div class="stat-box"><span class="n">$8B</span><span class="l">pre-money de Polymarket — respaldado por ICE (operador de NYSE)</span></div>
  </div>
  <p>Kalshi y Polymarket forman un duopolio global. <strong>No existe ninguna herramienta analítica para estos mercados.</strong> Ventana de first-mover: 12–18 meses.</p>

  <h2>Opciones 0DTE: El Segmento de Mayor Crecimiento</h2>
  <p>Los contratos que vencen el mismo día representan más del <strong>60% de todo el volumen de opciones en EE.UU.</strong> en 2025. Es la categoría de más rápido crecimiento. Y no existe ninguna plataforma diseñada específicamente para 0DTE con gamma visualization en tiempo real, dealer positioning e IV crush tracking.</p>

  <h2>VC — Dónde Apuestan los Grandes en 2025–2026</h2>
  <table>
    <thead><tr><th>Área</th><th>Señal de VC</th></tr></thead>
    <tbody>
      <tr><td><strong>Prediction markets</strong></td><td>Kalshi: $1B @ $11B — apuesta más grande de Q1 2026</td></tr>
      <tr><td><strong>API brokerage</strong></td><td>Alpaca: $52M Series C, $100M ARR</td></tr>
      <tr><td><strong>AI fintech vertical</strong></td><td>a16z: 32 deals en 2025 (+50%); AI = 58% de toda inversión fintech</td></tr>
      <tr><td><strong>Emerging markets</strong></td><td>Indonesia y Vietnam: top 10 global en nuevas cuentas forex</td></tr>
    </tbody>
  </table>
</div>


<!-- ==================== OPORTUNIDADES ==================== -->
<div class="section-page page-break">
  <div class="section-header">
    <div class="eyebrow">Sección 09 — El Núcleo del Documento</div>
    <div class="section-title">Las 10 Oportunidades de Producto</div>
    <p class="section-intro">Clasificadas por: Tamaño de mercado × Severidad del gap × Viabilidad técnica × Velocidad de monetización. Cada una con evidencia documentada de la demanda.</p>
  </div>

  <!-- OPP 1 -->
  <div class="opp-card">
    <div class="opp-header">
      <div class="opp-rank-row">
        <div class="opp-rank">1</div>
        <div class="opp-title">AI Coach Conductual Personalizado</div>
      </div>
      <div class="opp-tagline">El terapeuta de trading que cada trader necesita pero no puede pagar</div>
    </div>
    <div class="opp-meta-stack">
      <div class="meta-item"><span class="ml">TAM</span><span class="mv">$1.35B → $3.72B</span></div>
      <div class="meta-item"><span class="ml">Revenue</span><span class="mv">$29–79/mes SaaS</span></div>
      <div class="meta-item"><span class="ml">Complejidad</span><span class="mv">Media</span></div>
      <div class="meta-item"><span class="ml">Competencia</span><span class="mv">Débil/Fragmentada</span></div>
    </div>
    <div class="opp-body">
      <p><strong>El problema:</strong> El 80–90% de traders pierde dinero no por malas estrategias sino por comportamiento — revenge trading, FOMO, loss aversion, sobreconfianza. El coaching profesional cuesta $3,000–$15,000 por programa. Completamente inaccesible para el retail promedio.</p>
      <p><strong>El producto:</strong> Conecta con los brokers del trader vía API, importa su historial completo, y usa IA para:</p>
      <ul class="checklist">
        <li>Identificar patrones conductuales específicos del usuario</li>
        <li>Alertar ANTES de que coloque un trade de riesgo conductual alto</li>
        <li>Prescribir intervenciones de psicología conductual para sus sesgos identificados</li>
        <li>Gamificar la adherencia al plan (streaks de disciplina, no de P&amp;L)</li>
      </ul>
      <div class="sub-section no-break">
        <h4>Por Qué Gana</h4>
        <ul>
          <li>El gap es completamente documentado y cuantificado</li>
          <li>No compite con brokers — los necesita (win-win)</li>
          <li>Dartmouth study: tracking emocional = +23% en rentabilidad</li>
          <li>Mercado de plataformas adaptativas crece 18% CAGR</li>
          <li>Alta retención: mejora progresiva con el tiempo</li>
        </ul>
      </div>
      <div class="sub-section no-break">
        <h4>Competencia Actual — Por Qué es Débil</h4>
        <ul>
          <li>Edgewonk: solo post-hoc, sin intervención antes del trade</li>
          <li>TraderSync "Cypher AI": genérico, sin framework conductual</li>
          <li>Plancana: early stage, sin tracción significativa</li>
          <li>NINGUNO interviene en tiempo real antes del trade</li>
        </ul>
      </div>
    </div>
    <div class="opp-score">
      <span class="score-label">Score</span>
      <div class="score-bar-wrap"><div class="score-bar" style="width:95%"></div></div>
      <span class="score-num">9.5/10</span>
    </div>
  </div>

  <!-- OPP 2 -->
  <div class="opp-card">
    <div class="opp-header">
      <div class="opp-rank-row">
        <div class="opp-rank">2</div>
        <div class="opp-title">Signal Intelligence Hub Unificado</div>
      </div>
      <div class="opp-tagline">Dark pool + options flow + insiders + congresistas — en un solo feed con ranking por IA</div>
    </div>
    <div class="opp-meta-stack">
      <div class="meta-item"><span class="ml">TAM</span><span class="mv">$300M+ directo</span></div>
      <div class="meta-item"><span class="ml">Revenue</span><span class="mv">$79–149/mes</span></div>
      <div class="meta-item"><span class="ml">Complejidad</span><span class="mv">Media-Alta</span></div>
      <div class="meta-item"><span class="ml">Competencia</span><span class="mv">Fragmentada</span></div>
    </div>
    <div class="opp-body">
      <p><strong>El problema:</strong> Dark pools = 38–42% del volumen de acciones en EE.UU. Options flow, dark pool prints, trading de congresistas, filings de insiders y short interest son datos públicos — pero fragmentados en 5–8 herramientas que cuestan $100–$300/mes cada una. Los traders que usan todas gastan hasta $1,500/mes y aún correlacionan los datos manualmente.</p>
      <p><strong>El producto:</strong> Una plataforma que agrega todo en tiempo real y usa IA para rankear cada señal según su correlación histórica con movimientos de precio subsecuentes.</p>
      <div class="sub-section no-break">
        <h4>Por Qué Gana</h4>
        <ul>
          <li>Unusual Whales validó la demanda — levantó funding, comunidad activa</li>
          <li>La unificación en sí ya es el valor — nadie lo ha hecho</li>
          <li>El tracker de congresistas fue viral — demanda probada masivamente</li>
          <li>AI ranking crea ventaja competitiva que se entrena con el uso</li>
        </ul>
      </div>
      <div class="sub-section no-break">
        <h4>Competencia Actual</h4>
        <ul>
          <li>Unusual Whales: opciones + congresistas (sin dark pool unificado)</li>
          <li>FlowAlgo: solo options flow</li>
          <li>InsiderFinance: flow + dark pool, sin insiders/congresistas</li>
          <li>Todos: $100–300/mes por separado</li>
        </ul>
      </div>
    </div>
    <div class="opp-score">
      <span class="score-label">Score</span>
      <div class="score-bar-wrap"><div class="score-bar" style="width:90%"></div></div>
      <span class="score-num">9.0/10</span>
    </div>
  </div>

  <!-- OPP 3 -->
  <div class="opp-card">
    <div class="opp-header">
      <div class="opp-rank-row">
        <div class="opp-rank">3</div>
        <div class="opp-title">TaxTrader AI — Compliance en Tiempo Real</div>
      </div>
      <div class="opp-tagline">El problema fiscal de los traders activos resuelto de una vez</div>
    </div>
    <div class="opp-meta-stack">
      <div class="meta-item"><span class="ml">TAM</span><span class="mv">$2B+ software fiscal</span></div>
      <div class="meta-item"><span class="ml">Revenue</span><span class="mv">$199–499/año</span></div>
      <div class="meta-item"><span class="ml">Complejidad</span><span class="mv">Alta</span></div>
      <div class="meta-item"><span class="ml">Competencia</span><span class="mv">Muy débil</span></div>
    </div>
    <div class="opp-body">
      <p><strong>El problema:</strong> 2025 trajo el mayor cambio regulatorio en fiscal de traders desde décadas. Form 1099-DA solo reporta gross proceeds. Wash sale rules aplican a todas las cuentas pero ningún broker las rastrea de forma cruzada. No existe una sola plataforma que maneje equities + options + crypto + forex en un sistema unificado en tiempo real.</p>
      <p><strong>El producto:</strong> Conecta vía API a todos los brokers y exchanges. Rastrea wash sales cross-account en tiempo real. Alerta antes de que el trader ejecute un trade que violaría una wash sale. Genera documentación audit-ready automáticamente.</p>
      <div class="sub-section no-break">
        <h4>Por Qué Gana Ahora</h4>
        <ul>
          <li>2025–2026: mayor cambio regulatorio en años → demanda urgente</li>
          <li>Eliminación del PDT = nueva ola de day traders que necesitan tax tools</li>
          <li>IRS AI audit = riesgo creciente → traders pagan para protegerse</li>
          <li>Alta retención — una vez integrado, nadie lo desconecta</li>
        </ul>
      </div>
    </div>
    <div class="opp-score">
      <span class="score-label">Score</span>
      <div class="score-bar-wrap"><div class="score-bar" style="width:88%"></div></div>
      <span class="score-num">8.8/10</span>
    </div>
  </div>

  <!-- OPP 4 -->
  <div class="opp-card">
    <div class="opp-header">
      <div class="opp-rank-row">
        <div class="opp-rank">4</div>
        <div class="opp-title">BacktestPro — Backtesting Honesto Sin Código</div>
      </div>
      <div class="opp-tagline">Walk-forward, Monte Carlo y slippage real — sin escribir una línea de Python</div>
    </div>
    <div class="opp-meta-stack">
      <div class="meta-item"><span class="ml">TAM</span><span class="mv">Parte de $6.5B</span></div>
      <div class="meta-item"><span class="ml">Revenue</span><span class="mv">$29–199/mes</span></div>
      <div class="meta-item"><span class="ml">Complejidad</span><span class="mv">Media</span></div>
      <div class="meta-item"><span class="ml">Competencia</span><span class="mv">Débil en no-code</span></div>
    </div>
    <div class="opp-body">
      <p><strong>El problema:</strong> TradingView (1.9/5 en Trustpilot) no tiene walk-forward, Monte Carlo, ni slippage realista. TradeStation reporta fills erróneos en el 70% de los tests. Trade Ideas tiene solo 64 días de datos. QuantConnect requiere Python o C#. Los retail traders usan estrategias que nunca funcionarán en vivo y lo descubren perdiendo dinero real.</p>
      <p><strong>El producto:</strong> Plataforma no-code de backtesting con walk-forward optimization automático, Monte Carlo simulation, modelado realista de slippage, backtesting a nivel de portfolio, y un "Honesty Score" que detecta overfitting explícitamente.</p>
    </div>
    <div class="opp-score">
      <span class="score-label">Score</span>
      <div class="score-bar-wrap"><div class="score-bar" style="width:85%"></div></div>
      <span class="score-num">8.5/10</span>
    </div>
  </div>

  <!-- OPP 5 -->
  <div class="opp-card">
    <div class="opp-header">
      <div class="opp-rank-row">
        <div class="opp-rank">5</div>
        <div class="opp-title">PortfolioX — El Bloomberg del Trader Retail</div>
      </div>
      <div class="opp-tagline">P&amp;L real, riesgo, exposición y tax — cruzado, en tiempo real, en una pantalla</div>
    </div>
    <div class="opp-meta-stack">
      <div class="meta-item"><span class="ml">TAM</span><span class="mv">Decenas de M de traders</span></div>
      <div class="meta-item"><span class="ml">Revenue</span><span class="mv">$50–150/mes</span></div>
      <div class="meta-item"><span class="ml">Complejidad</span><span class="mv">Alta (APIs)</span></div>
      <div class="meta-item"><span class="ml">Competencia</span><span class="mv">Ninguna para trading</span></div>
    </div>
    <div class="opp-body">
      <p><strong>El problema:</strong> El trader activo tiene cuentas en 3–5 plataformas. Nadie le muestra su P&amp;L real consolidado, exposición neta, correlación entre posiciones o riesgo total en tiempo real cruzando todos sus brokers. Bloomberg hace esto por $24,000/año. No existe versión retail.</p>
      <p><strong>El producto:</strong> Dashboard conectado vía API a todos los brokers/exchanges. P&amp;L cross-account, exposición neta, Greeks de portfolio, correlación entre posiciones, y tax position. Alertas cuando la exposición total supera límites definidos por el usuario.</p>
    </div>
    <div class="opp-score">
      <span class="score-label">Score</span>
      <div class="score-bar-wrap"><div class="score-bar" style="width:83%"></div></div>
      <span class="score-num">8.3/10</span>
    </div>
  </div>

  <!-- OPP 6 -->
  <div class="opp-card">
    <div class="opp-header">
      <div class="opp-rank-row">
        <div class="opp-rank">6</div>
        <div class="opp-title">0DTE Master — Plataforma Nativa para Opciones del Día</div>
      </div>
      <div class="opp-tagline">La primera plataforma diseñada para los contratos que mueven el 60% del mercado</div>
    </div>
    <div class="opp-meta-stack">
      <div class="meta-item"><span class="ml">TAM</span><span class="mv">$3T notional diario</span></div>
      <div class="meta-item"><span class="ml">Revenue</span><span class="mv">$79–199/mes</span></div>
      <div class="meta-item"><span class="ml">Complejidad</span><span class="mv">Alta</span></div>
      <div class="meta-item"><span class="ml">Competencia</span><span class="mv">Ninguna purpose-built</span></div>
    </div>
    <div class="opp-body">
      <p><strong>El problema:</strong> Las opciones 0DTE son el 60%+ del volumen de opciones en EE.UU. — la categoría de más rápido crecimiento en derivados. Requieren herramientas específicas que ninguna plataforma tiene de forma nativa: gamma visualization en tiempo real, dealer positioning, IV crush tracking intraday, y simulación de P&amp;L al vencimiento.</p>
      <p><strong>El producto:</strong> Dashboard 0DTE con mapa de calor de gamma por strike en tiempo real, dealer positioning, intraday IV decay tracker, P&amp;L simulator al vencimiento, y ejecución integrada.</p>
    </div>
    <div class="opp-score">
      <span class="score-label">Score</span>
      <div class="score-bar-wrap"><div class="score-bar" style="width:82%"></div></div>
      <span class="score-num">8.2/10</span>
    </div>
  </div>

  <!-- OPP 7 -->
  <div class="opp-card">
    <div class="opp-header">
      <div class="opp-rank-row">
        <div class="opp-rank">7</div>
        <div class="opp-title">PredictionEdge — Analytics para Prediction Markets</div>
      </div>
      <div class="opp-tagline">El Unusual Whales de Kalshi y Polymarket — categoría completamente vacía</div>
    </div>
    <div class="opp-meta-stack">
      <div class="meta-item"><span class="ml">TAM</span><span class="mv">$44B en volumen</span></div>
      <div class="meta-item"><span class="ml">Revenue</span><span class="mv">$49–149/mes</span></div>
      <div class="meta-item"><span class="ml">Complejidad</span><span class="mv">Baja-Media</span></div>
      <div class="meta-item"><span class="ml">Competencia</span><span class="mv">Inexistente</span></div>
    </div>
    <div class="opp-body">
      <p><strong>El problema:</strong> Kalshi y Polymarket tienen $44B en volumen anual (+1,000% YoY). Kalshi levantó $1B a $11B en Q1 2026. Polymarket recibió inversión de ICE (NYSE). Este mercado explotó y <strong>no existe ninguna herramienta analítica</strong> para él — ni tracker de precisión histórica, ni detector de smart money, ni backtesting de señales.</p>
      <p><strong>El producto:</strong> Analytics para prediction markets: historial de precisión por tipo de contrato, detección de smart money, backtesting de estrategias, y alertas de oportunidades de valor.</p>
      <div class="sub-section no-break">
        <h4>La Mayor Ventaja Competitiva Posible</h4>
        <ul>
          <li>Categoría completamente nueva — ser el primero es todo</li>
          <li>Datos son en su mayoría públicos — baja barrera de entrada</li>
          <li>Kalshi + Polymarket tienen APIs abiertas</li>
          <li>Ventana de first-mover: 12–18 meses máximo</li>
          <li>Super Bowl 60 generó $1.63B solo en Polymarket</li>
        </ul>
      </div>
    </div>
    <div class="opp-score">
      <span class="score-label">Score</span>
      <div class="score-bar-wrap"><div class="score-bar" style="width:80%"></div></div>
      <span class="score-num">8.0/10</span>
    </div>
  </div>

  <!-- OPP 8 -->
  <div class="opp-card">
    <div class="opp-header">
      <div class="opp-rank-row">
        <div class="opp-rank">8</div>
        <div class="opp-title">TradingDuolingo — Educación Gamificada Adaptativa</div>
      </div>
      <div class="opp-tagline">Duolingo para trading: curriculum adaptativo, streaks de disciplina, instructores verificados</div>
    </div>
    <div class="opp-meta-stack">
      <div class="meta-item"><span class="ml">TAM</span><span class="mv">$1.35B → $3.72B</span></div>
      <div class="meta-item"><span class="ml">Revenue</span><span class="mv">Freemium + $19–49/mes</span></div>
      <div class="meta-item"><span class="ml">Complejidad</span><span class="mv">Media</span></div>
      <div class="meta-item"><span class="ml">Competencia</span><span class="mv">Débil (sin gamificación adaptativa)</span></div>
    </div>
    <div class="opp-body">
      <p><strong>El problema:</strong> La FTC encontró que Online Trading Academy vendía cursos de $50,000 con base nula para sus afirmaciones. YouTube está dominado por gurus sin track records verificables. Ninguna plataforma tiene curriculum adaptativo, gamificación de proceso (no P&amp;L), ni instructores con track records auditados en tiempo real.</p>
      <p><strong>El producto:</strong> Plataforma tipo Duolingo que adapta el curriculum según errores demostrados del trader, gamifica la adherencia al plan, integra simulación con stakes emocionales, y publica el track record auditable de cada instructor en tiempo real.</p>
    </div>
    <div class="opp-score">
      <span class="score-label">Score</span>
      <div class="score-bar-wrap"><div class="score-bar" style="width:75%"></div></div>
      <span class="score-num">7.5/10</span>
    </div>
  </div>

  <!-- OPP 9 -->
  <div class="opp-card">
    <div class="opp-header">
      <div class="opp-rank-row">
        <div class="opp-rank">9</div>
        <div class="opp-title">CryptoDeriv Risk Hub</div>
      </div>
      <div class="opp-tagline">Dashboard unificado para crypto derivatives: liquidaciones, funding rates, basis y protección DeFi</div>
    </div>
    <div class="opp-meta-stack">
      <div class="meta-item"><span class="ml">TAM</span><span class="mv">$85.7T en volumen</span></div>
      <div class="meta-item"><span class="ml">Revenue</span><span class="mv">Freemium + $49–99/mes</span></div>
      <div class="meta-item"><span class="ml">Complejidad</span><span class="mv">Media</span></div>
      <div class="meta-item"><span class="ml">Competencia</span><span class="mv">Fragmentada</span></div>
    </div>
    <div class="opp-body">
      <p><strong>El problema:</strong> $85.7T en volumen de crypto derivatives en 2025. $150B en liquidaciones forzadas. En mayo 2025, bots de IA vendieron $2B en activos en 3 minutos durante un flash crash. Los datos necesarios están fragmentados: Coinglass tiene liquidaciones, Velo tiene funding rates, DexScreener tiene DEX — nadie tiene todo junto con guardianes de riesgo automáticos.</p>
    </div>
    <div class="opp-score">
      <span class="score-label">Score</span>
      <div class="score-bar-wrap"><div class="score-bar" style="width:72%"></div></div>
      <span class="score-num">7.2/10</span>
    </div>
  </div>

  <!-- OPP 10 -->
  <div class="opp-card">
    <div class="opp-header">
      <div class="opp-rank-row">
        <div class="opp-rank">10</div>
        <div class="opp-title">PropTrust — La Prop Firm Transparente</div>
      </div>
      <div class="opp-tagline">Payouts auditados, cuentas reales verificadas, reglas que no cambian retroactivamente</div>
    </div>
    <div class="opp-meta-stack">
      <div class="meta-item"><span class="ml">TAM</span><span class="mv">$7.8B mercado prop firms</span></div>
      <div class="meta-item"><span class="ml">Revenue</span><span class="mv">Challenge fees + profit split</span></div>
      <div class="meta-item"><span class="ml">Complejidad</span><span class="mv">Alta (regulatoria)</span></div>
      <div class="meta-item"><span class="ml">Competencia</span><span class="mv">Alta en cantidad, baja en calidad</span></div>
    </div>
    <div class="opp-body">
      <p><strong>El problema:</strong> 80–100 prop firms colapsaron en 2024–2025. El 93% de traders nunca recibe un pago. La mayoría de "funded accounts" son demos. FundingTicks cerró en enero 2026 cambiando retroactivamente las reglas a cuentas activas. Existe un vacío de confianza masivo en el mercado.</p>
      <p><strong>El producto:</strong> La primera prop firm con cuentas reales verificadas, payouts auditados y on-chain verificables, reglas transparentes e inmutables, y track record público de todos los traders financiados.</p>
    </div>
    <div class="opp-score">
      <span class="score-label">Score</span>
      <div class="score-bar-wrap"><div class="score-bar" style="width:68%"></div></div>
      <span class="score-num">6.8/10</span>
    </div>
  </div>
</div>


<!-- ==================== RECOMENDACIONES ==================== -->
<div class="section-page page-break">
  <div class="section-header">
    <div class="eyebrow">Sección 10</div>
    <div class="section-title">Recomendaciones y Conclusión</div>
  </div>

  <h2>Nuestras 3 Recomendaciones Top</h2>

  <div class="highlight-box no-break">
    <h3>🥇 #1 — AI Coach Conductual (Score 9.5)</h3>
    <p>El gap más documentado, el mercado más grande, la competencia más débil. Todos los datos apuntan a que nadie ha conectado el diagnóstico conductual con la intervención en tiempo real y el curriculum adaptativo. Es el producto que más directamente ataca la causa raíz del fracaso del trader retail. Sin necesidad de datos de mercado en tiempo real — trabaja sobre historial del trader. Monetización desde el día 1.</p>
  </div>

  <div class="callout green no-break" style="margin-top:16px;">
    <p><strong>🥈 #2 — PredictionEdge (Score 8.0)</strong><br/>
    La ventana de first-mover es de 12–18 meses máximo. Kalshi y Polymarket tienen APIs abiertas, los datos son mayormente públicos, y el mercado pasó de $0 a $44B en 3 años. Construir el "Unusual Whales de prediction markets" ahora — mientras nadie lo ha hecho — es la oportunidad de menor complejidad técnica con el mayor potencial de ser la referencia de la categoría.</p>
  </div>

  <div class="callout amber no-break" style="margin-top:16px;">
    <p><strong>🥉 #3 — Signal Intelligence Hub (Score 9.0)</strong><br/>
    La demanda está validada (Unusual Whales tiene comunidad y funding). El producto existe en partes — la oportunidad es unirlo. El modelo de negocio es claro, la disposición a pagar está probada ($100–300/mes por herramienta individual), y el valor del bundling es inmediato y tangible.</p>
  </div>

  <div class="divider"></div>

  <h2>El Patrón Común</h2>
  <p>Todas las oportunidades top comparten una sola característica: <strong>democratizan herramientas institucionales a precio retail.</strong> No inventan nada nuevo — toman lo que los hedge funds ya tienen y lo hacen accesible a decenas de millones de personas que pagan $50–150/mes y lo necesitan urgentemente.</p>

  <div class="divider"></div>

  <h2>Conclusión</h2>
  <p>El trading retail es uno de los mercados más grandes, más activos y más desatendidos del mundo. El 80–90% de sus participantes pierde dinero de forma documentada durante 27 años de estudios. Las soluciones existen — en el mundo institucional, a precios prohibitivos. La infraestructura técnica (Alpaca API, MCP servers, datos cada vez más baratos) nunca ha estado más madura para construir.</p>

  <div class="highlight-box no-break" style="margin-top: 24px;">
    <h3>En Una Sola Frase</h3>
    <p style="font-size: 11pt; font-style: italic; color: #e2e8f0;">"El mayor mercado sin explotar en software de trading no es una nueva categoría de activos — es simplemente darle al trader retail las mismas herramientas que ya tienen los profesionales, al 1% del precio."</p>
  </div>

  <p style="font-size: 8pt; color: #94a3b8; text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0;">Investigación realizada en mayo 2026 · 150+ fuentes · Documento confidencial para uso estratégico interno</p>
</div>

</body>
</html>"""

from weasyprint import HTML
import warnings
warnings.filterwarnings('ignore')

print("Generando PDF mobile...")
output_path = '/home/user/TRADINGBOT2.0/Trading_Research_Mobile_iPhone.pdf'
HTML(string=html_content).write_pdf(output_path, presentational_hints=True)
import os
size = os.path.getsize(output_path)
print(f"PDF generado: {output_path} ({size/1024:.0f} KB)")
