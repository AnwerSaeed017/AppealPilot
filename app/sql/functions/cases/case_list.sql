-- One page of cases, newest first. p_status of NULL means every status.

DROP FUNCTION IF EXISTS case_list(text, integer, integer);

CREATE FUNCTION case_list(
    p_status text,
    p_limit integer,
    p_offset integer
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
    WHERE p_status IS NULL OR c.status = p_status
    ORDER BY c.created_at DESC, c.id
    LIMIT p_limit
    OFFSET p_offset;
$$;
