"""Fixed values of the model clients."""

import re

# How much of a provider's error response is kept in the error message.
ERROR_BODY_LIMIT = 300

# The error code Groq returns when the model's reply in JSON mode is not valid JSON.
GROQ_INVALID_JSON_CODE = "json_validate_failed"

# How Groq states a request that is over its per-call token limit: "Limit 8000, Requested
# 9258". The limit counts the prompt plus the reply allowance.
GROQ_REQUEST_TOO_LARGE = re.compile(r"Limit (\d+), Requested (\d+)")

# A reply allowance is never shrunk below this to fit a provider's limit; a smaller one
# could not hold a useful answer.
MIN_REPLY_ALLOWANCE_TOKENS = 1000

# Tokens taken off on top of the reported excess when shrinking a reply allowance.
REPLY_ALLOWANCE_MARGIN_TOKENS = 100

# Characters per token, for estimating a prompt's size before it is sent. Measured at
# 3.96 on a writer prompt for gpt-oss-120b; a lower figure overestimates the prompt, which
# errs towards a smaller reply allowance rather than a request that is refused.
ESTIMATED_CHARACTERS_PER_TOKEN = 3.7

# Tokens a chat request adds around the message text (roles, separators).
MESSAGE_OVERHEAD_TOKENS = 150

# How many recent requests the mock client remembers.
MOCK_MAX_RECORDED_CALLS = 1000

# A disk cache key is a SHA-256 hex digest; nothing else may become a file name.
CACHE_KEY_PATTERN = re.compile(r"^[0-9a-f]{64}$")
