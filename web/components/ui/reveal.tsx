import { cn } from "@/lib/utils";

/**
 * Orchestrated entrance wrapper. Server-safe (pure CSS keyframe + delay), so views
 * get one staggered reveal on load without shipping client JS. Compose with an
 * increasing `delay` across siblings for the cascade.
 */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <div className={cn("animate-rise", className)} style={{ animationDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}
