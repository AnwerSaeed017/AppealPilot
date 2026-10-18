"use client";

import { CheckIcon, PencilLineIcon, ShieldAlertIcon, UserCheckIcon, XIcon } from "lucide-react";
import { useActionState, useId, useState } from "react";

import { decide, type FormState } from "@/app/cases/actions";
import { FormErrors } from "@/components/form-errors";
import { PendingButton } from "@/components/pending-button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Label, Textarea } from "@/components/ui/misc";
import type { HumanDecisionKind } from "@/lib/api/types";

const CHOICES: { kind: HumanDecisionKind; label: string; icon: typeof CheckIcon }[] = [
  { kind: "APPROVE", label: "Approve", icon: CheckIcon },
  { kind: "EDIT_AND_APPROVE", label: "Edit and approve", icon: PencilLineIcon },
  { kind: "REJECT", label: "Reject", icon: XIcon },
];

const SUBMIT_LABEL: Record<HumanDecisionKind, string> = {
  APPROVE: "Approve draft",
  EDIT_AND_APPROVE: "Approve with my edits",
  REJECT: "Reject draft",
};

/**
 * The approval gate. Nothing leaves the practice until a reviewer decides here, and an
 * unverified draft says so before it can be approved.
 */
export function DecisionPanel({
  caseId,
  summary,
  unverifiedCount,
}: {
  caseId: string;
  summary: string;
  unverifiedCount: number;
}) {
  const [kind, setKind] = useState<HumanDecisionKind>("APPROVE");
  const [state, action, pending] = useActionState<FormState, FormData>(decide.bind(null, caseId), null);
  const ids = { group: useId(), edit: useId(), reason: useId() };

  return (
    <Card className="overflow-hidden border-primary/30 shadow-md">
      <div aria-hidden="true" className="h-1 bg-gradient-to-r from-primary to-cta/80" />
      <form action={action}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <span className="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary" aria-hidden="true">
              <UserCheckIcon className="size-4" />
            </span>
            Your decision
          </CardTitle>
          <CardDescription>
            The draft goes nowhere until you approve it. Check each assertion&apos;s sources first.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {unverifiedCount > 0 ? (
            <Alert tone="warning">
              <ShieldAlertIcon />
              <AlertTitle>
                {unverifiedCount === 1 ? "1 assertion failed" : `${unverifiedCount} assertions failed`} verification
              </AlertTitle>
              <AlertDescription>
                The failing assertions are marked in the draft. Edit them out or reject the draft rather
                than approve it as written.
              </AlertDescription>
            </Alert>
          ) : null}

          <fieldset className="space-y-2">
            <legend id={ids.group} className="sr-only">
              Decision
            </legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {CHOICES.map((choice) => {
                const Icon = choice.icon;
                return (
                  <label
                    key={choice.kind}
                    className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border bg-card px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:checked]:text-foreground has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring"
                  >
                    <input
                      type="radio"
                      name="kind"
                      value={choice.kind}
                      checked={kind === choice.kind}
                      onChange={() => setKind(choice.kind)}
                      className="sr-only"
                    />
                    <Icon className="size-4" aria-hidden="true" />
                    {choice.label}
                  </label>
                );
              })}
            </div>
          </fieldset>

          {kind === "EDIT_AND_APPROVE" ? (
            <div className="space-y-2">
              <Label htmlFor={ids.edit}>Your wording of the summary</Label>
              <Textarea id={ids.edit} name="edited_summary" defaultValue={summary} rows={8} required />
            </div>
          ) : null}
          {kind === "REJECT" ? (
            <div className="space-y-2">
              <Label htmlFor={ids.reason}>Why the draft is rejected</Label>
              <Textarea
                id={ids.reason}
                name="reason"
                rows={4}
                required
                placeholder="For example: the note does not document a separate evaluation."
              />
            </div>
          ) : null}

          <FormErrors errors={state?.errors} title="The decision was not recorded" />
        </CardContent>
        <CardFooter className="justify-end">
          <PendingButton
            type="submit"
            pending={pending}
            pendingLabel="Recording…"
            // Coral invites the click; an unverified draft does not get that invitation.
            variant={kind === "REJECT" ? "destructive" : unverifiedCount > 0 ? "default" : "cta"}
          >
            {SUBMIT_LABEL[kind]}
          </PendingButton>
        </CardFooter>
      </form>
    </Card>
  );
}
