import {
  ArrowUpRightIcon,
  BanIcon,
  FileQuestionIcon,
  ScaleIcon,
  WrenchIcon,
  type LucideIcon,
} from "lucide-react";

import { Meter } from "@/components/ui/meter";
import type { CaseState, RecommendedAction } from "@/lib/api/types";
import { formatMoney, formatPercent } from "@/lib/format";
import { ACTION } from "@/lib/labels";

const ICON: Record<RecommendedAction, LucideIcon> = {
  CORRECT_AND_RESUBMIT: WrenchIcon,
  APPEAL_WITH_EVIDENCE: ScaleIcon,
  REQUEST_DOCUMENTATION: FileQuestionIcon,
  NO_ACTION: BanIcon,
  ESCALATE_TO_HUMAN: ArrowUpRightIcon,
};

/**
 * The verdict at a glance: what the workflow recommends, how sure triage was, how much
 * of the draft survived verification, and what is at stake.
 */
export function RecommendationCard({ state }: { state: CaseState }) {
  const action = state.draft?.action ?? state.triage?.action;
  if (!action) return null;
  const Icon = ICON[action];
  const verdicts = state.verification?.verdicts ?? [];
  const verified = verdicts.filter((verdict) => verdict.supported).length;
  const allVerified = verdicts.length > 0 && verified === verdicts.length;

  return (
    <section
      aria-label="Recommendation"
      className="relative overflow-hidden rounded-xl border border-primary/25 bg-card shadow-xs"
    >
      <div aria-hidden="true" className="absolute inset-y-0 left-0 w-1 bg-primary" />
      <div className="grid gap-5 p-5 pl-6 md:grid-cols-[minmax(0,1fr)_16rem]">
        <div className="flex gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <Icon className="size-6" aria-hidden="true" />
          </span>
          <div className="min-w-0 space-y-1">
            <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Recommendation</p>
            <p className="text-xl font-semibold tracking-tight">{ACTION[action].label}</p>
            <p className="text-sm text-muted-foreground">{ACTION[action].description}</p>
            <p className="pt-1 text-sm">
              <span className="text-muted-foreground">At stake: </span>
              <span className="font-semibold tabular-nums">{formatMoney(state.case_input.denial.denied_amount)}</span>
            </p>
          </div>
        </div>
        <div className="space-y-3 self-center">
          {state.triage ? (
            <Meter
              label="Triage confidence"
              value={state.triage.confidence}
              valueText={formatPercent(state.triage.confidence)}
            />
          ) : null}
          {verdicts.length > 0 ? (
            <Meter
              label="Assertions verified"
              value={verified}
              max={verdicts.length}
              valueText={`${verified} of ${verdicts.length}`}
              tone={allVerified ? "success" : "danger"}
            />
          ) : null}
        </div>
      </div>
    </section>
  );
}
