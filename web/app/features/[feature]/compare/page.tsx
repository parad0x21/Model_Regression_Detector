import { compareRuns, getRuns } from "@/lib/api";
import { Reveal } from "@/components/ui/reveal";
import { CompareView } from "@/components/compare-view";

export const dynamic = "force-dynamic";

export default async function ComparePage({ params }: { params: Promise<{ feature: string }> }) {
  const { feature } = await params;
  const runs = await getRuns(feature);

  // Default pair: the trusted baseline (or the previous run) vs the newest run.
  const baseline = runs.find((r) => r.is_baseline);
  const initialA = baseline?.run_uuid ?? runs[1]?.run_uuid ?? runs[0]?.run_uuid ?? "";
  const initialB = runs[0]?.run_uuid ?? "";
  const initial =
    initialA && initialB && initialA !== initialB
      ? await compareRuns(initialA, initialB).catch(() => null)
      : null;

  return (
    <Reveal>
      <div className="mb-5">
        <p className="kicker">Run vs run</p>
        <p className="mt-2 max-w-2xl text-[14px] text-dim">
          Diff any two evaluations to see exactly which metrics moved — and whether the prompt
          or dataset changed underneath them.
        </p>
      </div>
      <CompareView feature={feature} runs={runs} initial={initial} initialA={initialA} initialB={initialB} />
    </Reveal>
  );
}
