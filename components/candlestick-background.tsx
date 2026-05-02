"use client";

import { useMemo } from "react";

interface Candle {
  x: number;
  bodyY: number;
  bodyH: number;
  wickHigh: number;
  wickLow: number;
  width: number;
  bright: boolean;
}

const CANVAS_W = 1600;
const CANVAS_H = 900;

function generateCandles(): Candle[] {
  // Deterministic pseudo-random — same shape on every render/SSR hydration.
  let s = 1337;
  const r = () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };

  const COUNT = 55;
  const candleW = 12;
  const spacing = CANVAS_W / COUNT;
  const candles: Candle[] = [];

  let price = CANVAS_H * 0.6;

  for (let i = 0; i < COUNT; i++) {
    const drift = (r() - 0.45) * 70; // slight upward bias for bullish look
    const open = price;
    const close = Math.max(140, Math.min(CANVAS_H - 140, open + drift));

    const top = Math.min(open, close);
    const bot = Math.max(open, close);
    const wickHigh = Math.max(40, top - r() * 35 - 5);
    const wickLow = Math.min(CANVAS_H - 40, bot + r() * 35 + 5);

    candles.push({
      x: i * spacing + spacing / 2,
      bodyY: top,
      bodyH: Math.max(6, bot - top),
      wickHigh,
      wickLow,
      width: candleW,
      bright: r() > 0.6,
    });

    price = close;
  }

  return candles;
}

export function CandlestickBackground() {
  const candles = useMemo(generateCandles, []);

  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden z-0"
      aria-hidden="true"
    >
      <svg
        className="w-full h-full opacity-[0.14]"
        viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          {/* Cylindrical 3D gradient — dark edge → bright core → dark edge */}
          <linearGradient id="cb-body" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#04240e" />
            <stop offset="22%" stopColor="#1a9d4d" />
            <stop offset="48%" stopColor="#42ff8a" />
            <stop offset="58%" stopColor="#42ff8a" />
            <stop offset="80%" stopColor="#178f44" />
            <stop offset="100%" stopColor="#02180a" />
          </linearGradient>

          <linearGradient id="cb-body-bright" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0a3a1d" />
            <stop offset="22%" stopColor="#22c562" />
            <stop offset="48%" stopColor="#67ffa0" />
            <stop offset="58%" stopColor="#67ffa0" />
            <stop offset="80%" stopColor="#1fb056" />
            <stop offset="100%" stopColor="#062814" />
          </linearGradient>

          {/* Soft drop shadow → depth */}
          <filter id="cb-shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="2.5" />
            <feOffset dx="2" dy="3" result="off" />
            <feComponentTransfer>
              <feFuncA type="linear" slope="0.55" />
            </feComponentTransfer>
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Vignette so candles fade gently into the bg toward the edges */}
          <radialGradient id="cb-vignette" cx="50%" cy="50%" r="80%">
            <stop offset="40%" stopColor="#0d1117" stopOpacity="0" />
            <stop offset="100%" stopColor="#0d1117" stopOpacity="0.85" />
          </radialGradient>
        </defs>

        <g filter="url(#cb-shadow)">
          {candles.map((c, i) => (
            <g key={i}>
              <line
                x1={c.x}
                y1={c.wickHigh}
                x2={c.x}
                y2={c.wickLow}
                stroke={c.bright ? "#67ffa0" : "#3fcd75"}
                strokeWidth="1.5"
                strokeLinecap="round"
              />
              <rect
                x={c.x - c.width / 2}
                y={c.bodyY}
                width={c.width}
                height={c.bodyH}
                fill={c.bright ? "url(#cb-body-bright)" : "url(#cb-body)"}
                rx="1.2"
              />
            </g>
          ))}
        </g>

        <rect width={CANVAS_W} height={CANVAS_H} fill="url(#cb-vignette)" />
      </svg>
    </div>
  );
}
