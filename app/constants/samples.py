"""Fixed values for the sample cases."""

import re

# One JSON file per sample case in the samples folder.
SAMPLE_FILE_GLOB = "*.json"

# An ISO date (2026-06-16) anywhere in a value, including inside free text.
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
