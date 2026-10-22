import { ShieldAlertIcon, ShieldCheckIcon, TargetIcon, UserRoundSearchIcon } from "lucide-react";
import type { ComponentType } from "react";

import { Badge } from "@/components/ui/badge";
import { Meter } from "@/components/ui/meter";
import type { EvaluationRun, TallyPair } from "@/lib/api/types";
import { better, formatTally, share, type Better } from "@/lib/evaluation";

type Headline = {
  key: string;
  title: string;
  question: string;
  pair: TallyPair;
  direction: "higher" | "lower";
  icon: ComponentType<{ className?: string }>;
};

function headlines(run: EvaluationRun): Headline[] {
  return [
    {
      key: "correct",
      title: "Right action",
      question: "Chose the labelled action, or an alternative the label accepts.",
      pair: run.correct,
      direction: "higher",
      icon: TargetIcon,
    },
    {
      key: "unsafe",
      title: "Unsafe actions",
      question: "A correction or appeal the label does not support. Fewer is better.",
      pair: run.unsafe,
      direction: "lower",
      icon: ShieldAlertIcon,
    },
    {
      key: "escalations",
      title: "Escalations caught",
      question: "Cases that need a person, sent to a person.",
      pair: run.escalations,
      direction: "higher",
      icon: UserRoundSearchIcon,
    },
    {
      key: "citations",
      title: "Quotes found in their source",
      question: "Every quoted word checked by code against the cited clause or document.",
      pair: run.citations_in_source,
      direction: "higher",
      icon: ShieldCheckIcon,
    },
  ];
}

const VERDICT: Record<Better, { text: string; tone: "success" | "danger" | "neutral" }> = {
  workflow: { text: "Workflow ahead", tone: "success" },
  baseline: { text: "Baseline ahead", tone: "danger" },
  even: { text: "Even", tone: "neutral" },
};

/** The four numbers a reviewer asks about first, each with both systems side by side. */
export function HeadlineComparison({ run }: { run: EvaluationRun }) {
  return (
    <section aria-label="Headline results" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {headlines(run).map((item) => {
        const Icon = item.icon;
        const verdict = VERDICT[better(item.pair, item.direction)];
        const lower = item.direction === "lower";
        return (
          <div key={item.key} className="flex flex-col gap-4 rounded-xl border bg-card p-5 shadow-xs">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="grid size-8 place-items-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="size-4" aria-hidden="true" />
                </span>
                <h3 className="text-sm font-semibold">{item.title}</h3>
              </div>
              <Badge tone={verdict.tone}>{verdict.text}</Badge>
            </div>
            <p className="text-xs text-muted-foreground">{item.question}</p>
            <div className="mt-auto space-y-3">
              <Meter
                label="Workflow"
                value={share(item.pair.workflow)}
                valueText={formatTally(item.pair.workflow)}
                tone={lower ? "danger" : "success"}
              />
              <Meter
                label="Single-prompt baseline"
                value={share(item.pair.baseline)}
                valueText={formatTally(item.pair.baseline)}
                tone={lower ? "danger" : "primary"}
              />
            </div>
          </div>
        );
      })}
    </section>
  );
}
