"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { Trade } from "@/lib/types";

interface Props {
  trades: Trade[];
  height?: number;
}

export function PnlChart({ trades, height = 200 }: Props) {
  const data = trades.map((t, i) => ({
    name: `#${i + 1}`,
    pnl: Math.round(t.pnl_net),
    dir: t.direction,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1C2333" vertical={false} />
        <XAxis dataKey="name" tick={{ fill: "#8B949E", fontSize: 9 }} tickLine={false} axisLine={false} interval={4} />
        <YAxis tick={{ fill: "#8B949E", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
        <Tooltip
          formatter={(v: number) => [`$${v.toFixed(0)}`, "P&L"]}
          contentStyle={{ background: "#1C2333", border: "1px solid #30363D", borderRadius: 6, fontSize: 12 }}
          labelStyle={{ color: "#8B949E" }}
        />
        <ReferenceLine y={0} stroke="#30363D" />
        {data.map((entry, idx) => (
          <Cell key={idx} fill={entry.pnl >= 0 ? "#00C853" : "#EF5350"} />
        ))}
        <Bar dataKey="pnl" radius={[2, 2, 0, 0]}>
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.pnl >= 0 ? "#00C853" : "#EF5350"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
