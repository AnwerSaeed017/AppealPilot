"use client";

import { PlayIcon } from "lucide-react";
import { useActionState } from "react";

import { runSample, type FormState } from "@/app/cases/actions";
import { FormErrors } from "@/components/form-errors";
import { PendingButton } from "@/components/pending-button";

export function RunSampleButton({ sampleId, title }: { sampleId: string; title: string }) {
  const [state, action, pending] = useActionState<FormState>(runSample.bind(null, sampleId), null);
  return (
    <form action={action} className="flex w-full flex-col gap-3">
      <FormErrors errors={state?.errors} />
      <PendingButton
        type="submit"
        variant="cta"
        className="w-full"
        pending={pending}
        pendingLabel="Starting…"
        aria-label={`Run sample: ${title}`}
      >
        <PlayIcon /> Run this case
      </PendingButton>
    </form>
  );
}
