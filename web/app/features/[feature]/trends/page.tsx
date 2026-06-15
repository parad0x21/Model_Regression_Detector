import { getBaseline, getTrend } from "@/lib/api";
import { pct } from "@/lib/utils";
import { Reveal } from "@/components/ui/reveal";
import { PassRateChart, ResourceChart, ScorerChart } from "@/components/trend-chart";

export const dynamic = "force-dynamic";

export default async function TrendsPage({ params }: { params: Promise<{ feature: string }> }) {
  const { feature } = await params;
  const [trend, baseline] = await Promise.all([getTrend(feature), getBaseline(feature)]);

  if (trend.length === 0) {
    return <div className="panel p-10 text-center text-dim">No runs to chart yet.</div>;
  }

  const first = trend[0];
  const last = trend[trend.length - 1];
  const delta = last.pass_rate - first.pass_rate;
  const direction = delta > 0.001 ? "rose" : delta < -0.001 ? "fell" : "held";
  const health = last.pass_rate < (baseline.active?.pass_rate ?? 0) - 0.05 ? "critical" : delta < -0.001 ? "warning" : "healthy";
  const hasScorers = Object.keys(last.scorer_means ?? {}).length > 0;

  return (
    <div className="space-y-5">
      <Reveal>
        <section className="panel p-6">
          <p className="kicker">Quality over time</p>
          <p className="mt-2 max-w-2xl font-display text-2xl leading-snug text-bright">
            Pass rate {direction} from {pct(first.pass_rate, 0)} to {pct(last.pass_rate, 0)}{" "}
            <span className="text-dim">across {trend.length} runs.</span>
          </p>
          <div className="mt-5">
            <PassRateChart data={trend} baseline={baseline.active?.pass_rate ?? null} feature={feature} health={health} />
          </div>
          <p className="mt-2 text-[12px] text-mute">Click any point to open that run.</p>
        </section>
      </Reveal>

      {hasScorers && (
        <Reveal delay={80}>
          <section className="panel p-6">
            <p className="kicker mb-1">Per-check quality</p>
            <p className="mb-4 text-[13px] text-dim">Each scorer's mean score across runs.</p>
            <ScorerChart data={trend} />
          </section>
        </Reveal>
      )}

      <Reveal delay={140}>
        <section className="panel p-6">
          <p className="kicker mb-1">Speed &amp; cost</p>
          <p className="mb-4 text-[13px] text-dim">
            Latency per run (ms). Tokens this run: {last.total_tokens.toLocaleString("en-US")}.
          </p>
          <ResourceChart data={trend} />
        </section>
      </Reveal>
    </div>
  );
}
