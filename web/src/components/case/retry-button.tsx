"use client";

import { RotateCcwIcon } from "lucide-react";
import { useActionState } from "react";

import { retry, type FormState } from "@/app/cases/actions";
import { FormErrors } from "@/components/form-errors";
import { PendingButton } from "@/components/pending-button";

export function RetryButton({ caseId }: { caseId: string }) {
  const [state, action, pending] = useActionState<FormState>(retry.bind(null, caseId), null);
  return (
    <form action={action} className="space-y-3">
      <PendingButton type="submit" variant="outline" pending={pending} pendingLabel="Retrying…">
        <RotateCcwIcon /> Retry from the last step
      </PendingButton>
      <FormErrors errors={state?.errors} title="The case was not restarted" />
    </form>
  );
}
