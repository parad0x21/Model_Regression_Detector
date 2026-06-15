"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { TrendPoint } from "@/lib/api";
import { healthColor, pct } from "@/lib/utils";

/**
 * Bespoke SVG trend charts. Hand-built (not a chart lib) for full design control and
 * guaranteed rendering across the RSC/React-19 stack — pass-rate area with a baseline
 * reference, plus multi-line charts for scorers and latency. All share one scale/hover core.
 */

const PALETTE = ["var(--signal)", "var(--warning)", "var(--healthy)", "#c98bff", "#ff9e7a"];

function useChartWidth(fallback = 760): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver((e) => {
      const w = e[0]?.contentRect.width;
      if (w && w > 0) setWidth(Math.round(w));
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}

interface Series {
  key: string;
  color: string;
  label: string;
}

function SvgTrend({
  data,
  series,
  height = 260,
  yDomain,
  baseline,
  format,
  area = false,
  onClickPoint,
}: {
  data: Array<Record<string, number | string>>;
  series: Series[];
  height?: number;
  yDomain: [number, number];
  baseline?: number | null;
  format: (v: number) => string;
  area?: boolean;
  onClickPoint?: (i: number) => void;
}) {
  const [ref, width] = useChartWidth();
  const [hover, setHover] = useState<number | null>(null);
  const L = 48;
  const R = 16;
  const T = 14;
  const B = 28;
  const pw = Math.max(20, width - L - R);
  const ph = Math.max(20, height - T - B);
  const n = data.length;
  const [lo, hi] = yDomain;
  const span = hi - lo || 1;

  const x = (i: number) => (n <= 1 ? L + pw / 2 : L + (i / (n - 1)) * pw);
  const y = (v: number) => T + (1 - (v - lo) / span) * ph;
  const yTicks = [0, 1, 2, 3].map((k) => lo + (span * k) / 3);
  const labelEvery = n > 9 ? Math.ceil(n / 6) : 1;

  return (
    <div ref={ref} className="relative w-full" style={{ height }}>
      <svg
        width={width}
        height={height}
        onMouseMove={(e) => {
          const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const mx = e.clientX - rect.left;
          const i = Math.round(((mx - L) / pw) * (n - 1));
          setHover(Math.max(0, Math.min(n - 1, i)));
        }}
        onMouseLeave={() => setHover(null)}
        onClick={() => hover != null && onClickPoint?.(hover)}
        style={{ cursor: onClickPoint ? "pointer" : "default" }}
      >
        <defs>
          <linearGradient id="area-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={series[0].color} stopOpacity={0.34} />
            <stop offset="100%" stopColor={series[0].color} stopOpacity={0} />
          </linearGradient>
        </defs>

        {/* grid + y labels */}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={L} y1={y(t)} x2={width - R} y2={y(t)} stroke="oklch(1 0 0 / 0.05)" />
            <text x={L - 8} y={y(t) + 3} textAnchor="end" fontSize={10.5} fill="var(--mute)" fontFamily="var(--font-jetbrains)">
              {format(t)}
            </text>
          </g>
        ))}

        {/* x labels */}
        {data.map((d, i) =>
          i % labelEvery === 0 ? (
            <text key={i} x={x(i)} y={height - 8} textAnchor="middle" fontSize={10.5} fill="var(--mute)" fontFamily="var(--font-jetbrains)">
              {String(d.label)}
            </text>
          ) : null,
        )}

        {/* baseline */}
        {baseline != null && (
          <g>
            <line x1={L} y1={y(baseline)} x2={width - R} y2={y(baseline)} stroke="var(--bright)" strokeOpacity={0.45} strokeDasharray="4 4" />
            <text x={width - R} y={y(baseline) - 5} textAnchor="end" fontSize={10} fill="var(--mute)">baseline</text>
          </g>
        )}

        {/* area under first series */}
        {area && n > 1 && (
          <path
            d={
              data.map((d, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(Number(d[series[0].key]))}`).join(" ") +
              ` L${x(n - 1)},${T + ph} L${x(0)},${T + ph} Z`
            }
            fill="url(#area-fill)"
          />
        )}

        {/* series lines + dots */}
        {series.map((s) => (
          <g key={s.key}>
            <path
              d={data.map((d, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(Number(d[s.key]))}`).join(" ")}
              fill="none"
              stroke={s.color}
              strokeWidth={2.2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {data.map((d, i) => (
              <circle
                key={i}
                cx={x(i)}
                cy={y(Number(d[s.key]))}
                r={hover === i ? 4.5 : 3}
                fill={s.color}
                style={hover === i ? { filter: `drop-shadow(0 0 5px ${s.color})` } : undefined}
              />
            ))}
          </g>
        ))}

        {/* hover guide */}
        {hover != null && <line x1={x(hover)} y1={T} x2={x(hover)} y2={T + ph} stroke="var(--line-2)" />}
      </svg>

      {/* tooltip */}
      {hover != null && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 rounded-lg border border-line-2 bg-ink-2/95 px-3 py-2 shadow-xl backdrop-blur"
          style={{ left: Math.min(width - 70, Math.max(70, x(hover))), top: 6 }}
        >
          <p className="mb-1 font-mono text-[11px] text-mute">{String(data[hover].label)}</p>
          {series.map((s) => (
            <p key={s.key} className="flex items-center gap-2 text-[12px]">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
              <span className="text-dim">{s.label}</span>
              <span className="tnum ml-auto pl-3 text-bright">{format(Number(data[hover][s.key]))}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export function PassRateChart({
  data,
  baseline,
  feature,
  health,
}: {
  data: TrendPoint[];
  baseline: number | null;
  feature: string;
  health: string;
}) {
  const router = useRouter();
  const rows = data.map((d) => ({ label: d.label, pass_rate: d.pass_rate, run_uuid: d.run_uuid }));
  const min = Math.min(...data.map((d) => d.pass_rate), baseline ?? 1);
  const lo = Math.max(0, Math.floor((min - 0.12) * 10) / 10);
  return (
    <SvgTrend
      data={rows}
      series={[{ key: "pass_rate", color: healthColor(health), label: "Pass rate" }]}
      height={300}
      yDomain={[lo, 1]}
      baseline={baseline}
      area
      format={(v) => pct(v, 0)}
      onClickPoint={(i) => router.push(`/features/${feature}/runs/${data[i].run_uuid}`)}
    />
  );
}

export function ScorerChart({ data }: { data: TrendPoint[] }) {
  const keys = Array.from(new Set(data.flatMap((d) => Object.keys(d.scorer_means ?? {}))));
  const rows = data.map((d) => ({ label: d.label, ...d.scorer_means }));
  return (
    <SvgTrend
      data={rows}
      series={keys.map((k, i) => ({ key: k, color: PALETTE[i % PALETTE.length], label: k }))}
      height={220}
      yDomain={[0, 1]}
      format={(v) => pct(v, 0)}
    />
  );
}

export function ResourceChart({ data }: { data: TrendPoint[] }) {
  const rows = data.map((d) => ({
    label: d.label,
    p95: d.p95_latency_ms,
    mean: d.mean_latency_ms,
  }));
  const max = Math.max(...data.map((d) => d.p95_latency_ms), 1);
  return (
    <SvgTrend
      data={rows}
      series={[
        { key: "p95", color: "var(--warning)", label: "p95 latency" },
        { key: "mean", color: "var(--signal)", label: "mean latency" },
      ]}
      height={220}
      yDomain={[0, Math.ceil(max * 1.15)]}
      format={(v) => `${Math.round(v)}ms`}
    />
  );
}
