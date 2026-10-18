-- The recorded steps of a case after a given position, in order.

DROP FUNCTION IF EXISTS case_events_list(text, integer);

CREATE FUNCTION case_events_list(
    p_case_id text,
    p_after_sequence integer
) RETURNS TABLE (
    sequence integer,
    step text,
    at timestamptz,
    summary text,
    provider text,
    model text,
    input_tokens integer,
    output_tokens integer,
    latency_ms double precision,
    cached boolean,
    attempts integer
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        e.sequence, e.step::text, e.at, e.summary,
        e.provider::text, e.model::text, e.input_tokens, e.output_tokens,
        e.latency_ms, e.cached, e.attempts
    FROM case_audit_events AS e
    WHERE e.case_id = p_case_id
      AND e.sequence > p_after_sequence
    ORDER BY e.sequence;
$$;
