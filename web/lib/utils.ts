import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a 0–1 ratio as a percentage string. */
export function pct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

/** Signed pass-rate points, e.g. +3 / -20 (used for deltas vs baseline). */
export function points(delta: number | null | undefined): string {
  if (delta === null || delta === undefined) return "—";
  const p = Math.round(delta * 100);
  return `${p > 0 ? "+" : ""}${p}`;
}

/** Compact integer with thousands separators. */
export function num(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("en-US");
}

/** Short, human time-ago from an ISO timestamp. */
export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const secs = Math.max(1, Math.floor((Date.now() - then) / 1000));
  const units: [number, string][] = [
    [60, "s"],
    [60, "m"],
    [24, "h"],
    [30, "d"],
    [12, "mo"],
    [Number.POSITIVE_INFINITY, "y"],
  ];
  let value = secs;
  let unit = "s";
  for (const [size, label] of units) {
    if (value < size) {
      unit = label;
      break;
    }
    value = Math.floor(value / size);
    unit = label;
  }
  return `${value}${unit} ago`;
}

export type Health = "healthy" | "warning" | "critical" | "unknown";

/** Map a health verdict to its design-token color variable. */
export function healthColor(health: string): string {
  switch (health) {
    case "critical":
      return "var(--critical)";
    case "warning":
      return "var(--warning)";
    case "healthy":
      return "var(--healthy)";
    default:
      return "var(--mute)";
  }
}

export function titleCase(slug: string): string {
  return slug
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
