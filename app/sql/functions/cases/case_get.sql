-- One case, or no rows when there is no such case.

DROP FUNCTION IF EXISTS case_get(text);

CREATE FUNCTION case_get(
    p_id text
) RETURNS TABLE (
    id text,
    claim_id text,
    payer_id text,
    carc_code text,
    as_of date,
    status text,
    action text,
    verified boolean,
    created_at timestamptz,
    updated_at timestamptz
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        c.id::text, c.claim_id::text, c.payer_id::text, c.carc_code::text, c.as_of,
        c.status::text, c.action::text, c.verified, c.created_at, c.updated_at
    FROM cases AS c
    WHERE c.id = p_id;
$$;
