"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

/** A compact, click-to-copy run identifier — keeps the UUID present but quiet. */
export function CopyId({ value, className }: { value: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1200);
        } catch {
          /* clipboard unavailable */
        }
      }}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border border-line bg-surface/40 px-2 py-1 font-mono text-[11px] text-mute transition-colors hover:text-dim hover:border-line-2",
        className,
      )}
      title="Copy run id"
    >
      {copied ? <Check size={11} className="text-healthy" /> : <Copy size={11} />}
      {value.slice(0, 8)}
    </button>
  );
}
