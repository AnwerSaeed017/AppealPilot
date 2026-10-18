import { cn } from "@/lib/utils";

const TONES = {
  primary: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
} as const;

/** A labelled horizontal gauge for a known range, such as a confidence or a share verified. */
export function Meter({
  label,
  value,
  max = 1,
  valueText,
  tone = "primary",
  className,
}: {
  label: string;
  value: number;
  max?: number;
  valueText: string;
  tone?: keyof typeof TONES;
  className?: string;
}) {
  const share = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;
  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-baseline justify-between gap-2 text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{valueText}</span>
      </div>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-valuetext={valueText}
        className="h-2 overflow-hidden rounded-full bg-muted"
      >
        <div className={cn("h-full rounded-full transition-[width]", TONES[tone])} style={{ width: `${share * 100}%` }} />
      </div>
    </div>
  );
}
