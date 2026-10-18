-- Create a case or bring it up to date, and record any steps of its run not yet recorded.
--
-- p_events is the case's whole audit trail as a JSON array, oldest first. A step is keyed
-- by case and position, so steps already recorded are skipped and calling this twice
-- with the same trail changes nothing. Both writes happen in the caller's transaction.

DROP FUNCTION IF EXISTS case_save(text, text, text, text, date, text, text, boolean, timestamptz, text);

CREATE FUNCTION case_save(
    p_id text,
    p_claim_id text,
    p_payer_id text,
    p_carc_code text,
    p_as_of date,
    p_status text,
    p_action text,
    p_verified boolean,
    p_now timestamptz,
    p_events text
) RETURNS void
LANGUAGE sql
AS $$
    INSERT INTO cases (
        id, claim_id, payer_id, carc_code, as_of,
        status, action, verified, created_at, updated_at
    )
    VALUES (
        p_id, p_claim_id, p_payer_id, p_carc_code, p_as_of,
        p_status, p_action, p_verified, p_now, p_now
    )
    ON CONFLICT (id) DO UPDATE
        SET status = EXCLUDED.status,
            action = EXCLUDED.action,
            verified = EXCLUDED.verified,
            updated_at = EXCLUDED.updated_at;

    INSERT INTO case_audit_events (
        case_id, sequence, step, at, summary,
        provider, model, input_tokens, output_tokens, latency_ms, cached, attempts
    )
    SELECT
        p_id,
        event.position::integer,
        event.value ->> 'step',
        (event.value ->> 'at')::timestamptz,
        event.value ->> 'summary',
        event.value -> 'llm_call' ->> 'provider',
        event.value -> 'llm_call' ->> 'model',
        (event.value -> 'llm_call' ->> 'input_tokens')::integer,
        (event.value -> 'llm_call' ->> 'output_tokens')::integer,
        (event.value -> 'llm_call' ->> 'latency_ms')::double precision,
        (event.value -> 'llm_call' ->> 'cached')::boolean,
        (event.value -> 'llm_call' ->> 'attempts')::integer
    FROM jsonb_array_elements(p_events::jsonb) WITH ORDINALITY AS event(value, position)
    ON CONFLICT (case_id, sequence) DO NOTHING;
$$;
