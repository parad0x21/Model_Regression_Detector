import { Clock, Cpu, FileText, Hash, Zap } from "lucide-react";
import { getRun, getRunRegressions, type SegmentStat } from "@/lib/api";
import { cn, num, pct, points } from "@/lib/utils";
import { Reveal } from "@/components/ui/reveal";
import { ScoreRing } from "@/components/ui/gauge";
import { Meter } from "@/components/ui/bar";
import { StatusPill, Tag } from "@/components/ui/status";
import { CopyId } from "@/components/ui/copy-id";
import { CasesExplorer } from "@/components/cases-explorer";
import { PromoteButton } from "@/components/promote-button";

export const dynamic = "force-dynamic";

function segTone(rate: number): string {
  if (rate < 0.5) return "var(--critical)";
  if (rate < 0.85) return "var(--warning)";
  return "var(--healthy)";
}

export default async function RunDetail({
  params,
}: {
  params: Promise<{ feature: string; runId: string }>;
}) {
  const { feature, runId } = await params;
  const [run, reg] = await Promise.all([
    getRun(runId),
    getRunRegressions(runId).catch(() => null),
  ]);
  const m = run.metrics;
  const segments = [...m.segments].sort((a, b) => a.pass_rate - b.pass_rate);
  const regressed = run.regression?.regressions ?? [];
  const started = new Date(run.start_time).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <div className="space-y-5">
      {/* Verdict hero */}
      <Reveal>
        <section className="panel relative overflow-hidden p-6 md:p-7">
          <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full blur-3xl" style={{ background: `radial-gradient(circle, ${run.verdict.health === "critical" ? "oklch(0.68 0.2 22 / 0.12)" : "oklch(0.82 0.125 202 / 0.1)"}, transparent 70%)` }} />

          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[12px] text-mute">Run #{run.sequence}</span>
              <span className="text-mute">·</span>
              <span className="font-mono text-[12px] text-mute">{run.model}</span>
            </div>
            <div className="flex items-center gap-2.5">
              <PromoteButton feature={feature} runUuid={run.run_uuid} isBaseline={run.is_baseline} />
              <CopyId value={run.run_uuid} />
            </div>
          </div>

          <div className="mt-5 flex flex-col items-center gap-8 sm:flex-row">
            <ScoreRing
              value={m.pass_rate}
              health={run.verdict.health}
              size={170}
              baseline={run.baseline?.pass_rate ?? null}
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-3">
                <StatusPill health={run.verdict.health} />
                {run.regression?.is_blocking && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-critical/12 px-2.5 py-1 text-xs font-medium text-critical ring-1 ring-inset ring-critical/30">
                    Blocks deploy
                  </span>
                )}
              </div>
              <p className="mt-3 font-display text-3xl leading-tight text-bright md:text-[34px]">
                {run.verdict.standing}.
              </p>
              <p className="mt-1.5 text-[15px] text-dim">
                {run.verdict.evidence}
                {run.baseline?.label ? ` — baseline is ${pct(run.baseline.pass_rate, 0)} (${run.baseline.label}).` : "."}
              </p>

              <div className="mt-5 flex flex-wrap gap-2">
                <Meta icon={<FileText size={12} />} label={`prompt ${run.prompt_version}`} />
                <Meta icon={<Hash size={12} />} label={`dataset ${run.dataset_version}`} />
                <Meta icon={<Clock size={12} />} label={`${run.duration_seconds.toFixed(1)}s`} />
                <Meta icon={<Zap size={12} />} label={`p95 ${Math.round(m.latency.p95_ms)}ms`} />
                <Meta icon={<Cpu size={12} />} label={`${num(m.tokens.total_tokens)} tok`} />
                <Meta label={`via ${run.triggered_by}`} />
                <Meta label={started} />
              </div>
            </div>
          </div>
        </section>
      </Reveal>

      {/* Quality breakdown */}
      <Reveal delay={80}>
        <section className="panel p-6">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-[1fr_1fr_minmax(180px,0.7fr)]">
            <div>
              <p className="kicker mb-3.5">Quality by check</p>
              <div className="space-y-3.5">
                {m.scorers.map((s) => (
                  <Meter key={s.name} label={s.label} value={s.mean_score} color="var(--signal)" trailing={pct(s.mean_score, 0)} />
                ))}
              </div>
            </div>
            <div>
              <p className="kicker mb-3.5">Quality by {m.segment_field ?? "segment"}</p>
              <div className="space-y-3.5">
                {segments.map((s: SegmentStat) => (
                  <Meter key={s.segment} label={s.segment} value={s.pass_rate} color={segTone(s.pass_rate)} trailing={pct(s.pass_rate, 0)} />
                ))}
              </div>
            </div>
            <div className="space-y-3 md:border-l md:border-line md:pl-7">
              <Tile label="Cases" value={String(m.total_cases)} />
              <Tile label="Mean latency" value={`${Math.round(m.latency.mean_ms)}ms`} />
              <Tile label="Tokens / case" value={String(Math.round(m.tokens.mean_tokens_per_case))} />
            </div>
          </div>
        </section>
      </Reveal>

      {/* Why it regressed */}
      {regressed.length > 0 && (
        <Reveal delay={140}>
          <section className="rounded-[18px] border border-critical/25 bg-critical/[0.05] p-6">
            <p className="kicker text-critical/90">Why it regressed</p>
            <p className="mt-1 text-[14px] text-dim">
              {run.regression?.critical_count ?? 0} critical, {run.regression?.warning_count ?? 0} warning
              {run.regression?.prompt_changed ? " · prompt changed" : ""}
              {run.regression?.dataset_changed ? " · dataset changed" : ""}
            </p>
            <ul className="mt-4 space-y-2.5">
              {regressed.map((r) => (
                <li key={r.name} className="flex items-start gap-3">
                  <span
                    className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: r.severity === "critical" ? "var(--critical)" : "var(--warning)" }}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="text-[13.5px] text-text">{r.reason}</span>
                  </span>
                  <span className="shrink-0 tnum text-[13px] text-critical">{points(r.delta)} pts</span>
                </li>
              ))}
            </ul>
          </section>
        </Reveal>
      )}

      {/* Test log */}
      <Reveal delay={200}>
        <section className="panel p-6">
          <div className="mb-4 flex items-baseline justify-between">
            <p className="kicker">Test log</p>
            <span className="text-[12px] text-mute">{m.total_cases} cases · {m.failed + m.errored} need review</span>
          </div>
          <CasesExplorer cases={run.cases} segmentField={m.segment_field} />
        </section>
      </Reveal>
    </div>
  );
}

function Meta({ icon, label }: { icon?: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface/50 px-2 py-1 font-mono text-[11px] text-dim">
      {icon}
      {label}
    </span>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="text-[13px] text-mute">{label}</span>
      <span className="tnum text-[15px] text-bright">{value}</span>
    </div>
  );
}
