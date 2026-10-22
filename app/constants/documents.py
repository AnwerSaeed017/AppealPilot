"""Groups of supporting document kinds that rules act on."""

from app.schemas.supporting_document import DocumentKind

# Documents that add to the clinical record of a service already given. One written
# after the denial may add findings that were not recorded at the time.
CLINICAL_LATE_ENTRY_KINDS: frozenset[DocumentKind] = frozenset({DocumentKind.ADDENDUM})
