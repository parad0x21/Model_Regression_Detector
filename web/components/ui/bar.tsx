import { cn } from "@/lib/utils";

/** A stacked pass / fail / error bar — the at-a-glance outcome distribution. */
export function SegmentedBar({
  passed,
  failed,
  errored,
  className,
  height = 8,
}: {
  passed: number;
  failed: number;
  errored: number;
  className?: string;
  height?: number;
}) {
  const total = Math.max(1, passed + failed + errored);
  const seg = (n: number) => `${(n / total) * 100}%`;
  return (
    <div
      className={cn("flex w-full overflow-hidden rounded-full bg-white/5", className)}
      style={{ height }}
    >
      <div style={{ width: seg(passed), backgroundColor: "var(--healthy)" }} />
      <div style={{ width: seg(failed), backgroundColor: "var(--critical)" }} />
      <div style={{ width: seg(errored), backgroundColor: "var(--warning)" }} />
    </div>
  );
}

/** A single labelled meter (used for per-segment / per-scorer pass rates). */
export function Meter({
  label,
  value,
  color,
  trailing,
}: {
  label: string;
  value: number;
  color?: string;
  trailing?: string;
}) {
  return (
    <div className="group">
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span className="truncate text-[13px] text-dim">{label}</span>
        <span className="tnum text-[13px] text-bright">{trailing ?? `${Math.round(value * 100)}%`}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className="h-full rounded-full transition-[width] duration-700"
          style={{ width: `${Math.max(2, value * 100)}%`, backgroundColor: color ?? "var(--signal)" }}
        />
      </div>
    </div>
  );
}
