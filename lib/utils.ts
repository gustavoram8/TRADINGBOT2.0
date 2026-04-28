import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt(value: number, decimals = 2): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function fmtUSD(value: number, decimals = 0): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : value > 0 ? "+" : "";
  return `${sign}$${abs.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

export function fmtPct(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function pnlColor(value: number): string {
  if (value > 0) return "text-fin-green";
  if (value < 0) return "text-fin-red";
  return "text-text-secondary";
}

export function pnlBg(value: number): string {
  if (value > 0) return "bg-fin-green/10 text-fin-green";
  if (value < 0) return "bg-fin-red/10 text-fin-red";
  return "bg-bg-tertiary text-text-secondary";
}
