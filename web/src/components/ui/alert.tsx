import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

const alertVariants = cva(
  "relative grid w-full grid-cols-[auto_1fr] items-start gap-x-3 gap-y-1 rounded-lg border px-4 py-3 text-sm [&>svg]:mt-0.5 [&>svg]:size-4",
  {
    variants: {
      tone: {
        neutral: "bg-card text-card-foreground",
        info: "border-info/30 bg-info-soft text-foreground [&>svg]:text-info",
        warning: "border-warning/30 bg-warning-soft text-foreground [&>svg]:text-warning",
        success: "border-success/30 bg-success-soft text-foreground [&>svg]:text-success",
        danger: "border-danger/30 bg-danger-soft text-foreground [&>svg]:text-danger",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export function Alert({
  className,
  tone,
  ...props
}: ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return <div role="alert" className={cn(alertVariants({ tone }), className)} {...props} />;
}

export function AlertTitle({ className, ...props }: ComponentProps<"p">) {
  return <p className={cn("col-start-2 font-medium", className)} {...props} />;
}

export function AlertDescription({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("col-start-2 text-muted-foreground", className)} {...props} />;
}
