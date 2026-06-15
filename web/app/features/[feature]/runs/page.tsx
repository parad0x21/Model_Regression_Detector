import Link from "next/link";
import { getRuns } from "@/lib/api";
import { cn, num, pct, timeAgo } from "@/lib/utils";
import { Reveal } from "@/components/ui/reveal";
import { SegmentedBar } from "@/components/ui/bar";
import { HealthDot, Tag } from "@/components/ui/status";

export const dynamic = "force-dynamic";

export default async function RunsTimeline({
  params,
}: {
  params: Promise<{ feature: string }>;
}) {
  const { feature } = await params;
  const runs = await getRuns(feature);

  if (runs.length === 0) {
    return (
      <Reveal>
        <div className="panel p-10 text-center">
          <p className="text-[15px] text-dim">No runs recorded for this feature yet.</p>
          <p className="mt-1.5 text-[13px] text-mute">
            Trigger an evaluation via the CLI to see runs here.
          </p>
        </div>
      </Reveal>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <Reveal>
        <div className="flex items-baseline justify-between">
          <div>
            <p className="kicker">Run history</p>
            <p className="mt-1 text-[13px] text-mute">{runs.length} total · newest first</p>
          </div>
        </div>
      </Reveal>

      {/* Timeline */}
      <Reveal delay={70}>
        <div className="panel divide-y divide-line overflow-hidden">
          {runs.map((run, i) => {
            const isCritical = run.health === "critical";
            const isWarning = run.health === "warning";
            return (
              <Link
                key={run.run_uuid}
                href={`/features/${feature}/runs/${run.run_uuid}`}
                className={cn(
                  "group flex items-center gap-4 px-5 py-4 transition-colors hover:bg-surface-2",
                  i === 0 && "rounded-t-[17px]",
                  i === runs.length - 1 && "rounded-b-[17px]",
                )}
              >
                {/* Sequence + health dot */}
                <div className="flex w-12 shrink-0 items-center gap-2">
                  <HealthDot health={run.health} />
                  <span className="font-mono text-[12px] text-mute">#{run.sequence}</span>
                </div>

                {/* Pass rate */}
                <div className="w-20 shrink-0 text-right">
                  <span
                    className={cn(
                      "tnum text-[22px] font-semibold leading-none",
                      isCritical ? "text-critical" : isWarning ? "text-warning" : "text-bright",
                    )}
                  >
                    {pct(run.pass_rate, 0)}
                  </span>
                </div>

                {/* Segmented bar */}
                <div className="hidden w-28 shrink-0 sm:block">
                  <SegmentedBar
                    passed={run.passed}
                    failed={run.failed}
                    errored={run.errored}
                    height={7}
                  />
                  <p className="mt-1 font-mono text-[10.5px] text-mute">
                    {run.passed}p · {run.failed}f
                    {run.errored > 0 ? ` · ${run.errored}e` : ""}
                  </p>
                </div>

                {/* Tags: model, versions */}
                <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
                  <Tag>{run.model}</Tag>
                  <Tag>p{run.prompt_version}</Tag>
                  <Tag>d{run.dataset_version}</Tag>
                  {run.is_baseline && (
                    <Tag className="border-signal/30 text-signal/90">baseline</Tag>
                  )}
                </div>

                {/* Triggered by + tokens */}
                <div className="hidden shrink-0 items-end gap-0.5 text-right md:flex md:flex-col">
                  <span className="font-mono text-[11px] text-mute">{run.triggered_by}</span>
                  <span className="tnum font-mono text-[11px] text-mute">
                    {num(run.total_tokens)} tok
                  </span>
                </div>

                {/* Time */}
                <div className="w-20 shrink-0 text-right">
                  <span className="font-mono text-[12px] text-mute">{timeAgo(run.started_at)}</span>
                </div>
              </Link>
            );
          })}
        </div>
      </Reveal>
    </div>
  );
}
