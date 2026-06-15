import { GitBranch } from "lucide-react";
import { getBaseline, type BaselineInfo } from "@/lib/api";
import { pct, timeAgo } from "@/lib/utils";
import { Reveal } from "@/components/ui/reveal";
import { Tag } from "@/components/ui/status";

export const dynamic = "force-dynamic";

export default async function BaselinePage({
  params,
}: {
  params: Promise<{ feature: string }>;
}) {
  const { feature } = await params;
  const baseline = await getBaseline(feature);
  const { active, history } = baseline;

  return (
    <div className="space-y-5">
      {/* Active baseline hero */}
      <Reveal>
        {active ? (
          <section className="panel relative overflow-hidden p-6 md:p-7">
            {/* Subtle glow */}
            <div
              className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full blur-3xl"
              style={{
                background:
                  "radial-gradient(circle, oklch(0.82 0.125 202 / 0.12), transparent 70%)",
              }}
            />

            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-2">
                <GitBranch size={15} className="text-signal" />
                <p className="kicker text-signal/80">Active baseline</p>
              </div>
              <Tag className="border-signal/30 text-signal/90">active</Tag>
            </div>

            <div className="mt-4 flex flex-col gap-6 sm:flex-row sm:items-end">
              <div>
                <p className="tnum font-mono text-[52px] font-semibold leading-none text-bright">
                  {pct(active.pass_rate, 1)}
                </p>
                <p className="mt-2 text-[15px] font-medium text-text">{active.run_label}</p>
              </div>
              <div className="space-y-1 pb-1 text-[13px] text-mute">
                <p>
                  Promoted by{" "}
                  <span className="font-mono text-dim">{active.promoted_by}</span>
                </p>
                <p>{timeAgo(active.promoted_at)}</p>
                {active.note && (
                  <p className="mt-2 max-w-sm rounded-lg border border-line bg-surface/40 px-3 py-2 text-[12.5px] italic text-dim">
                    "{active.note}"
                  </p>
                )}
              </div>
            </div>

            <p className="mt-5 border-t border-line pt-4 text-[12.5px] text-mute">
              The baseline is the trusted bar every new run is measured against — regressions are
              detected when a candidate run falls below it on key metrics.
            </p>
          </section>
        ) : (
          <section className="panel p-8 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-line bg-surface/60">
              <GitBranch size={20} className="text-mute" />
            </div>
            <p className="text-[15px] font-medium text-dim">No baseline set yet</p>
            <p className="mx-auto mt-2 max-w-sm text-[13px] text-mute">
              The baseline is the trusted bar every new run is measured against. Promote a run to
              baseline from its detail page to enable regression detection.
            </p>
          </section>
        )}
      </Reveal>

      {/* Promotion history */}
      {history.length > 0 && (
        <Reveal delay={70}>
          <section className="panel p-6">
            <p className="kicker mb-4">Promotion history</p>
            <div className="divide-y divide-line">
              {history.map((b: BaselineInfo) => (
                <div
                  key={b.id}
                  className="flex items-center gap-4 py-3 first:pt-0 last:pb-0"
                >
                  {/* Pass rate */}
                  <span className="tnum w-16 shrink-0 font-mono text-[18px] font-semibold text-bright">
                    {pct(b.pass_rate, 0)}
                  </span>

                  {/* Label + meta */}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13px] text-text">{b.run_label ?? "—"}</span>
                      {b.is_active && (
                        <Tag className="border-signal/30 text-signal/90">active</Tag>
                      )}
                    </div>
                    <p className="mt-0.5 font-mono text-[11px] text-mute">
                      {b.promoted_by} · {timeAgo(b.promoted_at)}
                    </p>
                  </div>

                  {/* Note */}
                  {b.note && (
                    <p className="hidden max-w-[200px] truncate text-right text-[12px] italic text-mute sm:block">
                      "{b.note}"
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>
        </Reveal>
      )}
    </div>
  );
}
