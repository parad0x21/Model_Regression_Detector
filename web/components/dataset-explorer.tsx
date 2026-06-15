"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import type { DatasetCase, DatasetView } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Tag } from "@/components/ui/status";
import { Meter } from "@/components/ui/bar";

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: "var(--healthy)",
  medium: "var(--warning)",
  hard: "var(--critical)",
};

function difficultyTone(d: string): string {
  return DIFFICULTY_COLOR[d.toLowerCase()] ?? "var(--mute)";
}

function DifficultyBadge({ value }: { value: string }) {
  const color = difficultyTone(value);
  return (
    <span
      className="inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-[11px]"
      style={{
        borderColor: `${color}40`,
        color,
        backgroundColor: `${color}12`,
      }}
    >
      {value}
    </span>
  );
}

function CaseRow({ c }: { c: DatasetCase }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-line bg-surface/30 px-4 py-3 transition-colors hover:border-line-2">
      <span className="mt-0.5 shrink-0 font-mono text-[11px] text-mute">{c.case_id}</span>
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-1.5">
          {c.category && <Tag>{c.category}</Tag>}
          <DifficultyBadge value={c.difficulty} />
        </div>
        <p className="line-clamp-2 text-[13px] text-dim">{c.input_text}</p>
        {c.notes && <p className="text-[12px] text-mute">{c.notes}</p>}
      </div>
    </div>
  );
}

export function DatasetExplorer({ data }: { data: DatasetView }) {
  const allDifficulties = useMemo(
    () => Array.from(new Set(data.cases.map((c) => c.difficulty))).sort(),
    [data.cases],
  );
  const allCategories = useMemo(
    () =>
      Array.from(new Set(data.cases.map((c) => c.category).filter(Boolean) as string[])).sort(),
    [data.cases],
  );

  const [selectedDifficulties, setSelectedDifficulties] = useState<Set<string>>(new Set());
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");

  function toggleDifficulty(d: string) {
    setSelectedDifficulties((prev) => {
      const next = new Set(prev);
      if (next.has(d)) next.delete(d);
      else next.add(d);
      return next;
    });
  }

  function toggleCategory(c: string) {
    setSelectedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return data.cases.filter((c) => {
      if (selectedDifficulties.size > 0 && !selectedDifficulties.has(c.difficulty)) return false;
      if (
        selectedCategories.size > 0 &&
        (c.category === null || !selectedCategories.has(c.category))
      )
        return false;
      if (q) {
        const hay =
          `${c.case_id} ${c.input_text} ${c.notes} ${c.category ?? ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [data.cases, selectedDifficulties, selectedCategories, query]);

  const maxByDifficulty = Math.max(...data.coverage.by_difficulty.map((d) => d.count), 1);
  const maxByCategory = Math.max(...data.coverage.by_category.map((d) => d.count), 1);

  return (
    <div className="space-y-5">
      {/* Coverage section */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div className="panel p-5">
          <p className="kicker mb-3.5">By difficulty</p>
          <div className="space-y-3">
            {data.coverage.by_difficulty.map((d) => (
              <Meter
                key={d.key}
                label={d.key}
                value={d.count / maxByDifficulty}
                color={difficultyTone(d.key)}
                trailing={`${d.count}`}
              />
            ))}
          </div>
        </div>
        <div className="panel p-5">
          <p className="kicker mb-3.5">By category</p>
          <div className="space-y-3">
            {data.coverage.by_category.map((d) => (
              <Meter
                key={d.key}
                label={d.key}
                value={d.count / maxByCategory}
                color="var(--signal)"
                trailing={`${d.count}`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Difficulty chips */}
        <div className="flex items-center gap-1 rounded-lg border border-line bg-surface/40 p-1">
          <span className="px-2 font-mono text-[11px] text-mute">diff</span>
          {allDifficulties.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => toggleDifficulty(d)}
              className={cn(
                "rounded-md px-3 py-1.5 font-mono text-[12px] font-medium transition-colors",
                selectedDifficulties.has(d)
                  ? "bg-surface-2 text-bright"
                  : "text-mute hover:text-text",
              )}
            >
              {d}
            </button>
          ))}
        </div>

        {/* Category chips */}
        {allCategories.length > 0 && (
          <div className="flex flex-wrap items-center gap-1 rounded-lg border border-line bg-surface/40 p-1">
            <span className="px-2 font-mono text-[11px] text-mute">cat</span>
            {allCategories.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => toggleCategory(c)}
                className={cn(
                  "rounded-md px-3 py-1.5 font-mono text-[12px] font-medium transition-colors",
                  selectedCategories.has(c)
                    ? "bg-surface-2 text-bright"
                    : "text-mute hover:text-text",
                )}
              >
                {c}
              </button>
            ))}
          </div>
        )}

        {/* Search */}
        <div className="relative ml-auto">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-mute" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search cases…"
            className="h-9 w-56 rounded-lg border border-line bg-surface/40 pl-9 pr-3 text-[13px] text-text placeholder:text-mute focus:border-signal/40 focus:outline-none"
          />
        </div>
      </div>

      {/* Case list */}
      <div>
        <p className="mb-3 text-[12px] text-mute">
          {filtered.length} of {data.case_count} cases
        </p>
        <div className="space-y-2">
          {filtered.map((c) => (
            <CaseRow key={c.case_id} c={c} />
          ))}
          {filtered.length === 0 && (
            <p className="rounded-xl border border-line bg-surface/30 px-4 py-8 text-center text-[13px] text-mute">
              No cases match the current filters.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
