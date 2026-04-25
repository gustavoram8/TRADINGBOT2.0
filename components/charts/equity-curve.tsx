"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { EquityPoint } from "@/lib/types";

interface Props {
  data: EquityPoint[];
  initialBalance?: number;
  height?: number;
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { value: number; name: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const equity = payload[0]?.value ?? 0;
  const dd = payload[1]?.value ?? 0;
  return (
    <div className="bg-bg-tertiary border border-border rounded-md p-3 text-xs">
      <p className="text-text-secondary mb-1">{label}</p>
      <p className="text-fin-green font-mono">Equity: ${equity.toLocaleString()}</p>
      {dd > 0 && (
        <p className="text-fin-red font-mono">DD: -${dd.toFixed(0)}</p>
      )}
    </div>
  );
}

export function EquityCurve({ data, initialBalance = 50000, height = 240 }: Props) {
  const formatted = data.map((p) => ({
    date: new Date(p.datetime).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    equity: Math.round(p.equity),
    drawdown: Math.round(p.drawdown),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={formatted} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#00C853" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#00C853" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1C2333" />
        <XAxis dataKey="date" tick={{ fill: "#8B949E", fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
        <YAxis tick={{ fill: "#8B949E", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={initialBalance} stroke="#30363D" strokeDasharray="4 4" />
        <Area
          type="monotone"
          dataKey="equity"
          stroke="#00C853"
          strokeWidth={2}
          fill="url(#equityGrad)"
          dot={false}
          activeDot={{ r: 4, fill: "#00C853" }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
