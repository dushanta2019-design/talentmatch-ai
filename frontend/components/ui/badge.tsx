import * as React from "react";
import { cn } from "@/lib/utils";

const styles: Record<string, string> = {
  default: "bg-gray-100 text-gray-700",
  green: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-700",
  red: "bg-rose-100 text-rose-700",
  blue: "bg-brand-100 text-brand-700",
};

export function Badge({
  color = "default",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { color?: keyof typeof styles }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        styles[color],
        className
      )}
      {...props}
    />
  );
}
