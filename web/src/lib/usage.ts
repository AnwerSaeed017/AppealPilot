import type { AuditEvent } from "./api/types";

export type Usage = {
  /** Steps that called a model. */
  modelSteps: number;
  /** Model calls, counting each re-ask after an invalid reply. */
  attempts: number;
  inputTokens: number;
  outputTokens: number;
  latencyMs: number;
};

/** What the model calls of a run cost, summed from its audit trail. */
export function usageOf(audit: readonly AuditEvent[]): Usage {
  const calls = audit.flatMap((event) => (event.llm_call ? [event.llm_call] : []));
  return {
    modelSteps: calls.length,
    attempts: calls.reduce((total, call) => total + call.attempts, 0),
    inputTokens: calls.reduce((total, call) => total + call.input_tokens, 0),
    outputTokens: calls.reduce((total, call) => total + call.output_tokens, 0),
    latencyMs: calls.reduce((total, call) => total + call.latency_ms, 0),
  };
}
