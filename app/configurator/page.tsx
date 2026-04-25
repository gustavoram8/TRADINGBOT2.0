"use client";

import { useState } from "react";
import { useTradingStore } from "@/store";
import { cn } from "@/lib/utils";
import { PRESET_CONFIGS, DEFAULT_CONFIG } from "@/lib/mock-data";
import type { BotConfig } from "@/lib/types";
import { Save, Download, Upload, AlertTriangle } from "lucide-react";

function Slider({ label, value, min, max, step = 1, unit = "", onChange }: {
  label: string; value: number; min: number; max: number; step?: number; unit?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-text-secondary">{label}</span>
        <span className="font-mono text-text-primary">{unit === "$" ? `$${value.toLocaleString()}` : `${value}${unit}`}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 bg-bg-tertiary rounded-full appearance-none cursor-pointer accent-brand-blue"
      />
      <div className="flex justify-between text-[10px] text-text-muted">
        <span>{unit === "$" ? `$${min}` : `${min}${unit}`}</span>
        <span>{unit === "$" ? `$${max}` : `${max}${unit}`}</span>
      </div>
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

  function applyPreset(name: string) {
    setConfig({ ...PRESET_CONFIGS[name] });
  }

  function handleSave() {
    setActiveConfig(config);
    setSaveMsg("Configuración aplicada ✓");
    setTimeout(() => setSaveMsg(""), 2000);
  }

  function handleExport() {
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `config_${config.name}.json`;
    a.click();
  }

  function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    file.text().then((t) => {
      try { setConfig(JSON.parse(t)); }
      catch { alert("JSON inválido"); }
    });
  }

  const tabs = [
    ["risk", "Riesgo"],
    ["fvg", "FVG"],
    ["structure", "Estructura"],
    ["exits", "Salidas"],
    ["sessions", "Sesiones"],
    ["json", "JSON"],
  ] as const;

  const killzones = [
    { name: "Asia", start: "20:00", end: "00:00", entry: false, close: false },
    { name: "London", start: "02:00", end: "05:00", entry: false, close: false },
    { name: "NY AM", start: "09:30", end: "11:00", entry: true, close: false },
    { name: "NY Lunch", start: "12:00", end: "13:00", entry: false, close: true },
    { name: "NY PM", start: "13:30", end: "16:00", entry: false, close: false },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Bot Builder</h1>
          <p className="text-sm text-text-secondary mt-0.5">Parámetros de la estrategia ICT</p>
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
        <p className="text-sm font-medium mb-3">Presets</p>
        <div className="flex flex-wrap gap-2">
          {Object.keys(PRESET_CONFIGS).map((name) => (
            <button key={name} onClick={() => applyPreset(name)} className={cn("btn-secondary", config.name === name && "border-brand-blue text-brand-blue")}>
              {name}
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
            <button key={t} onClick={() => setActiveTab(t)} className={cn("px-4 py-2 text-sm", activeTab === t ? "tab-active" : "tab-inactive")}>
              {l}
            </button>
          ))}
        </div>

        {activeTab === "risk" && (
          <div className="card grid grid-cols-1 md:grid-cols-2 gap-6">
            <Slider label="Capital inicial ($)" value={config.initial_capital} min={10000} max={200000} step={5000} unit="$" onChange={(v) => update("initial_capital", v)} />
            <Slider label="Pérdida máxima diaria ($)" value={config.max_daily_loss} min={200} max={1500} step={50} unit="$" onChange={(v) => update("max_daily_loss", v)} />
            <Slider label="Máx. trades por día" value={config.max_trades_per_day} min={1} max={5} onChange={(v) => update("max_trades_per_day", v)} />
            <Slider label="Contratos por defecto" value={config.default_contracts} min={1} max={6} onChange={(v) => update("default_contracts", v)} />
            <Slider label="Big Loss threshold ($)" value={config.big_loss_threshold} min={200} max={1000} step={50} unit="$" onChange={(v) => update("big_loss_threshold", v)} />
            <Slider label="Big Win threshold ($)" value={config.big_win_threshold} min={400} max={2000} step={100} unit="$" onChange={(v) => update("big_win_threshold", v)} />
          </div>
        )}

        {activeTab === "fvg" && (
          <div className="card grid grid-cols-1 md:grid-cols-2 gap-6">
            {(["1h", "15m", "5m", "1m"] as const).flatMap((tf) => [
              <Slider key={`lb_${tf}`} label={`Lookback ${tf} (barras)`} value={config[`fvg_lookback_${tf}` as keyof BotConfig] as number} min={5} max={50} onChange={(v) => update(`fvg_lookback_${tf}` as keyof BotConfig, v)} />,
              <Slider key={`max_${tf}`} label={`Max FVGs activos ${tf}`} value={config[`fvg_max_${tf}` as keyof BotConfig] as number} min={1} max={10} onChange={(v) => update(`fvg_max_${tf}` as keyof BotConfig, v)} />,
            ])}
            <Slider label="Search range (puntos)" value={config.fvg_search_range} min={100} max={800} step={50} onChange={(v) => update("fvg_search_range", v)} />
          </div>
        )}

        {activeTab === "structure" && (
          <div className="card">
            <Slider label="Structure lookback 4H (velas)" value={config.structure_lookback} min={3} max={12} onChange={(v) => update("structure_lookback", v)} />
          </div>
        )}

        {activeTab === "exits" && (
          <div className="card space-y-6">
            <Slider label="Break-even trigger (%)" value={config.break_even_pct} min={0.2} max={0.8} step={0.05} unit="%" onChange={(v) => update("break_even_pct", v)} />
            <Slider label="Cerrar al % del TP" value={config.close_at_pct} min={0.7} max={1.0} step={0.05} unit="%" onChange={(v) => update("close_at_pct", v)} />
            {config.break_even_pct >= config.close_at_pct && (
              <div className="flex items-center gap-2 text-fin-gold text-sm">
                <AlertTriangle size={14} />
                Break-even ({(config.break_even_pct * 100).toFixed(0)}%) ≥ close_at ({(config.close_at_pct * 100).toFixed(0)}%) — el break-even nunca disparará.
              </div>
            )}
          </div>
        )}

        {activeTab === "sessions" && (
          <div className="card overflow-x-auto">
            <p className="text-xs text-text-secondary mb-3">Horario del bot: 09:30–16:00 ET. Solo NY AM permite entradas.</p>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs">
                  {["Sesión", "Inicio ET", "Fin ET", "¿Entrar?", "¿Cerrar al entrar?"].map((h) => (
                    <th key={h} className="text-left py-2 pr-4 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {killzones.map((kz) => (
                  <tr key={kz.name} className="border-b border-border/40">
                    <td className="py-2 pr-4 font-medium">{kz.name}</td>
                    <td className="py-2 pr-4 font-mono">{kz.start}</td>
                    <td className="py-2 pr-4 font-mono">{kz.end}</td>
                    <td className="py-2 pr-4">
                      {kz.entry ? <span className="badge-green">SÍ</span> : <span className="text-text-muted text-xs">NO</span>}
                    </td>
                    <td className="py-2 pr-4">
                      {kz.close ? <span className="badge-red">SÍ</span> : <span className="text-text-muted text-xs">NO</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === "json" && (
          <div className="card">
            <textarea
              className="w-full h-96 bg-bg-tertiary border border-border rounded-md p-3 font-mono text-xs text-text-primary focus:outline-none focus:border-brand-blue resize-none"
              value={JSON.stringify(config, null, 2)}
              onChange={(e) => {
                try { setConfig(JSON.parse(e.target.value)); }
                catch { /* invalid JSON */ }
              }}
            />
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="card">
        <p className="text-sm font-medium mb-3">Resumen — {config.name}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          {[
            ["Capital", `$${config.initial_capital.toLocaleString()}`],
            ["Contratos", String(config.default_contracts)],
            ["Max DD Diario", `$${config.max_daily_loss}`],
            ["Max Trades/Día", String(config.max_trades_per_day)],
          ].map(([k, v]) => (
            <div key={k} className="bg-bg-tertiary rounded-md p-3">
              <p className="text-xs text-text-secondary">{k}</p>
              <p className="font-bold font-mono mt-0.5">{v}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
