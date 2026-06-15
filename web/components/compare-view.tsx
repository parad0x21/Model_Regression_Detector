"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import type { Comparison, RunSummary } from "@/lib/api";
import { cn, pct, points } from "@/lib/utils";
import { StatusPill, Tag } from "@/components/ui/status";

const sevToHealth: Record<string, string> = { pass: "healthy", warning: "warning", critical: "critical" };

function RunSelect({
  label,
  value,
  runs,
  onChange,
}: {
  label: string;
  value: string;
  runs: RunSummary[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="block flex-1">
      <span className="kicker">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1.5 h-11 w-full rounded-xl border border-line bg-surface/50 px-3 font-mono text-[13px] text-text focus:border-signal/40 focus:outline-none"
      >
        {runs.map((r) => (
          <option key={r.run_uuid} value={r.run_uuid}>
            #{r.sequence} · {Math.round(r.pass_rate * 100)}% {r.is_baseline ? "· baseline" : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

function isHeadline(name: string): boolean {
  return name === "pass_rate" || (name.startsWith("scorer.") && name.endsWith(".mean_score"));
}

export function CompareView({
  feature,
  runs,
  initial,
  initialA,
  initialB,
}: {
  feature: string;
  runs: RunSummary[];
  initial: Comparison | null;
  initialA: string;
  initialB: string;
}) {
  const [a, setA] = useState(initialA);
  const [b, setB] = useState(initialB);
  const [data, setData] = useState<Comparison | null>(initial);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!a || !b) return;
    // The default pair is already server-rendered; only fetch on a real change.
    if (a === initialA && b === initialB) {
      setData(initial);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetch(`/api/compare?a=${a}&b=${b}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => !cancelled && setData(d))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [a, b, initial, initialA, initialB]);

  const headline = useMemo(
    () => (data ? data.comparisons.filter((c) => isHeadline(c.name)) : []),
    [data],
  );

  if (runs.length < 2) {
    return <div className="panel p-10 text-center text-dim">Need at least two runs to compare.</div>;
  }

  return (
    <div className="space-y-5">
      <section className="panel p-6">
        <div className="flex flex-col items-stretch gap-4 sm:flex-row sm:items-end">
          <RunSelect label="Reference (A)" value={a} runs={runs} onChange={setA} />
          <ArrowRight className="mb-3 hidden shrink-0 text-mute sm:block" size={18} />
          <RunSelect label="Candidate (B)" value={b} runs={runs} onChange={setB} />
        </div>
      </section>

      {loading && !data ? (
        <div className="panel flex items-center justify-center p-12 text-mute">
          <Loader2 className="animate-spin" size={18} />
        </div>
      ) : data ? (
        <>
          <section className="panel p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <StatusPill
                health={sevToHealth[data.severity] ?? "unknown"}
                label={
                  data.severity === "pass"
                    ? "No regressions"
                    : `${data.critical_count} critical · ${data.warning_count} warning`
                }
              />
              <div className="flex items-center gap-2">
                <Tag className={cn(data.prompt_changed && "border-signal/30 text-signal/90")}>
                  prompt {data.prompt_changed ? "changed" : "same"}
                </Tag>
                <Tag className={cn(data.dataset_changed && "border-signal/30 text-signal/90")}>
                  dataset {data.dataset_changed ? "changed" : "same"}
                </Tag>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
              {headline.map((c) => {
                const worse = c.regressed;
                const better = c.delta > 0 && !c.regressed;
                return (
                  <div key={c.name} className="panel-inset p-4">
                    <p className="truncate text-[12px] text-mute">{c.label}</p>
                    <p className="mt-1.5 font-mono text-xl font-semibold text-bright tnum">{pct(c.candidate_value, 0)}</p>
                    <p
                      className={cn(
                        "mt-0.5 tnum text-[12px]",
                        worse ? "text-critical" : better ? "text-healthy" : "text-mute",
                      )}
                    >
                      {points(c.delta)} pts vs A
                    </p>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="panel overflow-hidden">
            <div className="grid grid-cols-[1.4fr_repeat(4,0.7fr)] gap-px bg-line text-[12px]">
              {["Metric", "Run A", "Run B", "Δ", "Verdict"].map((h) => (
                <span key={h} className="bg-panel px-4 py-2.5 kicker">{h}</span>
              ))}
              {data.comparisons.map((c) => (
                <Row key={c.name} c={c} />
              ))}
            </div>
          </section>
        </>
      ) : (
        <div className="panel p-10 text-center text-mute">Select two runs.</div>
      )}
    </div>
  );
}

function fmt(v: number): string {
  return Math.abs(v) < 2 ? v.toFixed(3) : Math.round(v).toString();
}

function Row({ c }: { c: Comparison["comparisons"][number] }) {
  const tone = c.regressed ? "text-critical" : c.delta > 0 && c.kind === "quality" ? "text-healthy" : "text-dim";
  return (
    <>
      <span className="bg-panel px-4 py-2.5 text-[13px] text-text">{c.label}</span>
      <span className="bg-panel px-4 py-2.5 tnum text-[13px] text-dim">{fmt(c.baseline_value)}</span>
      <span className="bg-panel px-4 py-2.5 tnum text-[13px] text-bright">{fmt(c.candidate_value)}</span>
      <span className={cn("bg-panel px-4 py-2.5 tnum text-[13px]", tone)}>
        {c.delta > 0 ? "+" : ""}
        {fmt(c.delta)}
      </span>
      <span className="bg-panel px-4 py-2.5 text-[12px]">
        {c.regressed ? (
          <span className="text-critical">{c.severity}</span>
        ) : (
          <span className="text-mute">ok</span>
        )}
      </span>
    </>
  );
}
