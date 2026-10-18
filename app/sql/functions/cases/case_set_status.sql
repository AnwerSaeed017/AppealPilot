-- Change a case's status. Returns false when there is no such case.

DROP FUNCTION IF EXISTS case_set_status(text, text, timestamptz);

CREATE FUNCTION case_set_status(
    p_id text,
    p_status text,
    p_now timestamptz
) RETURNS boolean
LANGUAGE sql
AS $$
    WITH changed AS (
        UPDATE cases
        SET status = p_status,
            updated_at = p_now
        WHERE id = p_id
        RETURNING 1
    )
    SELECT EXISTS (SELECT 1 FROM changed);
$$;
