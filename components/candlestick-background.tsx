"use client";

import { useMemo } from "react";

/**
 * Decorative background ("Market Pulse"):
 *  – Soft pulsing color orbs (palette-matched: brand blue, fin green)
 *  – Subtle dot grid (trading-terminal feel)
 *  – Animated chart line with area fill that "breathes"
 *  – A handful of small accent candlesticks at the edges
 *
 * Pure decoration. Pointer-events disabled. Deterministic — no hydration drift.
 */

interface MiniCandle {
  x: number;
  y: number;
  h: number;
  bullish: boolean;
}

const W = 1600;
const H = 900;

function buildScene() {
  let s = 4242;
  const r = () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };

  const points: { x: number; y: number }[] = [];
  const N = 14;
  let y = H * 0.55;
  for (let i = 0; i <= N; i++) {
    const drift = (r() - 0.45) * 110;
    y = Math.max(H * 0.25, Math.min(H * 0.78, y + drift));
    points.push({ x: (W * i) / N, y });
  }

  let path = `M ${points[0].x},${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i];
    const p1 = points[i + 1];
    const cx = (p0.x + p1.x) / 2;
    path += ` C ${cx},${p0.y} ${cx},${p1.y} ${p1.x},${p1.y}`;
  }
  const areaPath = `${path} L ${W},${H} L 0,${H} Z`;

  const candles: MiniCandle[] = [];
  for (let i = 0; i < 18; i++) {
    const edgeBand = r() < 0.5 ? r() * 0.25 : 0.75 + r() * 0.25;
    candles.push({
      x: edgeBand * W,
      y: 80 + r() * (H - 200),
      h: 18 + r() * 42,
      bullish: r() > 0.4,
    });
  }

  return { path, areaPath, candles };
}

export function CandlestickBackground() {
  const scene = useMemo(buildScene, []);

  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden z-0"
      aria-hidden="true"
    >
      {/* Pulsing color orbs — palette: brand blue + fin green */}
      <div
        className="absolute -top-40 -left-40 w-[680px] h-[680px] rounded-full opacity-[0.22] blur-3xl animate-mp-pulse-slow"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, #1F6FEB 0%, #1F6FEB00 65%)",
        }}
      />
      <div
        className="absolute top-1/3 -right-32 w-[620px] h-[620px] rounded-full opacity-[0.20] blur-3xl animate-mp-pulse-slower"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, #00C853 0%, #00C85300 65%)",
        }}
      />
      <div
        className="absolute -bottom-48 left-1/3 w-[700px] h-[700px] rounded-full opacity-[0.18] blur-3xl animate-mp-pulse-slow"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, #58A6FF 0%, #58A6FF00 65%)",
        }}
      />

      {/* Dot grid overlay */}
      <svg
        className="absolute inset-0 w-full h-full opacity-[0.18]"
        aria-hidden="true"
      >
        <defs>
          <pattern
            id="mp-dots"
            x="0"
            y="0"
            width="34"
            height="34"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="1.2" cy="1.2" r="1.2" fill="#30363D" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#mp-dots)" />
      </svg>

      {/* Main "market pulse" SVG */}
      <svg
        className="absolute inset-0 w-full h-full"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <linearGradient id="mp-area" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#00C853" stopOpacity="0.32" />
            <stop offset="55%" stopColor="#00C853" stopOpacity="0.06" />
            <stop offset="100%" stopColor="#00C853" stopOpacity="0" />
          </linearGradient>

          <linearGradient id="mp-line" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00C853" />
            <stop offset="55%" stopColor="#42A5F5" />
            <stop offset="100%" stopColor="#58A6FF" />
          </linearGradient>

          <filter id="mp-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <radialGradient id="mp-vignette" cx="50%" cy="50%" r="78%">
            <stop offset="55%" stopColor="#0D1117" stopOpacity="0" />
            <stop offset="100%" stopColor="#0D1117" stopOpacity="0.7" />
          </radialGradient>
        </defs>

        <path
          d={scene.areaPath}
          fill="url(#mp-area)"
          className="animate-mp-breathe"
          style={{ transformOrigin: "50% 100%" }}
        />

        <path
          d={scene.path}
          fill="none"
          stroke="url(#mp-line)"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.55"
          filter="url(#mp-glow)"
        />

        {scene.candles.map((c, i) => (
          <g key={i} opacity="0.28">
            <line
              x1={c.x}
              y1={c.y - 6}
              x2={c.x}
              y2={c.y + c.h + 6}
              stroke={c.bullish ? "#00C853" : "#EF5350"}
              strokeWidth="1"
            />
            <rect
              x={c.x - 3}
              y={c.y}
              width={6}
              height={c.h}
              fill={c.bullish ? "#00C853" : "#EF5350"}
              rx="1"
            />
          </g>
        ))}

        <rect width={W} height={H} fill="url(#mp-vignette)" />
      </svg>
    </div>
  );
}
