import { getFeature, getRunRegressions, getRuns } from "@/lib/api";
import { Reveal } from "@/components/ui/reveal";
import { RegressionsView } from "@/components/regressions-view";

export const dynamic = "force-dynamic";

export default async function RegressionsPage({
  params,
}: {
  params: Promise<{ feature: string }>;
}) {
  const { feature } = await params;
  const [runs, overview] = await Promise.all([getRuns(feature), getFeature(feature)]);

  if (runs.length === 0) {
    return <div className="panel p-10 text-center text-dim">No runs to analyze yet.</div>;
  }

  // Default to the most recent flagged run so the page opens on something actionable.
  const flagged = runs.find((r) => r.health === "critical" || r.health === "warning");
  const target = flagged ?? runs[0];
  const initial = await getRunRegressions(target.run_uuid);

  return (
    <Reveal>
      <div className="mb-5">
        <p className="kicker">Root-cause analysis</p>
        <p className="mt-2 max-w-2xl text-[14px] text-dim">
          Trace any regressed metric down to the exact cases that caused it — the bridge between
          “a number dropped” and “here’s what the model got wrong.”
        </p>
      </div>
      <RegressionsView
        feature={feature}
        runs={runs}
        initial={initial}
        segmentField={overview.segment_field}
      />
    </Reveal>
  );
}
