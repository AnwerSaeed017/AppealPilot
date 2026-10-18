import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { AuditEvent } from "@/lib/api/types";
import { formatCount, formatDateTime, formatDuration } from "@/lib/format";
import { stepLabel } from "@/lib/labels";

export function AuditView({ audit }: { audit: readonly AuditEvent[] }) {
  if (audit.length === 0) {
    return <p className="py-10 text-center text-sm text-muted-foreground">No steps recorded yet.</p>;
  }
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>#</TableHead>
            <TableHead>Step</TableHead>
            <TableHead>What happened</TableHead>
            <TableHead>Model</TableHead>
            <TableHead className="text-right">Tokens in / out</TableHead>
            <TableHead className="text-right">Time</TableHead>
            <TableHead className="text-right">At</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {audit.map((event, index) => (
            <TableRow key={index} className="align-top">
              <TableCell className="text-muted-foreground tabular-nums">{index + 1}</TableCell>
              <TableCell className="font-medium whitespace-nowrap">{stepLabel(event.step)}</TableCell>
              <TableCell className="max-w-md text-sm">{event.summary}</TableCell>
              <TableCell className="text-xs whitespace-nowrap">
                {event.llm_call ? (
                  <div className="space-y-1">
                    <div className="font-mono">{event.llm_call.model}</div>
                    <div className="flex gap-1">
                      {event.llm_call.cached ? <Badge>cached</Badge> : null}
                      {event.llm_call.attempts > 1 ? (
                        <Badge tone="warning" title="The model's reply was re-asked after it failed validation.">
                          {event.llm_call.attempts} attempts
                        </Badge>
                      ) : null}
                    </div>
                  </div>
                ) : (
                  <span className="text-muted-foreground">code only</span>
                )}
              </TableCell>
              <TableCell className="text-right text-xs whitespace-nowrap tabular-nums">
                {event.llm_call
                  ? `${formatCount(event.llm_call.input_tokens)} / ${formatCount(event.llm_call.output_tokens)}`
                  : "—"}
              </TableCell>
              <TableCell className="text-right text-xs whitespace-nowrap tabular-nums">
                {event.llm_call ? formatDuration(event.llm_call.latency_ms) : "—"}
              </TableCell>
              <TableCell className="text-right text-xs whitespace-nowrap text-muted-foreground tabular-nums">
                {formatDateTime(event.at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
