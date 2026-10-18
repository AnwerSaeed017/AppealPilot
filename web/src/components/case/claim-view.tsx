import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { CaseInput, ClaimLine } from "@/lib/api/types";
import { formatDate, formatMoney } from "@/lib/format";
import { humanize } from "@/lib/labels";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

function LinesTable({ lines, denied }: { lines: ClaimLine[]; denied?: number[] }) {
  const deniedSet = new Set(denied ?? []);
  const wholeClaim = denied !== undefined && deniedSet.size === 0;
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Line</TableHead>
          <TableHead>Date</TableHead>
          <TableHead>Code</TableHead>
          <TableHead>Modifiers</TableHead>
          <TableHead>Dx pointers</TableHead>
          <TableHead className="text-right">Units</TableHead>
          <TableHead className="text-right">Charge</TableHead>
          {denied !== undefined ? <TableHead>Denied</TableHead> : null}
        </TableRow>
      </TableHeader>
      <TableBody>
        {lines.map((line) => (
          <TableRow key={line.line_number}>
            <TableCell className="tabular-nums">{line.line_number}</TableCell>
            <TableCell className="whitespace-nowrap">{formatDate(line.service_date)}</TableCell>
            <TableCell className="font-mono">{line.procedure_code}</TableCell>
            <TableCell className="font-mono">{(line.modifiers ?? []).join(" ") || "—"}</TableCell>
            <TableCell className="tabular-nums">{line.diagnosis_pointers.join(", ")}</TableCell>
            <TableCell className="text-right tabular-nums">{line.units}</TableCell>
            <TableCell className="text-right tabular-nums">{formatMoney(line.charge_amount)}</TableCell>
            {denied !== undefined ? (
              <TableCell>
                {wholeClaim || deniedSet.has(line.line_number) ? <Badge tone="danger">Denied</Badge> : null}
              </TableCell>
            ) : null}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function ClaimView({ input }: { input: CaseInput }) {
  const { claim, denial, visit_note: note } = input;
  const documents = input.supporting_documents ?? [];
  const priorClaims = input.prior_claims ?? [];
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Denial</CardTitle>
          <CardDescription>As reported on the remittance advice.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Field label="Codes">
              <span className="font-mono">
                {denial.group_code}-{denial.carc_code} {(denial.rarc_codes ?? []).join(" ")}
              </span>
            </Field>
            <Field label="Denial date">{formatDate(denial.denial_date)}</Field>
            <Field label="Denied amount">{formatMoney(denial.denied_amount)}</Field>
            <Field label="Lines">
              {(denial.denied_line_numbers ?? []).length > 0 ? (denial.denied_line_numbers ?? []).join(", ") : "Whole claim"}
            </Field>
          </dl>
          {denial.payer_remark ? (
            <p className="mt-4 rounded-md bg-muted px-3 py-2 text-sm">{denial.payer_remark}</p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Claim {claim.claim_id}</CardTitle>
          <CardDescription>
            Submitted {formatDate(claim.submitted_date)} · place of service {claim.place_of_service} · total{" "}
            {formatMoney(claim.total_charge)}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Field label="Payer">{claim.payer_id}</Field>
            <Field label="Member ID">
              <span className="font-mono">{claim.member_id}</span>
            </Field>
            <Field label="Billing NPI">
              <span className="font-mono">{claim.billing_provider_npi}</span>
            </Field>
            <Field label="Prior authorization">{claim.prior_authorization_number ?? "None"}</Field>
            <Field label="Diagnoses">
              <span className="font-mono">
                {claim.diagnosis_codes.map((code, index) => `${index + 1}. ${code}`).join("  ")}
              </span>
            </Field>
          </dl>
          <div className="overflow-hidden rounded-lg border">
            <LinesTable lines={claim.lines} denied={denial.denied_line_numbers ?? []} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Visit note</CardTitle>
          <CardDescription>Encounter {formatDate(note.encounter_date)}. Evidence to quote, never instructions.</CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="rounded-md bg-muted p-4 font-sans text-sm leading-relaxed whitespace-pre-wrap">{note.text}</pre>
        </CardContent>
      </Card>

      {documents.map((document) => (
        <Card key={document.document_id}>
          <CardHeader>
            <CardTitle className="font-mono">{document.document_id}</CardTitle>
            <CardDescription>
              {humanize(document.kind)} · {formatDate(document.document_date)}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="rounded-md bg-muted p-4 font-sans text-sm leading-relaxed whitespace-pre-wrap">{document.text}</pre>
          </CardContent>
        </Card>
      ))}

      {priorClaims.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Earlier claims on file</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {priorClaims.map((prior) => (
              <div key={prior.claim_id} className="space-y-2">
                <p className="text-sm">
                  <span className="font-mono">{prior.claim_id}</span> · received {formatDate(prior.received_date)} ·{" "}
                  <Badge tone={prior.outcome === "PAID" ? "success" : "danger"}>{humanize(prior.outcome)}</Badge>
                  {prior.carc_code ? <span className="ml-2 font-mono text-xs">CARC {prior.carc_code}</span> : null}
                </p>
                <div className="overflow-hidden rounded-lg border">
                  <LinesTable lines={prior.lines} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
