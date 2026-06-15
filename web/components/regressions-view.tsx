"use client";

import { useEffect, useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import type { RegressionsResponse, RunSummary } from "@/lib/api";
import { cn, points } from "@/lib/utils";
import { StatusPill } from "@/components/ui/status";
import { CasesExplorer } from "@/components/cases-explorer";

const sevToHealth: Record<string, string> = { pass: "healthy", warning: "warning", critical: "critical" };

export function RegressionsView({
  feature,
  runs,
  initial,
  segmentField,
}: {
  feature: string;
  runs: RunSummary[];
  initial: RegressionsResponse;
  segmentField: string | null;
}) {
  const [runUuid, setRunUuid] = useState(initial.run_uuid);
  const [data, setData] = useState<RegressionsResponse>(initial);
  const [loading, setLoading] = useState(false);
  const firstMetric = initial.comparison?.regressions[0]?.name ?? null;
  const [metric, setMetric] = useState<string | null>(firstMetric);

  useEffect(() => {
    if (runUuid === initial.run_uuid) {
      setData(initial);
      setMetric(initial.comparison?.regressions[0]?.name ?? null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetch(`/api/runs/${runUuid}/regressions`)
      .then((r) => r.json())
      .then((d: RegressionsResponse) => {
        if (cancelled) return;
        setData(d);
        setMetric(d.comparison?.regressions[0]?.name ?? null);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [runUuid, initial]);

  const regressed = data.comparison?.regressions ?? [];
  const cases = metric ? (data.root_cause[metric] ?? []) : [];

  return (
    <div className="space-y-5">
      <section className="panel p-5">
        <label className="block max-w-md">
          <span className="kicker">Candidate run</span>
          <select
            value={runUuid}
            onChange={(e) => setRunUuid(e.target.value)}
            className="mt-1.5 h-11 w-full rounded-xl border border-line bg-surface/50 px-3 font-mono text-[13px] text-text focus:border-signal/40 focus:outline-none"
          >
            {runs.map((r) => (
              <option key={r.run_uuid} value={r.run_uuid}>
                #{r.sequence} · {Math.round(r.pass_rate * 100)}% · {r.health}
              </option>
            ))}
          </select>
        </label>
      </section>

      {loading ? (
        <div className="panel flex items-center justify-center p-12 text-mute">
          <Loader2 className="animate-spin" size={18} />
        </div>
      ) : !data.comparison || regressed.length === 0 ? (
        <div className="panel flex flex-col items-center justify-center p-14 text-center">
          <span className="grid h-12 w-12 place-items-center rounded-xl bg-healthy/10 ring-1 ring-healthy/25">
            <ShieldCheck className="text-healthy" size={22} />
          </span>
          <p className="mt-4 font-display text-xl text-bright">No regressions on this run</p>
          <p className="mt-1.5 max-w-sm text-[13.5px] text-dim">
            {data.has_baseline
              ? "Every metric held or improved against the baseline."
              : "No baseline is set yet, so there is nothing to regress against."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[300px_1fr]">
          {/* Regressed metrics list */}
          <section className="panel h-fit p-5">
            <div className="mb-3 flex items-center justify-between">
              <p className="kicker">Regressed metrics</p>
              <StatusPill
                health={sevToHealth[data.comparison.severity] ?? "critical"}
                label={`${data.comparison.critical_count}C · ${data.comparison.warning_count}W`}
              />
            </div>
            <div className="space-y-1.5">
              {regressed.map((r) => {
                const active = r.name === metric;
                const count = data.root_cause[r.name]?.length ?? 0;
                return (
                  <button
                    key={r.name}
                    type="button"
                    onClick={() => setMetric(r.name)}
                    className={cn(
                      "w-full rounded-xl border px-3.5 py-3 text-left transition-colors",
                      active
                        ? "border-line-2 bg-surface-2"
                        : "border-line bg-surface/30 hover:bg-surface/60",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-[13px] text-text">{r.label}</span>
                      <span className="tnum shrink-0 text-[12px] text-critical">{points(r.delta)}</span>
                    </div>
                    <p className="mt-1 text-[11.5px] text-mute">
                      {count > 0 ? `${count} cases` : "aggregate metric"}
                    </p>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Contributing cases */}
          <section className="panel p-6">
            {metric && (
              <div className="mb-4">
                <p className="kicker">Root cause</p>
                <p className="mt-1.5 text-[14px] text-dim">
                  {regressed.find((r) => r.name === metric)?.reason}
                </p>
              </div>
            )}
            {cases.length > 0 ? (
              <CasesExplorer cases={cases} segmentField={segmentField} />
            ) : (
              <p className="rounded-xl border border-line bg-surface/30 px-4 py-8 text-center text-[13px] text-mute">
                This is an aggregate metric (latency/tokens) — not attributable to specific cases.
              </p>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
