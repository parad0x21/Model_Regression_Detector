"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, GitBranch, Loader2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type State = "idle" | "loading" | "confirm" | "done" | "error";

/**
 * Promote a run to baseline from the UI (previously CLI-only). Honors the platform's
 * "never silently overwrite with a worse run" rule: a run with regressions returns a
 * 200 with `promoted:false` + reasons, which we surface as an explicit "promote anyway".
 */
export function PromoteButton({
  feature,
  runUuid,
  isBaseline,
  size = "sm",
}: {
  feature: string;
  runUuid: string;
  isBaseline: boolean;
  size?: "sm" | "md";
}) {
  const router = useRouter();
  const [state, setState] = useState<State>("idle");
  const [reasons, setReasons] = useState<string[]>([]);

  async function promote(force: boolean) {
    setState("loading");
    try {
      const res = await fetch(`/api/features/${feature}/baseline/promote`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ run_uuid: runUuid, promoted_by: "web", force }),
      });
      const data = await res.json();
      if (data.promoted) {
        setState("done");
        router.refresh();
        setTimeout(() => setState("idle"), 1600);
      } else {
        setReasons(data.eligibility?.reasons ?? []);
        setState("confirm");
      }
    } catch {
      setState("error");
    }
  }

  if (isBaseline) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-lg border border-signal/30 bg-signal/10 px-3 py-1.5 text-[13px] font-medium text-signal">
        <GitBranch size={14} /> Current baseline
      </span>
    );
  }

  if (state === "confirm") {
    return (
      <div className="flex flex-col items-end gap-1.5">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-[12px] text-warning">
            <TriangleAlert size={13} /> Has regressions
          </span>
          <Button size={size} variant="danger" onClick={() => promote(true)}>
            Promote anyway
          </Button>
          <Button size={size} variant="ghost" onClick={() => setState("idle")}>
            Cancel
          </Button>
        </div>
        {reasons[0] && <span className="max-w-xs text-right text-[11px] text-mute">{reasons[0]}</span>}
      </div>
    );
  }

  return (
    <Button
      size={size}
      variant={state === "done" ? "outline" : "outline"}
      onClick={() => promote(false)}
      disabled={state === "loading"}
      className={cn(state === "done" && "border-healthy/40 text-healthy")}
    >
      {state === "loading" ? (
        <Loader2 size={14} className="animate-spin" />
      ) : state === "done" ? (
        <Check size={14} />
      ) : (
        <GitBranch size={14} />
      )}
      {state === "done" ? "Promoted" : "Promote to baseline"}
    </Button>
  );
}
