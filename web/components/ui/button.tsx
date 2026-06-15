"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const button = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-150 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-45 select-none",
  {
    variants: {
      variant: {
        signal:
          "bg-signal text-ink hover:brightness-110 shadow-[0_0_0_1px_oklch(0.82_0.125_202/0.4),0_8px_24px_-12px_oklch(0.82_0.125_202/0.7)]",
        solid: "bg-bright text-ink hover:bg-white",
        outline:
          "border border-line-2 bg-surface/40 text-text hover:bg-surface-2 hover:border-line-2",
        ghost: "text-dim hover:text-bright hover:bg-surface-2",
        danger:
          "bg-critical/15 text-critical border border-critical/30 hover:bg-critical/25",
      },
      size: {
        sm: "h-8 px-3 text-[13px]",
        md: "h-10 px-4",
        lg: "h-11 px-5 text-[15px]",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "outline", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp ref={ref} className={cn(button({ variant, size }), className)} {...props} />;
  },
);
Button.displayName = "Button";
