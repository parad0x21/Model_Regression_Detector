import { healthColor, pct } from "@/lib/utils";

/**
 * A circular pass-rate gauge — the run-detail hero's instrument readout.
 * The arc is colored by health; a faint baseline tick marks the bar to clear.
 */
export function ScoreRing({
  value,
  health,
  size = 156,
  stroke = 10,
  baseline,
  label = "pass rate",
}: {
  value: number;
  health: string;
  size?: number;
  stroke?: number;
  baseline?: number | null;
  label?: string;
}) {
  const r = (size - stroke) / 2 - 2;
  const c = 2 * Math.PI * r;
  const dash = Math.max(0, Math.min(1, value)) * c;
  const color = healthColor(health);
  const center = size / 2;
  // baseline marker angle (top = -90deg)
  const baseAngle = baseline != null ? -90 + baseline * 360 : null;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={center} cy={center} r={r} fill="none" stroke="oklch(1 0 0 / 0.08)" strokeWidth={stroke} />
        <circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c}`}
          style={{ filter: `drop-shadow(0 0 6px ${color})`, transition: "stroke-dasharray 0.9s cubic-bezier(0.22,1,0.36,1)" }}
        />
        {baseAngle != null && (
          <line
            x1={center + (r - stroke / 2 - 3) * Math.cos((baseAngle * Math.PI) / 180)}
            y1={center + (r - stroke / 2 - 3) * Math.sin((baseAngle * Math.PI) / 180)}
            x2={center + (r + stroke / 2 + 3) * Math.cos((baseAngle * Math.PI) / 180)}
            y2={center + (r + stroke / 2 + 3) * Math.sin((baseAngle * Math.PI) / 180)}
            stroke="var(--bright)"
            strokeWidth={2}
            opacity={0.6}
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-3xl font-semibold tracking-tight text-bright tnum">{pct(value, 0)}</span>
        <span className="kicker mt-1">{label}</span>
      </div>
    </div>
  );
}
