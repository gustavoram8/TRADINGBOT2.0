"use client";

import React, { useState } from "react";
import { useTradingStore } from "@/store";
import { cn } from "@/lib/utils";
import { PRESET_CONFIGS, DEFAULT_CONFIG } from "@/lib/mock-data";
import type { BotConfig } from "@/lib/types";
import { Save, Download, Upload, AlertTriangle, Info, ShieldCheck, ShieldAlert } from "lucide-react";

// ── Slider with optional hint ────────────────────────────────────────────
function Slider({ label, hint, value, min, max, step = 1, unit = "", onChange }: {
  label: string; hint?: string; value: number; min: number; max: number;
  step?: number; unit?: string; onChange: (v: number) => void;
}) {
  const display = unit === "$" ? `$${value.toLocaleString()}` : unit === "%" ? `${(value * 100).toFixed(0)}%` : `${value}${unit}`;
  const minDisplay = unit === "$" ? `$${min.toLocaleString()}` : unit === "%" ? `${(min * 100).toFixed(0)}%` : `${min}${unit}`;
  const maxDisplay = unit === "$" ? `$${max.toLocaleString()}` : unit === "%" ? `${(max * 100).toFixed(0)}%` : `${max}${unit}`;

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-text-secondary">{label}</span>
        <span className="font-mono font-semibold text-text-primary">{display}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 bg-bg-tertiary rounded-full appearance-none cursor-pointer accent-brand-blue"
      />
      <div className="flex justify-between text-[10px] text-text-muted">
        <span>{minDisplay}</span>
        <span>{maxDisplay}</span>
      </div>
      {hint && (
        <p className="text-[10px] text-text-muted leading-relaxed border-l-2 border-border pl-2">{hint}</p>
      )}
    </div>
  );
}

// ── Section header inside a tab ──────────────────────────────────────────
function SectionTitle({ title, description }: { title: string; description: string }) {
  return (
    <div className="col-span-full pb-1 border-b border-border">
      <p className="text-xs font-semibold text-text-primary">{title}</p>
      <p className="text-[10px] text-text-muted mt-0.5">{description}</p>
    </div>
  );
}

// ── Info box ─────────────────────────────────────────────────────────────
function InfoBox({ children }: React.PropsWithChildren<object>) {
  return (
    <div className="col-span-full flex gap-2 bg-brand-blue/10 border border-brand-blue/30 rounded-md p-3 text-[11px] text-text-secondary leading-relaxed">
      <Info size={13} className="text-brand-blue shrink-0 mt-0.5" />
      <span>{children}</span>
    </div>
  );
}

export default function ConfiguratorPage() {
  const { activeConfig, setActiveConfig } = useTradingStore();
  const [config, setConfig] = useState<BotConfig>({ ...activeConfig });
  const [activeTab, setActiveTab] = useState<"risk" | "fvg" | "structure" | "exits" | "sessions" | "json">("risk");
  const [saveMsg, setSaveMsg] = useState("");

  function update<K extends keyof BotConfig>(key: K, value: BotConfig[K]) {
    setConfig((c) => ({ ...c, [key]: value }));
  }
  function applyPreset(name: string) { setConfig({ ...PRESET_CONFIGS[name] }); }
  function handleSave() {
    setActiveConfig(config);
    setSaveMsg("Configuración aplicada ✓");
    setTimeout(() => setSaveMsg(""), 2000);
  }
  function handleExport() {
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `config_${config.name}.json`; a.click();
  }
  function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    file.text().then((t) => { try { setConfig(JSON.parse(t)); } catch { alert("JSON inválido"); } });
  }

  // Derived risk values
  const propFirmLimit = config.initial_capital * 0.05;
  const dailyLossPct = (config.max_daily_loss / propFirmLimit) * 100;
  const propFirmSafe = config.max_daily_loss <= propFirmLimit * 0.5;

  const tabs = [
    ["risk", "Riesgo"],
    ["fvg", "FVG"],
    ["structure", "Estructura"],
    ["exits", "Salidas"],
    ["sessions", "Sesiones"],
    ["json", "JSON"],
  ] as const;

  const killzones = [
    { name: "Asia",     start: "20:00", end: "00:00", entry: false, close: false,
      desc: "Sesión de baja liquidez. El bot no entra ni sale en esta ventana." },
    { name: "London",   start: "02:00", end: "05:00", entry: false, close: false,
      desc: "Apertura de Londres. Alta volatilidad pero fuera del horario configurado." },
    { name: "NY AM",    start: "09:30", end: "11:00", entry: true,  close: false,
      desc: "Apertura de Nueva York. Mayor liquidez del día. Única ventana donde el bot busca entradas." },
    { name: "NY Lunch", start: "12:00", end: "13:00", entry: false, close: true,
      desc: "Lunch de NY. Liquidez cae. El bot cierra posiciones abiertas para no quedar expuesto." },
    { name: "NY PM",    start: "13:30", end: "16:00", entry: false, close: false,
      desc: "Tarde de NY. El bot puede tener posiciones abiertas pero no abre nuevas." },
  ];

  // Break-even / close visual positions (as %)
  const bePct = Math.round(config.break_even_pct * 100);
  const closePct = Math.round(config.close_at_pct * 100);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Bot Builder</h1>
          <p className="text-sm text-text-secondary mt-0.5">Configura cada parámetro de la estrategia ICT y aplica el cambio al backtest</p>
        </div>
        <div className="flex items-center gap-2">
          {saveMsg && <span className="text-xs text-fin-green">{saveMsg}</span>}
          <button onClick={handleSave} className="btn-primary flex items-center gap-1.5">
            <Save size={14} /> Aplicar Config
          </button>
        </div>
      </div>

      {/* Presets */}
      <div className="card">
        <p className="text-sm font-medium mb-1">Presets rápidos</p>
        <p className="text-[11px] text-text-muted mb-3">Puntos de partida predefinidos. Puedes ajustar cualquier parámetro tras seleccionar uno.</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(PRESET_CONFIGS).map(([name, preset]) => (
            <button key={name} onClick={() => applyPreset(name)}
              className={cn("btn-secondary flex flex-col items-start gap-0.5 px-3 py-2 h-auto", config.name === name && "border-brand-blue text-brand-blue")}>
              <span className="text-xs font-medium">{name}</span>
              <span className="text-[10px] text-text-muted font-normal">
                {preset.default_contracts}c · ${preset.max_daily_loss} DD · {preset.max_trades_per_day} trades/día
              </span>
            </button>
          ))}
          <div className="ml-auto flex gap-2">
            <button onClick={handleExport} className="btn-secondary flex items-center gap-1.5">
              <Download size={13} /> Exportar
            </button>
            <label className="btn-secondary flex items-center gap-1.5 cursor-pointer">
              <Upload size={13} /> Importar
              <input type="file" accept=".json" onChange={handleImport} className="hidden" />
            </label>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div>
        <div className="border-b border-border flex gap-1 mb-4">
          {tabs.map(([t, l]) => (
            <button key={t} onClick={() => setActiveTab(t)}
              className={cn("px-4 py-2 text-sm", activeTab === t ? "tab-active" : "tab-inactive")}>
              {l}
            </button>
          ))}
        </div>

        {/* ── RIESGO ────────────────────────────────────────────────────── */}
        {activeTab === "risk" && (
          <div className="space-y-4">
            {/* Prop-firm compliance card */}
            <div className={cn("card flex items-start gap-3", propFirmSafe ? "border-fin-green/30" : "border-fin-gold/40")}>
              {propFirmSafe
                ? <ShieldCheck size={18} className="text-fin-green shrink-0 mt-0.5" />
                : <ShieldAlert size={18} className="text-fin-gold shrink-0 mt-0.5" />}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold">Cumplimiento Prop Firm</p>
                <p className="text-[11px] text-text-secondary mt-0.5">
                  Límite máximo de pérdida (5% de ${config.initial_capital.toLocaleString()}):
                  <span className="font-mono text-text-primary font-semibold"> ${propFirmLimit.toLocaleString()}</span>
                </p>
                {/* DD bar */}
                <div className="mt-2">
                  <div className="flex h-2 bg-bg-tertiary rounded-full overflow-hidden">
                    <div
                      className={cn("rounded-full transition-all", dailyLossPct > 70 ? "bg-fin-gold" : "bg-fin-green")}
                      style={{ width: `${Math.min(dailyLossPct, 100)}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-text-muted mt-1">
                    Tu pérdida máxima diaria (${config.max_daily_loss}) consume el{" "}
                    <span className={cn("font-semibold", dailyLossPct > 70 ? "text-fin-gold" : "text-fin-green")}>
                      {dailyLossPct.toFixed(0)}%
                    </span>{" "}
                    del límite total — {propFirmSafe ? "margen seguro" : "considera reducirla"}.
                  </p>
                </div>
              </div>
            </div>

            <div className="card grid grid-cols-1 md:grid-cols-2 gap-6">
              <SectionTitle
                title="Capital y tamaño de posición"
                description="Definen cuánto dinero maneja el bot y con qué tamaño opera."
              />
              <Slider
                label="Capital inicial" value={config.initial_capital} min={10000} max={200000} step={5000} unit="$"
                hint="Punto de partida de la cuenta. Todas las métricas de riesgo (drawdown, daily loss) se calculan sobre este valor."
                onChange={(v) => update("initial_capital", v)}
              />
              <Slider
                label="Contratos por defecto" value={config.default_contracts} min={1} max={20}
                hint="Número de contratos MNQ que usa el bot en condiciones normales. Cada contrato MNQ vale $2 por punto. Con 10 contratos y 30 puntos de movimiento = $600 brutos. Se reduce automáticamente si el drawdown se acerca al límite del 5%."
                onChange={(v) => update("default_contracts", v)}
              />
              <Slider
                label="Pérdida máxima por operación" value={config.max_loss_per_trade} min={100} max={2000} step={50} unit="$"
                hint="Si el Stop Loss lógico del trade (basado en el FVG protector y la liquidez) implica perder más de este monto con 1 solo contrato, el bot descarta el trade. El SL siempre se coloca por lógica ICT — este valor decide si la operación es compatible con tu gestión de riesgo."
                onChange={(v) => update("max_loss_per_trade", v)}
              />

              <SectionTitle
                title="Kill-switches diarios"
                description="Reglas que detienen el bot cuando el riesgo del día supera los umbrales definidos."
              />
              <Slider
                label="Pérdida máxima diaria" value={config.max_daily_loss} min={200} max={1500} step={50} unit="$"
                hint="Si el bot pierde esta cantidad en el día, deja de operar hasta el día siguiente. Evita días catastrófico. Mantenerla por debajo del 50% del límite total es lo recomendado."
                onChange={(v) => update("max_daily_loss", v)}
              />
              <Slider
                label="Máx. trades por día" value={config.max_trades_per_day} min={1} max={5}
                hint="Una vez que el bot llega a este número de operaciones en el día, deja de buscar nuevas entradas. Limita la sobreoperación."
                onChange={(v) => update("max_trades_per_day", v)}
              />

              <SectionTitle
                title="Umbrales de alerta"
                description="El bot detecta cuándo un trade individual es excepcionalmente grande (bueno o malo) para ajustar su comportamiento."
              />
              <Slider
                label="Umbral de pérdida grande" value={config.big_loss_threshold} min={200} max={1000} step={50} unit="$"
                hint='Si una sola operación pierde más de este valor, se considera una "pérdida grande". El bot puede volverse más conservador el resto del día y es registrada como evento de riesgo.'
                onChange={(v) => update("big_loss_threshold", v)}
              />
              <Slider
                label="Umbral de ganancia grande" value={config.big_win_threshold} min={400} max={2000} step={100} unit="$"
                hint='Si una sola operación gana más de este valor, se considera una "ganancia grande". El bot puede proteger la ganancia operando con más cautela el resto del día.'
                onChange={(v) => update("big_win_threshold", v)}
              />
            </div>
          </div>
        )}

        {/* ── FVG ───────────────────────────────────────────────────────── */}
        {activeTab === "fvg" && (
          <div className="space-y-4">
            <div className="card">
              <InfoBox>
                Un <strong>Fair Value Gap (FVG)</strong> es una vela con movimiento tan fuerte que deja un hueco entre la mecha de la vela anterior y la mecha de la siguiente. El mercado tiende a volver a esas zonas para "llenarlas". El bot las detecta por timeframe y las usa como zonas de entrada.
                <br /><br />
                <strong>Lookback</strong>: cuántas velas hacia atrás escanea para encontrar FVGs válidos.
                <strong> Max activos</strong>: cuántos FVGs puede tener en memoria a la vez. Si llega al límite, descarta el más antiguo.
                <strong> Search range</strong>: radio en puntos alrededor del precio actual donde el bot busca FVGs. Si hay un FVG pero el precio está lejos, lo ignora.
              </InfoBox>
            </div>

            {(["1h", "15m", "5m", "1m"] as const).map((tf) => (
              <div key={tf} className="card grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="col-span-full pb-1 border-b border-border flex items-center gap-2">
                  <span className="text-xs font-bold text-brand-blue font-mono uppercase">{tf}</span>
                  <span className="text-[10px] text-text-muted">
                    {tf === "1h" && "Macro — define el sesgo y las zonas grandes"}
                    {tf === "15m" && "Intermedio — afina la zona de entrada"}
                    {tf === "5m" && "Ejecución — confirma el setup antes de entrar"}
                    {tf === "1m" && "Micro — entrada precisa de bajo riesgo"}
                  </span>
                </div>
                <Slider
                  label={`Lookback (velas ${tf})`}
                  value={config[`fvg_lookback_${tf}` as keyof BotConfig] as number}
                  min={5} max={50}
                  hint={`Escanea las últimas N velas de ${tf} buscando FVGs. Más velas = más oportunidades detectadas, pero también más ruido y señales obsoletas.`}
                  onChange={(v) => update(`fvg_lookback_${tf}` as keyof BotConfig, v)}
                />
                <Slider
                  label={`Max FVGs activos (${tf})`}
                  value={config[`fvg_max_${tf}` as keyof BotConfig] as number}
                  min={1} max={10}
                  hint={`Si ya hay ${config[`fvg_max_${tf}` as keyof BotConfig]} FVGs activos en ${tf} y se detecta uno nuevo, el más antiguo se elimina. Evita acumular demasiadas zonas en el mapa.`}
                  onChange={(v) => update(`fvg_max_${tf}` as keyof BotConfig, v)}
                />
              </div>
            ))}

            <div className="card">
              <Slider
                label="Search range (puntos)"
                value={config.fvg_search_range} min={100} max={800} step={50}
                hint="Si el precio actual está a más de N puntos de un FVG, el bot lo ignora al evaluar la entrada. Evita que el bot entre en FVGs que ya quedaron muy lejos del precio."
                onChange={(v) => update("fvg_search_range", v)}
              />
            </div>
          </div>
        )}

        {/* ── ESTRUCTURA ────────────────────────────────────────────────── */}
        {activeTab === "structure" && (
          <div className="space-y-4">
            <div className="card">
              <InfoBox>
                La <strong>estructura de mercado</strong> determina si el bot busca trades <em>largos</em> (alcistas) o <em>cortos</em> (bajistas). El bot analiza las velas de 4H mirando atrás N velas y detecta si el precio está haciendo máximos y mínimos crecientes (tendencia alcista) o decrecientes (bajista). Solo toma trades en la dirección de esa tendencia.
              </InfoBox>
            </div>
            <div className="card">
              <Slider
                label="Lookback de estructura (velas 4H)"
                value={config.structure_lookback} min={3} max={12}
                hint="Cuántas velas de 4H analiza el bot para determinar la tendencia. Con 3–4 velas reacciona rápido a cambios de tendencia. Con 10–12 velas es más estable pero tarda más en cambiar de sesgo."
                onChange={(v) => update("structure_lookback", v)}
              />

              {/* Visual of lookback */}
              <div className="mt-4 pt-4 border-t border-border">
                <p className="text-[10px] text-text-muted mb-2">
                  Con <span className="text-text-primary font-mono font-semibold">{config.structure_lookback}</span> velas de 4H = mirando ~{(config.structure_lookback * 4)} horas hacia atrás
                </p>
                <div className="flex items-end gap-1 h-10">
                  {Array.from({ length: config.structure_lookback }).map((_, i) => (
                    <div
                      key={i}
                      className="flex-1 rounded-sm bg-brand-blue/40 border border-brand-blue/60"
                      style={{ height: `${30 + Math.sin(i * 0.8) * 12}px` }}
                    />
                  ))}
                  <div className="flex-1 rounded-sm bg-brand-blue border border-brand-blue" style={{ height: "42px" }} title="Vela actual" />
                </div>
                <p className="text-[10px] text-text-muted mt-1">← {config.structure_lookback} velas analizadas · vela actual →</p>
              </div>
            </div>
          </div>
        )}

        {/* ── SALIDAS ───────────────────────────────────────────────────── */}
        {activeTab === "exits" && (
          <div className="space-y-4">
            <div className="card">
              <InfoBox>
                El bot gestiona cada trade con dos mecanismos automáticos de salida parcial para proteger ganancias. Ambos se activan en función del recorrido hacia el <strong>Take Profit (TP)</strong>.
              </InfoBox>
            </div>

            <div className="card space-y-6">
              <Slider
                label="Break-even — activar al llegar al"
                value={config.break_even_pct} min={0.2} max={0.8} step={0.05} unit="%"
                hint={`Cuando el precio recorre el ${bePct}% del camino hacia el TP, el Stop Loss se mueve al precio de entrada (break-even). Si el mercado gira, el trade cierra en 0 en vez de pérdida. Ejemplo: TP a 100 puntos → break-even activa a los +${bePct} puntos.`}
                onChange={(v) => update("break_even_pct", v)}
              />
              <Slider
                label="Cierre anticipado — al llegar al"
                value={config.close_at_pct} min={0.7} max={1.0} step={0.05} unit="%"
                hint={`El bot cierra la posición completa cuando el precio llega al ${closePct}% del TP, en vez de esperar al 100%. Reduce la ganancia máxima pero aumenta el porcentaje de trades ganadores. Ejemplo: TP a 100 puntos → cierra en +${closePct} puntos.`}
                onChange={(v) => update("close_at_pct", v)}
              />

              {/* Trade journey visual */}
              <div className="pt-2 border-t border-border">
                <p className="text-[10px] text-text-muted mb-3 font-semibold uppercase tracking-wider">Diagrama de un trade típico</p>
                <div className="relative">
                  {/* Track */}
                  <div className="h-3 bg-bg-tertiary rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-fin-red/30 via-fin-green/40 to-fin-green rounded-full"
                      style={{ width: "100%" }} />
                  </div>
                  {/* Markers */}
                  {[
                    { pct: 0, label: "Entrada", color: "text-text-muted", dot: "bg-text-muted" },
                    { pct: bePct, label: `Break-even\n(${bePct}%)`, color: "text-fin-gold", dot: "bg-fin-gold" },
                    { pct: closePct, label: `Cierre\n(${closePct}%)`, color: "text-brand-blue", dot: "bg-brand-blue" },
                    { pct: 100, label: "TP\n(100%)", color: "text-fin-green", dot: "bg-fin-green" },
                  ].map(({ pct, label, color, dot }) => (
                    <div key={pct} className="absolute top-0 flex flex-col items-center" style={{ left: `${pct}%`, transform: "translateX(-50%)" }}>
                      <div className={cn("w-2 h-2 rounded-full -mt-0.5 border-2 border-bg-primary", dot)} />
                      <div className={cn("text-[9px] mt-1 text-center whitespace-pre leading-tight", color)}>{label}</div>
                    </div>
                  ))}
                </div>
                <div className="flex justify-between text-[9px] text-text-muted mt-8">
                  <span>SL (pérdida)</span>
                  <span>TP máximo</span>
                </div>
              </div>

              {/* Warning */}
              {config.break_even_pct >= config.close_at_pct && (
                <div className="flex items-center gap-2 bg-fin-gold/10 border border-fin-gold/40 rounded-md p-3 text-xs text-fin-gold">
                  <AlertTriangle size={13} />
                  Break-even ({bePct}%) ≥ Cierre anticipado ({closePct}%) — el SL llegaría a break-even después del cierre. Aumenta el cierre anticipado o baja el break-even.
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── SESIONES ─────────────────────────────────────────────────── */}
        {activeTab === "sessions" && (
          <div className="space-y-4">
            <div className="card">
              <InfoBox>
                El mercado de <strong>MNQ (Micro Nasdaq)</strong> opera 23h al día, pero no todas las horas tienen la misma liquidez. El bot solo opera en horarios donde hay suficiente volumen para que las entradas y salidas sean eficientes. Todos los horarios están en <strong>ET (Eastern Time)</strong>.
              </InfoBox>
            </div>
            <div className="card space-y-3">
              {killzones.map((kz) => (
                <div key={kz.name} className={cn(
                  "rounded-md p-3 border",
                  kz.entry ? "border-fin-green/40 bg-fin-green/5" : "border-border bg-bg-tertiary"
                )}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="text-center shrink-0 w-16">
                        <p className="text-xs font-semibold text-text-primary">{kz.name}</p>
                        <p className="text-[10px] font-mono text-text-muted">{kz.start}–{kz.end}</p>
                      </div>
                      <p className="text-[11px] text-text-secondary">{kz.desc}</p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      {kz.entry
                        ? <span className="badge-green text-[10px]">Entradas ✓</span>
                        : <span className="text-[10px] text-text-muted px-2 py-0.5 border border-border rounded">No entra</span>}
                      {kz.close
                        ? <span className="badge-red text-[10px]">Cierra ✓</span>
                        : null}
                    </div>
                  </div>
                </div>
              ))}
              <p className="text-[10px] text-text-muted pt-1">
                Las sesiones son fijas (regla de la estrategia ICT). Para cambiarlas habla con el desarrollador del bot.
              </p>
            </div>
          </div>
        )}

        {/* ── JSON ─────────────────────────────────────────────────────── */}
        {activeTab === "json" && (
          <div className="card">
            <p className="text-xs text-text-muted mb-3">Edición directa del JSON de configuración. Útil para copiar/pegar configuraciones. Cualquier cambio válido se refleja automáticamente en los sliders.</p>
            <textarea
              className="w-full h-96 bg-bg-tertiary border border-border rounded-md p-3 font-mono text-xs text-text-primary focus:outline-none focus:border-brand-blue resize-none"
              value={JSON.stringify(config, null, 2)}
              onChange={(e) => { try { setConfig(JSON.parse(e.target.value)); } catch { /* invalid JSON while typing */ } }}
            />
          </div>
        )}
      </div>

      {/* ── Resumen activo ───────────────────────────────────────────────── */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-medium">Resumen de la configuración activa</p>
          <span className="text-xs text-text-muted">
            Pendiente de aplicar{" "}
            {JSON.stringify(config) !== JSON.stringify(activeConfig) && (
              <span className="text-fin-gold">· cambios sin guardar</span>
            )}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Capital inicial", value: `$${config.initial_capital.toLocaleString()}`, sub: "base de la cuenta" },
            { label: "Contratos MNQ", value: String(config.default_contracts), sub: `$${config.default_contracts * 2}/punto · $${config.default_contracts * 50}/trade (25 pts riesgo)` },
            { label: "Máx. pérdida/trade", value: `$${config.max_loss_per_trade}`, sub: "trade descartado si SL supera esto" },
            { label: "DD máx diario", value: `$${config.max_daily_loss}`, sub: `${dailyLossPct.toFixed(0)}% del límite 5%` },
            { label: "Trades por día", value: `≤ ${config.max_trades_per_day}`, sub: "máximo permitido" },
            { label: "Break-even", value: `${bePct}% del TP`, sub: "SL → entrada al llegar aquí" },
            { label: "Cierre anticipado", value: `${closePct}% del TP`, sub: "posición cerrada aquí" },
            { label: "Límite prop firm", value: `$${propFirmLimit.toLocaleString()}`, sub: "5% del capital — hard stop" },
            { label: "Estructura 4H", value: `${config.structure_lookback} velas`, sub: `≈ ${config.structure_lookback * 4}h de contexto` },
          ].map(({ label, value, sub }) => (
            <div key={label} className="bg-bg-tertiary rounded-md p-3">
              <p className="text-[10px] text-text-muted">{label}</p>
              <p className="font-bold font-mono text-sm mt-0.5">{value}</p>
              <p className="text-[10px] text-text-muted mt-0.5">{sub}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
