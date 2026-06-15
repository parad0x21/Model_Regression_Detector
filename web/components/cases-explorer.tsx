"use client";

import { useMemo, useState } from "react";
import { Check, ChevronRight, Search, X } from "lucide-react";
import type { CaseRow } from "@/lib/api";
import { cn } from "@/lib/utils";

type Filter = "all" | "failing" | "passed";

function valueToText(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}

/** Side-by-side expected vs actual field comparison — the heart of explainability. */
function FieldDiff({ expected, actual }: { expected: Record<string, unknown>; actual: Record<string, unknown> | null }) {
  const keys = Array.from(new Set([...Object.keys(expected), ...Object.keys(actual ?? {})]));
  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <div className="grid grid-cols-[120px_1fr_1fr] bg-surface/60 text-[11px]">
        <span className="px-3 py-2 kicker">field</span>
        <span className="px-3 py-2 kicker">expected</span>
        <span className="px-3 py-2 kicker">model output</span>
      </div>
      {keys.map((k) => {
        const exp = valueToText(expected[k]);
        const act = actual ? valueToText(actual[k]) : "—";
        const mismatch = exp !== act;
        return (
          <div key={k} className="grid grid-cols-[120px_1fr_1fr] border-t border-line text-[13px]">
            <span className="truncate px-3 py-2 font-mono text-mute">{k}</span>
            <span className="px-3 py-2 text-healthy/90">{exp}</span>
            <span
              className={cn(
                "px-3 py-2",
                mismatch ? "bg-critical/[0.08] font-medium text-critical" : "text-dim",
              )}
            >
              {act}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function CaseCard({ c, segmentField }: { c: CaseRow; segmentField: string | null }) {
  const [open, setOpen] = useState(false);
  const tone =
    c.outcome === "passed" ? "healthy" : c.outcome === "errored" ? "warning" : "critical";
  const dot =
    tone === "healthy" ? "var(--healthy)" : tone === "warning" ? "var(--warning)" : "var(--critical)";
  const category = segmentField ? valueToText(c.expected[segmentField]) : null;

  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border bg-surface/30 transition-colors",
        open ? "border-line-2" : "border-line hover:border-line-2",
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: dot, boxShadow: `0 0 6px ${dot}` }} />
        <span className="shrink-0 font-mono text-[12px] text-mute">{c.case_id}</span>
        {category && (
          <span className="shrink-0 rounded-md border border-line bg-surface/60 px-1.5 py-0.5 font-mono text-[10.5px] text-dim">
            {category}
          </span>
        )}
        <span className={cn("min-w-0 flex-1 truncate text-[13px]", c.passed ? "text-mute" : "text-text")}>
          {c.summary}
        </span>
        <ChevronRight size={15} className={cn("shrink-0 text-mute transition-transform", open && "rotate-90")} />
      </button>

      {open && (
        <div className="animate-fade space-y-4 border-t border-line px-4 py-4">
          {c.input_text && (
            <div>
              <p className="kicker mb-1.5">Input</p>
              <p className="panel-inset px-3 py-2.5 text-[13px] leading-relaxed text-dim">{c.input_text}</p>
            </div>
          )}
          {c.error ? (
            <div className="rounded-xl border border-warning/30 bg-warning/[0.07] px-3 py-2.5 text-[13px] text-warning">
              {c.error}
            </div>
          ) : (
            <FieldDiff expected={c.expected} actual={c.actual} />
          )}
          <div>
            <p className="kicker mb-2">Checks</p>
            <div className="space-y-1.5">
              {c.scorers.map((s) => (
                <div key={s.name} className="flex items-start gap-2.5 text-[13px]">
                  <span className="mt-0.5 shrink-0">
                    {s.passed ? (
                      <Check size={14} className="text-healthy" />
                    ) : (
                      <X size={14} className="text-critical" />
                    )}
                  </span>
                  <span className="shrink-0 font-mono text-mute">{s.name}</span>
                  <span className="text-dim">{s.detail}</span>
                  <span className="ml-auto shrink-0 tnum text-mute">{s.score.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function CasesExplorer({ cases, segmentField }: { cases: CaseRow[]; segmentField: string | null }) {
  const failingCount = cases.filter((c) => !c.passed).length;
  const [filter, setFilter] = useState<Filter>(failingCount > 0 ? "failing" : "all");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return cases
      .filter((c) => {
        if (filter === "failing" && c.passed) return false;
        if (filter === "passed" && !c.passed) return false;
        if (q) {
          const hay = `${c.case_id} ${c.input_text} ${JSON.stringify(c.expected)} ${JSON.stringify(c.actual)}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => Number(a.passed) - Number(b.passed)); // failures first
  }, [cases, filter, query]);

  const chips: { key: Filter; label: string; count: number }[] = [
    { key: "failing", label: "Failing", count: failingCount },
    { key: "passed", label: "Passed", count: cases.length - failingCount },
    { key: "all", label: "All", count: cases.length },
  ];

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1 rounded-lg border border-line bg-surface/40 p-1">
          {chips.map((chip) => (
            <button
              key={chip.key}
              type="button"
              onClick={() => setFilter(chip.key)}
              className={cn(
                "rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors",
                filter === chip.key ? "bg-surface-2 text-bright" : "text-mute hover:text-text",
              )}
            >
              {chip.label} <span className="tnum text-mute">{chip.count}</span>
            </button>
          ))}
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-mute" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search cases…"
            className="h-9 w-56 rounded-lg border border-line bg-surface/40 pl-9 pr-3 text-[13px] text-text placeholder:text-mute focus:border-signal/40 focus:outline-none"
          />
        </div>
      </div>

      <div className="space-y-2">
        {filtered.map((c) => (
          <CaseCard key={c.case_id} c={c} segmentField={segmentField} />
        ))}
        {filtered.length === 0 && (
          <p className="rounded-xl border border-line bg-surface/30 px-4 py-8 text-center text-[13px] text-mute">
            No cases match.
          </p>
        )}
      </div>
    </div>
  );
}
