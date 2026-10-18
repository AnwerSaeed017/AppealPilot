"""Fixed values of the case workflow: step names, model tasks and limits."""

from app.schemas.llm import ReasoningEffort

# Step names. They are the graph's node names and the `step` of each audit event.
STEP_RULES = "rules"
STEP_RETRIEVAL = "retrieval"
STEP_INTAKE = "intake"
STEP_RECORD_CHECKS = "record_checks"
STEP_DOCUMENT_RETRIEVAL = "document_retrieval"
STEP_TRIAGE = "triage"
STEP_WRITER = "writer"
STEP_VERIFIER = "verifier"
# The model task inside the verifier step. It runs on the judge model.
TASK_JUDGE = "judge"
STEP_REVIEW = "review"
STEP_APPROVAL = "approval"

# How many times the writer may be sent back after a failed verification.
MAX_WRITER_REVISIONS = 2

# The most model calls one case may use before it stops rewriting and goes to a person.
# Without it the worst case is 15: three attempts each for intake and triage, and three
# for each of three drafts, plus a judge call per draft.
MAX_MODEL_CALLS_PER_CASE = 10

# How many times a model is asked for output that parses, the first try included.
MAX_OUTPUT_ATTEMPTS = 3

# Reasoning effort per model task, where it differs from the provider's default. The
# writer's job is to arrange and quote evidence it is given, not to decide; at the
# default effort gpt-oss-120b spent 2,027 of 2,209 reply tokens reasoning and its draft
# was cut off, while at low effort it used 1,035 and wrote a complete, cited draft
# (measured 2026-10-18). Triage, which decides, keeps the default.
WRITER_REASONING_EFFORT: ReasoningEffort = "low"

# Output token limits per model task. Reasoning models count their hidden reasoning
# against this limit, so the long outputs (the facts, the draft) need room beyond the
# visible JSON; a reply cut off at the limit is re-asked and tends to come back shorter.
MAX_OUTPUT_TOKENS: dict[str, int] = {
    STEP_INTAKE: 4000,
    STEP_TRIAGE: 800,
    STEP_WRITER: 4000,
    TASK_JUDGE: 1200,
}

# How documents are shown to a model: delimited, with every line numbered.
DOCUMENT_OPEN = '<document id="{document_id}" kind="{kind}">'
DOCUMENT_LINE = "{number}| {text}"
DOCUMENT_CLOSE = "</document>"

# Shown in place of an empty list.
NOTHING = "(none)"
