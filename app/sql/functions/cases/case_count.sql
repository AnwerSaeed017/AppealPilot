-- How many cases there are. p_status of NULL means every status.

DROP FUNCTION IF EXISTS case_count(text);

CREATE FUNCTION case_count(
    p_status text
) RETURNS bigint
LANGUAGE sql
STABLE
AS $$
    SELECT count(*)
    FROM cases AS c
    WHERE p_status IS NULL OR c.status = p_status;
$$;
