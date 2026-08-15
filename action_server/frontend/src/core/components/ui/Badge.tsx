import * as React from "react";
import { cn } from "@/shared/utils/cn";
import { StatusIcon, type StatusName } from "@/shared/components/Icons";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "success"
    | "error"
    | "warning"
    | "info"
    | "neutral"
    | "primary"
    | "secondary";
  status?: StatusName;
}

const VARIANT_CLASSES: Record<NonNullable<BadgeProps["variant"]>, string> = {
  success:
    "bg-success/10 text-success dark:bg-success/15 dark:text-success border border-success/20 dark:border-success/30",
  error:
    "bg-destructive/10 text-destructive dark:bg-destructive/15 dark:text-destructive border border-destructive/20 dark:border-destructive/30",
  warning:
    "bg-warning/10 text-warning dark:bg-warning/15 dark:text-yellow-400 border border-warning/20 dark:border-warning/30",
  info: "bg-info/10 text-info dark:bg-info/15 dark:text-info border border-info/20 dark:border-info/30",
  neutral:
    "bg-muted text-muted-foreground dark:bg-muted/50 dark:text-muted-foreground border border-border",
  // Type badges for distinguishing Actions vs Robots
  primary:
    "bg-primary/10 text-primary dark:bg-primary/15 dark:text-primary border border-primary/20 dark:border-primary/30",
  secondary:
    "bg-info/10 text-info dark:bg-info/15 dark:text-cyan-400 border border-info/20 dark:border-info/30",
};

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = "neutral", status, children, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          // Layout & typography
          "inline-flex min-h-6 items-center gap-1.5 px-2.5 py-0.5 text-xs font-medium",
          // Style
          "rounded-full",
          // Animations
          "transition-colors duration-[var(--duration-interaction)]",
          "motion-reduce:transition-none",
          // Variant styles
          VARIANT_CLASSES[variant],
          className,
        )}
        {...props}
      >
        {status && <StatusIcon status={status} size={16} />}
        {children}
      </span>
    );
  },
);

Badge.displayName = "Badge";

export { Badge };
