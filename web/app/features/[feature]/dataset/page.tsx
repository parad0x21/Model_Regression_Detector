import { Database } from "lucide-react";
import { getDataset } from "@/lib/api";
import { Reveal } from "@/components/ui/reveal";
import { Tag } from "@/components/ui/status";
import { DatasetExplorer } from "@/components/dataset-explorer";

export const dynamic = "force-dynamic";

export default async function DatasetPage({
  params,
}: {
  params: Promise<{ feature: string }>;
}) {
  const { feature } = await params;
  const data = await getDataset(feature);

  return (
    <div className="space-y-5">
      {/* Header */}
      <Reveal>
        <section className="panel p-6">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line bg-surface/60">
              <Database size={16} className="text-signal" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-display text-xl text-bright">Golden dataset</p>
                <Tag>{data.version}</Tag>
              </div>
              {data.description && (
                <p className="mt-1 text-[14px] text-dim">{data.description}</p>
              )}
              <p className="mt-2 text-[13px] text-mute">
                <span className="tnum font-mono text-text">{data.case_count}</span> hand-labeled
                cases across{" "}
                <span className="tnum font-mono text-text">
                  {data.coverage.by_category.length}
                </span>{" "}
                {data.coverage.by_category.length === 1 ? "category" : "categories"}
                {data.segment_field ? ` · segmented by ${data.segment_field}` : ""}
              </p>
            </div>
          </div>
        </section>
      </Reveal>

      {/* Interactive explorer (client component) */}
      <Reveal delay={70}>
        <DatasetExplorer data={data} />
      </Reveal>
    </div>
  );
}
