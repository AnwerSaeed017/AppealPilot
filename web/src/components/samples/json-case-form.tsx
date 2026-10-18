"use client";

import { SendIcon } from "lucide-react";
import { useActionState } from "react";

import { submitCaseJson, type FormState } from "@/app/cases/actions";
import { FormErrors } from "@/components/form-errors";
import { PendingButton } from "@/components/pending-button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Label, Textarea } from "@/components/ui/misc";

const PLACEHOLDER = `{
  "claim": { "claim_id": "...", "payer_id": "MEDICARE", "lines": [ ... ] },
  "denial": { "carc_code": "50", "denial_date": "...", ... },
  "visit_note": { "encounter_date": "...", "text": "..." },
  "supporting_documents": [],
  "prior_claims": []
}`;

export function JsonCaseForm() {
  const [state, action, pending] = useActionState<FormState, FormData>(submitCaseJson, null);
  const invalid = Boolean(state?.errors.length);
  return (
    <Card>
      <form action={action}>
        <CardContent className="space-y-3">
          <Label htmlFor="case-json">Case JSON</Label>
          <Textarea
            id="case-json"
            name="case"
            spellCheck={false}
            rows={12}
            placeholder={PLACEHOLDER}
            aria-invalid={invalid}
            aria-describedby={invalid ? "case-json-errors" : undefined}
            className="font-mono text-xs"
          />
          <div id="case-json-errors">
            <FormErrors errors={state?.errors} title="The API did not accept this case" />
          </div>
        </CardContent>
        <CardFooter className="justify-end">
          <PendingButton type="submit" pending={pending} pendingLabel="Submitting…">
            <SendIcon /> Submit case
          </PendingButton>
        </CardFooter>
      </form>
    </Card>
  );
}
