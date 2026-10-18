"""Procedure code modifiers that the rules look for."""

# A significant, separately identifiable evaluation on the day of a procedure.
SEPARATE_EVALUATION = "25"

# Right, left and bilateral.
SIDE_MODIFIERS: frozenset[str] = frozenset({"RT", "LT", "50"})

# A procedure repeated on the same day, by the same or by another clinician.
REPEAT_MODIFIERS: frozenset[str] = frozenset({"76", "77"})
