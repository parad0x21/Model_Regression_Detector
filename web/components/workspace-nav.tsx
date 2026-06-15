"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { key: "", label: "Overview" },
  { key: "runs", label: "Runs" },
  { key: "trends", label: "Trends" },
  { key: "compare", label: "Compare" },
  { key: "regressions", label: "Regressions" },
  { key: "dataset", label: "Dataset" },
  { key: "baseline", label: "Baseline" },
] as const;

export function WorkspaceNav({ feature }: { feature: string }) {
  const pathname = usePathname();
  const base = `/features/${feature}`;

  return (
    <nav className="flex gap-1 overflow-x-auto border-b border-line">
      {TABS.map((t) => {
        const href = t.key ? `${base}/${t.key}` : base;
        // Active when the path matches exactly (overview) or starts with the tab segment.
        const active =
          t.key === ""
            ? pathname === base
            : pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={t.key || "overview"}
            href={href}
            className={cn(
              "relative whitespace-nowrap px-3.5 py-2.5 text-[13.5px] font-medium transition-colors",
              active ? "text-bright" : "text-mute hover:text-text",
            )}
          >
            {t.label}
            {active && (
              <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-signal" style={{ boxShadow: "0 0 8px var(--signal)" }} />
            )}
          </Link>
        );
      })}
    </nav>
  );
}
