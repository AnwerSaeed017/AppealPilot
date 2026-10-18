"""Write the API responses the web app's tests run against.

    uv run python -m scripts.build_web_fixtures

Every fixture is built from the API's own schemas, the real sample cases and the real
policy clauses, then serialised exactly as the API would send it. If a schema changes in
a way the web app has not caught up with, building the fixtures or the web tests fail.

The cases show each state a reviewer meets: running, waiting with a verified draft,
waiting with a draft that failed verification, approved, rejected and failed.
"""

import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.agents.states.case_state import CaseState
from app.repositories.file_policy_repository import FilePolicyRepository
from app.schemas.audit_event import AuditEvent, LlmCallRecord
from app.schemas.case_clause import CaseClause, ClauseOrigin
from app.schemas.case_input import CaseInput
from app.schemas.case_status import CaseStatus
from app.schemas.case_summary import CaseEvent, CaseSnapshot, CaseSummary, CaseView
from app.schemas.draft import Assertion, Citation, CitationKind, Draft
from app.schemas.finding import Finding, FindingCode
from app.schemas.human_decision import HumanDecision, HumanDecisionKind
from app.schemas.note_fact import NoteFact
from app.schemas.recommended_action import RecommendedAction
from app.schemas.sample_case import SampleCase
from app.schemas.triage_decision import TriageDecision
from app.schemas.verification_report import AssertionVerdict, VerificationReport

TARGET = Path("web/tests/fixtures")
SAMPLES = Path("seeders/samples")
POLICIES = Path("seeders/policies")
AS_OF = date(2026, 10, 16)
STARTED = datetime(2026, 10, 16, 14, 2, 11, tzinfo=UTC)


def sample(sample_id: str) -> SampleCase:
    return SampleCase.model_validate_json((SAMPLES / f"{sample_id}.json").read_text("utf-8"))


def call(
    model: str, tokens_in: int, tokens_out: int, ms: float, attempts: int = 1
) -> LlmCallRecord:
    provider = "gemini" if model.startswith("gemini") else "groq"
    return LlmCallRecord(
        provider=provider,
        model=model,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
        latency_ms=ms,
        cached=False,
        attempts=attempts,
    )


AGENT = "openai/gpt-oss-120b"
JUDGE = "gemini-3.1-flash-lite"


def event(seconds: int, step: str, summary: str, llm: LlmCallRecord | None = None) -> AuditEvent:
    return AuditEvent(
        step=step, at=STARTED + timedelta(seconds=seconds), summary=summary, llm_call=llm
    )


async def clauses(*ranked: tuple[str, ClauseOrigin]) -> tuple[CaseClause, ...]:
    repository = FilePolicyRepository(POLICIES)
    selected = []
    for rank, (clause_id, origin) in enumerate(ranked, start=1):
        clause = await repository.get_clause(clause_id)
        assert clause is not None, clause_id
        selected.append(CaseClause(clause=clause, rank=rank, origin=origin))
    return tuple(selected)


def quote_of(text: str, words: str) -> str:
    assert words in text, words
    return words


async def modifier_25_state() -> CaseState:
    case = sample("visit-without-modifier-25")
    note = case.input.visit_note.text
    mod = await clauses(
        ("MEDICARE-MOD-1.1", ClauseOrigin.RULE),
        ("MEDICARE-MOD-1.2", ClauseOrigin.SEARCH),
        ("MEDICARE-APL-2.1", ClauseOrigin.SEARCH),
        ("MEDICARE-APL-2.2", ClauseOrigin.NEIGHBOUR),
    )
    mod_text = mod[0].clause.text
    minor_text = mod[1].clause.text
    reopen_text = mod[2].clause.text
    return CaseState(
        case_id="case-modifier-25",
        as_of=AS_OF,
        case_input=case.input,
        status=CaseStatus.AWAITING_APPROVAL,
        findings=(
            Finding(
                code=FindingCode.VISIT_WITHOUT_MODIFIER_25,
                message=(
                    "A visit is billed on the same day as a procedure without modifier 25. "
                    "Whether the record supports the modifier needs review."
                ),
                clause_ids=("MEDICARE-MOD-1.1",),
                line_numbers=(1,),
            ),
        ),
        clauses=mod,
        note_facts=(
            NoteFact(
                statement="HbA1c rose to 8.4% and empagliflozin was started.",
                document_id="NOTE",
                line_number=4,
                quote=quote_of(note, "HbA1c 8.4% today, up from 7.6% in 2026-04."),
            ),
            NoteFact(
                statement="Blood pressure was above goal and amlodipine was added.",
                document_id="NOTE",
                line_number=11,
                quote=quote_of(
                    note, "Essential hypertension, not at goal. Add amlodipine 5 mg daily."
                ),
            ),
            NoteFact(
                statement="A corticosteroid injection was given into the right knee.",
                document_id="NOTE",
                line_number=13,
                quote=quote_of(note, "Procedure: right knee intra-articular injection."),
            ),
        ),
        triage=TriageDecision(
            action=RecommendedAction.CORRECT_AND_RESUBMIT,
            confidence=0.86,
            reasons=(
                "The visit line lacks modifier 25, which Medicare requires for a separate "
                "evaluation on the day of a procedure.",
                "The note documents diabetes and hypertension management beyond the "
                "injection, so the modifier is supported.",
                "A missing modifier is a clerical omission, corrected by reopening.",
            ),
        ),
        draft=Draft(
            action=RecommendedAction.CORRECT_AND_RESUBMIT,
            summary=(
                "Request a reopening of the initial determination to add modifier 25 to "
                "line 1 (99214). The visit managed uncontrolled type 2 diabetes and "
                "hypertension, with medication changes, separately from the right knee "
                "injection billed on line 2."
            ),
            correction="Line 1: 99214 → 99214-25. No other line changes.",
            assertions=(
                Assertion(
                    text=(
                        "Medicare pays for a same-day visit when it is a significant, "
                        "separately identifiable service and modifier 25 is on the visit code."
                    ),
                    citations=(
                        Citation(
                            kind=CitationKind.CLAUSE,
                            source_id="MEDICARE-MOD-1.1",
                            quote=quote_of(
                                mod_text, "Modifier -25 is added to the E/M code on the claim."
                            ),
                        ),
                    ),
                ),
                Assertion(
                    text="The visit adjusted diabetes treatment after a raised HbA1c.",
                    citations=(
                        Citation(
                            kind=CitationKind.DOCUMENT,
                            source_id="NOTE",
                            quote=quote_of(note, "Start empagliflozin 10 mg daily"),
                        ),
                    ),
                ),
                Assertion(
                    text="The visit adjusted blood pressure treatment.",
                    citations=(
                        Citation(
                            kind=CitationKind.DOCUMENT,
                            source_id="NOTE",
                            quote=quote_of(note, "Add amlodipine 5 mg daily."),
                        ),
                    ),
                ),
                Assertion(
                    text=(
                        "A visit on the day of a minor procedure is separately payable when it "
                        "is separately identifiable."
                    ),
                    citations=(
                        Citation(
                            kind=CitationKind.CLAUSE,
                            source_id="MEDICARE-MOD-1.2",
                            quote=quote_of(
                                minor_text,
                                (
                                    "unless a significant, separately identifiable service is also "
                                    "performed"
                                ),
                            ),
                        ),
                    ),
                ),
                Assertion(
                    text=(
                        "A missing modifier is corrected through a reopening, not a "
                        "redetermination."
                    ),
                    citations=(
                        Citation(
                            kind=CitationKind.CLAUSE,
                            source_id="MEDICARE-APL-2.1",
                            quote=quote_of(
                                reopen_text,
                                (
                                    "a contractor must process clerical "
                                    "errors (which includes minor "
                                    "errors and omissions) as reopenings"
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            missing_evidence=(),
        ),
        verification=VerificationReport(
            verdicts=tuple(
                AssertionVerdict(assertion_index=index, supported=True) for index in range(5)
            )
        ),
        writer_attempts=1,
        audit=(
            event(0, "rules", "Rule findings: VISIT_WITHOUT_MODIFIER_25."),
            event(
                1,
                "retrieval",
                (
                    "Selected 4 clauses: MEDICARE-MOD-1.1, MEDICARE-MOD-1.2, MEDICARE-APL-2.1, "
                    "MEDICARE-APL-2.2."
                ),
            ),
            event(
                9, "intake", "Extracted 3 facts from the record.", call(AGENT, 2794, 612, 7380.0)
            ),
            event(9, "record_checks", "No contradiction in the record that code can see."),
            event(9, "document_retrieval", "No supporting documents; nothing added."),
            event(
                14,
                "triage",
                "Action: CORRECT_AND_RESUBMIT (confidence 0.86).",
                call(AGENT, 3311, 402, 4912.0),
            ),
            event(
                26,
                "writer",
                "Draft 1 with 5 assertions.",
                call(AGENT, 4120, 1180, 11204.0, attempts=2),
            ),
            event(31, "verifier", "All 5 assertions verified.", call(JUDGE, 2210, 310, 4420.0)),
            event(31, "review", "Sent for approval with a verified draft."),
        ),
    )


async def bone_density_state(passed: bool) -> CaseState:
    case = sample("bone-density-repeat-on-steroids")
    documents = {
        document.document_id: document.text for document in case.input.supporting_documents
    }
    note = case.input.visit_note.text
    cov = await clauses(
        ("MEDICARE-COV-1.2", ClauseOrigin.RULE),
        ("MEDICARE-COV-1.3", ClauseOrigin.SEARCH),
        ("MEDICARE-COV-2.1", ClauseOrigin.SEARCH),
        ("MEDICARE-COV-1.1", ClauseOrigin.SEARCH),
        ("MEDICARE-APL-1.1", ClauseOrigin.DOCUMENT),
    )
    frequency = cov[0].clause.text
    beneficiaries = cov[1].clause.text
    appeal = cov[4].clause.text
    unsupported_quote = "covered every 12 months for patients on steroids"
    return CaseState(
        case_id="case-bone-density" if passed else "case-bone-density-unverified",
        as_of=AS_OF,
        case_input=case.input,
        status=CaseStatus.AWAITING_APPROVAL,
        findings=(
            Finding(
                code=FindingCode.PROCEDURE_CONDITIONS_CLAUSE,
                message=(
                    "The conditions for procedure code 77080 on line 1 are set by clause "
                    "MEDICARE-COV-1.2."
                ),
                clause_ids=("MEDICARE-COV-1.2",),
                line_numbers=(1,),
            ),
            Finding(
                code=FindingCode.CLINICAL_SUPPORT_NEEDS_REVIEW,
                message=(
                    "The denial turns on whether the service was medically necessary. No rule "
                    "decides that; it needs evidence from the record."
                ),
                line_numbers=(1,),
            ),
        ),
        clauses=cov,
        note_facts=(
            NoteFact(
                statement="The patient has taken prednisone daily since 2025-12-02, now 10 mg.",
                document_id="NOTE",
                line_number=4,
                quote=quote_of(note, "she remains on 10 mg daily today"),
            ),
            NoteFact(
                statement="The pharmacy record shows continuous prednisone fills without gaps.",
                document_id="RX-HISTORY",
                line_number=9,
                quote=quote_of(documents["RX-HISTORY"], "No gaps in supply between fills."),
            ),
            NoteFact(
                statement="Lumbar spine density fell 5.9% since the last scan.",
                document_id="DXA-REPORT",
                line_number=5,
                quote=quote_of(
                    documents["DXA-REPORT"], "lumbar spine bone mineral density down 5.9%"
                ),
            ),
        ),
        triage=TriageDecision(
            action=RecommendedAction.APPEAL_WITH_EVIDENCE,
            confidence=0.81,
            reasons=(
                (
                    "The scan was within 23 months of the "
                    "last one, which the general frequency rule "
                    "does not cover."
                ),
                (
                    "Medicare allows more frequent scans "
                    "to monitor long-term glucocorticoid therapy "
                    "of more than 3 months."
                ),
                (
                    "The note and pharmacy record document more than seven months of prednisone at "
                    "10 mg or more."
                ),
            ),
        ),
        draft=Draft(
            action=RecommendedAction.APPEAL_WITH_EVIDENCE,
            summary=(
                "File a redetermination request within 120 days of the notice. The repeat DXA "
                "falls under the frequency exception for monitoring long-term glucocorticoid "
                "therapy: the patient has taken prednisone at 10 mg or more daily since "
                "2025-12-02, and the scan shows significant bone loss."
            ),
            assertions=(
                Assertion(
                    text=(
                        "Medicare may cover a bone density scan more often than every 23 months "
                        "when medically necessary, including to monitor long-term steroid "
                        "therapy."
                    ),
                    citations=(
                        Citation(
                            kind=CitationKind.CLAUSE,
                            source_id="MEDICARE-COV-1.2",
                            quote=quote_of(
                                frequency,
                                (
                                    "Monitoring beneficiaries on "
                                    "long-term glucocorticoid (steroid) "
                                    "therapy of more than 3 months."
                                ),
                            ),
                        ),
                    ),
                ),
                Assertion(
                    text=(
                        "The patient qualifies as an individual on glucocorticoid therapy of 5 "
                        "mg of prednisone or more a day for more than 3 months."
                    ),
                    citations=(
                        Citation(
                            kind=CitationKind.CLAUSE,
                            source_id="MEDICARE-COV-1.3",
                            quote=quote_of(
                                beneficiaries,
                                (
                                    "glucocorticoid (steroid) therapy equivalent to an average of "
                                    "5.0 mg of prednisone, or greater, per day for more than 3 "
                                    "months"
                                ),
                            ),
                        ),
                        Citation(
                            kind=CitationKind.DOCUMENT,
                            source_id="RX-HISTORY",
                            quote=quote_of(
                                documents["RX-HISTORY"],
                                (
                                    "2025-12-02: prednisone 5 mg, 3 tablets daily (15 mg), 30-day "
                                    "supply."
                                ),
                            ),
                        ),
                    ),
                ),
                Assertion(
                    text=(
                        "The scan found significant bone loss since the previous study."
                        if passed
                        else "Medicare covers a scan every 12 months for patients on steroids."
                    ),
                    citations=(
                        Citation(
                            kind=CitationKind.DOCUMENT,
                            source_id="DXA-REPORT",
                            quote=quote_of(
                                documents["DXA-REPORT"],
                                (
                                    "Both changes exceed the least significant change for this "
                                    "scanner."
                                ),
                            ),
                        )
                        if passed
                        else Citation(
                            kind=CitationKind.CLAUSE,
                            source_id="MEDICARE-COV-2.1",
                            quote=unsupported_quote,
                        ),
                    ),
                ),
                Assertion(
                    text=(
                        "A redetermination must be requested within 120 days of receiving the "
                        "notice."
                    ),
                    citations=(
                        Citation(
                            kind=CitationKind.CLAUSE,
                            source_id="MEDICARE-APL-1.1",
                            quote=quote_of(
                                appeal,
                                (
                                    "any request for redetermination must be filed within 120 "
                                    "calendar days from the date a "
                                    "party receives the notice of the "
                                    "initial determination"
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            missing_evidence=("A signed order for the repeat scan, if the payer asks for it.",),
        ),
        verification=VerificationReport(
            verdicts=(
                AssertionVerdict(assertion_index=0, supported=True),
                AssertionVerdict(assertion_index=1, supported=True),
                AssertionVerdict(assertion_index=2, supported=True)
                if passed
                else AssertionVerdict(
                    assertion_index=2,
                    supported=False,
                    problems=(f'Quote not found in MEDICARE-COV-2.1: "{unsupported_quote}"',),
                ),
                AssertionVerdict(assertion_index=3, supported=True),
            )
        ),
        writer_attempts=1 if passed else 3,
        audit=(
            event(
                0,
                "rules",
                "Rule findings: PROCEDURE_CONDITIONS_CLAUSE, CLINICAL_SUPPORT_NEEDS_REVIEW.",
            ),
            event(1, "retrieval", "Selected 4 clauses."),
            event(
                10, "intake", "Extracted 3 facts from the record.", call(AGENT, 3420, 701, 8102.0)
            ),
            event(10, "record_checks", "No contradiction in the record that code can see."),
            event(
                10, "document_retrieval", "Added MEDICARE-APL-1.1 from the supporting documents."
            ),
            event(
                15,
                "triage",
                "Action: APPEAL_WITH_EVIDENCE (confidence 0.81).",
                call(AGENT, 3990, 455, 5320.0),
            ),
            *(
                (
                    event(
                        28, "writer", "Draft 1 with 4 assertions.", call(AGENT, 5110, 1320, 12010.0)
                    ),
                    event(
                        33, "verifier", "All 4 assertions verified.", call(JUDGE, 2640, 380, 4710.0)
                    ),
                    event(33, "review", "Sent for approval with a verified draft."),
                )
                if passed
                else (
                    event(
                        28, "writer", "Draft 1 with 4 assertions.", call(AGENT, 5110, 1320, 12010.0)
                    ),
                    event(31, "verifier", "1 of 4 assertions failed: 2.", None),
                    event(
                        44, "writer", "Draft 2 with 4 assertions.", call(AGENT, 5920, 1290, 11880.0)
                    ),
                    event(47, "verifier", "1 of 4 assertions failed: 2.", None),
                    event(
                        60, "writer", "Draft 3 with 4 assertions.", call(AGENT, 6010, 1301, 12200.0)
                    ),
                    event(63, "verifier", "1 of 4 assertions failed: 2.", None),
                    event(
                        63,
                        "review",
                        (
                            "Sent for approval UNVERIFIED after 3 "
                            "drafts; the failing assertions are "
                            "flagged."
                        ),
                    ),
                )
            ),
        ),
    )


async def timely_filing_state(status: CaseStatus) -> CaseState:
    case = sample("claim-filed-after-one-year")
    tf = await clauses(
        ("MEDICARE-TF-1.1", ClauseOrigin.RULE),
        ("MEDICARE-TF-1.2", ClauseOrigin.SEARCH),
        ("MEDICARE-TF-2.1", ClauseOrigin.SEARCH),
    )
    finding = Finding(
        code=FindingCode.FILING_LIMIT_EXCEEDED,
        message=(
            "The claim's submission date is 392 days after the service; the filing limit is "
            "365 days."
        ),
        clause_ids=("MEDICARE-TF-1.1",),
    )
    audit: tuple[AuditEvent, ...] = (
        event(0, "rules", "Rule findings: FILING_LIMIT_EXCEEDED."),
        event(
            1, "retrieval", "Selected 3 clauses: MEDICARE-TF-1.1, MEDICARE-TF-1.2, MEDICARE-TF-2.1."
        ),
    )
    return CaseState(
        case_id="case-timely-filing" if status is CaseStatus.FAILED else "case-timely-running",
        as_of=AS_OF,
        case_input=case.input,
        status=status,
        findings=(finding,),
        clauses=tf,
        audit=audit,
    )


def summary(state: CaseState, minutes: int) -> CaseSummary:
    snapshot = CaseSnapshot.of(state)
    created = STARTED - timedelta(minutes=minutes)
    return CaseSummary(
        **snapshot.model_dump(),
        created_at=created,
        updated_at=STARTED + timedelta(seconds=40) - timedelta(minutes=minutes),
    )


def decided(state: CaseState, decision: HumanDecision) -> CaseState:
    rejected = decision.kind is HumanDecisionKind.REJECT
    return state.model_copy(
        update={
            "case_id": f"{state.case_id}-{'rejected' if rejected else 'approved'}",
            "human_decision": decision,
            "status": CaseStatus.REJECTED if rejected else CaseStatus.APPROVED,
            "audit": (
                *state.audit,
                event(300, "approval", f"Reviewer decision: {decision.kind.value}."),
            ),
        }
    )


def dump(name: str, value: Any) -> None:
    path = TARGET / name
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path}")


async def build_states() -> list[CaseState]:
    awaiting = await modifier_25_state()
    bone = await bone_density_state(passed=True)
    unverified = await bone_density_state(passed=False)
    failed = await timely_filing_state(CaseStatus.FAILED)
    running = await timely_filing_state(CaseStatus.RUNNING)
    approved = decided(bone, HumanDecision(kind=HumanDecisionKind.APPROVE))
    rejected = decided(
        awaiting,
        HumanDecision(
            kind=HumanDecisionKind.REJECT, reason="The diabetes review was routine follow-up only."
        ),
    )

    return [awaiting, unverified, running, failed, approved, rejected, bone]


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    states = asyncio.run(build_states())
    awaiting = states[0]
    views = [
        CaseView(summary=summary(state, minutes=index * 7), state=state)
        for index, state in enumerate(states)
    ]
    # A case row with no saved workflow state, as test data written straight to the
    # database leaves behind. The page must say so instead of waiting for it.
    orphan = summary(awaiting, minutes=len(states) * 7).model_copy(
        update={"case_id": "case-without-state", "claim_id": "CLM-TEST-0001"}
    )
    views.append(CaseView(summary=orphan, state=None))
    dump("cases.json", [view.model_dump(mode="json") for view in views])

    samples = [sample(path.stem) for path in sorted(SAMPLES.glob("*.json"))]
    dump("samples.json", [item.model_dump(mode="json") for item in samples])

    # The steps a new run reports over its event stream, in order.
    steps = list(awaiting.audit)
    dump(
        "run-events.json",
        [
            CaseEvent(sequence=index, event=step).model_dump(mode="json")
            for index, step in enumerate(steps, start=1)
        ],
    )
    # The submission check the API applies, so the mock can reject what the API would.
    CaseInput.model_validate(samples[0].input.model_dump(mode="json"))


if __name__ == "__main__":
    main()
