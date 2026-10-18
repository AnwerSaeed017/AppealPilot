"""Per-case building blocks: seeded incidental values, payload builders and documents."""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.schemas.code_types import VISIT_NOTE_DOCUMENT_ID
from app.schemas.recommended_action import RecommendedAction

# Billed amount per unit, by procedure code. Invented figures.
CHARGES: dict[str, str] = {
    "99213": "135.00",
    "99214": "185.00",
    "17110": "160.00",
    "20610": "140.00",
    "29881": "2400.00",
    "72148": "710.00",
    "73721": "620.00",
    "93000": "55.00",
    "95810": "980.00",
    "97110": "45.00",
    "E0601": "95.00",
    "J7325": "480.00",
}

REMARKS: dict[str, str] = {
    "4": "Required modifier missing, or modifier inconsistent with the procedure.",
    "11": "Diagnosis is inconsistent with the procedure.",
    "18": "Exact duplicate of a claim or service already processed.",
    "29": "The time limit for filing has expired.",
    "50": "Service not deemed medically necessary on the information submitted.",
    "197": "Authorization or precertification absent.",
    "252": "Additional documentation is required to adjudicate this claim.",
}


def make_npi(rng: random.Random) -> str:
    """A random NPI with a valid check digit."""
    body = "1" + "".join(str(rng.randint(0, 9)) for _ in range(8))
    total = 0
    # The check digit will sit in position 0 from the right, so the body starts at 1.
    for position, character in enumerate(reversed("80840" + body), start=1):
        digit = int(character)
        if position % 2 == 1:
            digit = digit * 2 - 9 if digit > 4 else digit * 2
        total += digit
    return body + str((10 - total % 10) % 10)


class Doc:
    """A document built line by line, remembering which lines carry the evidence."""

    def __init__(self, document_id: str = VISIT_NOTE_DOCUMENT_ID) -> None:
        self.document_id = document_id
        self._lines: list[str] = []
        self._tags: dict[str, list[int]] = {}

    def add(self, text: str, tag: str | None = None) -> "Doc":
        self._lines.append(text)
        if tag is not None:
            self._tags.setdefault(tag, []).append(len(self._lines))
        return self

    @property
    def text(self) -> str:
        return "\n".join(self._lines)

    def refs(self, *tags: str) -> list[dict[str, Any]]:
        """Evidence references for every line carrying one of the tags, in line order."""
        numbers = sorted(number for tag in tags for number in self._tags[tag])
        return [{"document_id": self.document_id, "line_number": number} for number in numbers]


@dataclass
class Built:
    """What a scenario returns: the raw input and the label that goes with it."""

    input: dict[str, Any]
    as_of_date: date
    action: RecommendedAction | None
    rationale: str
    clauses: tuple[str, ...] = ()
    evidence: list[dict[str, Any]] = field(default_factory=list)
    missing: tuple[str, ...] = ()
    correction: str | None = None
    alternatives: tuple[RecommendedAction, ...] = ()
    tags: tuple[str, ...] = ()


class Kit:
    """Seeded values and builders for one case.

    The seed combines the run seed with the scenario key, so a case does not change
    when other scenarios are added, removed or reordered.
    """

    def __init__(self, seed: int, key: str, payer: str) -> None:
        self.rng = random.Random(f"{seed}:{key}")
        self.payer = payer
        self.side = self.rng.choice(("right", "left"))
        self.age = self.rng.randint(34, 78)
        self.sex = self.rng.choice(("woman", "man"))
        self.dos = date(2026, 2, 2) + timedelta(days=self.rng.randint(0, 150))
        self.claim_id = self.new_claim_id()
        self.member_id = f"{payer}-{self.rng.randint(10_000_000, 99_999_999)}"
        self.patient_id = f"PT-{self.rng.randint(1, 999_999):06d}"
        self.npi = make_npi(self.rng)
        self._birth_offset = self.rng.randint(10, 350)
        self.submitted = self.dos + timedelta(days=self.rng.randint(3, 10))
        self.denied = self.submitted + timedelta(days=self.rng.randint(10, 20))
        self.as_of = self.denied + timedelta(days=self.rng.randint(5, 15))

    # Incidental values -------------------------------------------------------

    def pick(self, *options: str) -> str:
        return self.rng.choice(options)

    def between(self, low: int, high: int) -> int:
        return self.rng.randint(low, high)

    def new_claim_id(self) -> str:
        return f"CLM-2026-{self.rng.randint(1, 999_999):06d}"

    def reference(self, prefix: str) -> str:
        return f"{prefix}-{self.rng.randint(100_000, 999_999)}"

    @property
    def side_modifier(self) -> str:
        return "RT" if self.side == "right" else "LT"

    @property
    def other_side(self) -> str:
        return "left" if self.side == "right" else "right"

    @property
    def knee_oa_code(self) -> str:
        return "M17.11" if self.side == "right" else "M17.12"

    @property
    def knee_pain_code(self) -> str:
        return "M25.561" if self.side == "right" else "M25.562"

    def reschedule(self, *, dos: date | None = None, submit_after: int | None = None) -> None:
        """Move the date of service or the submission date; later dates follow."""
        if dos is not None:
            self.dos = dos
        gap_to_submission = (
            submit_after if submit_after is not None else (self.submitted - self.dos).days
        )
        gap_to_denial = (self.denied - self.submitted).days
        gap_to_as_of = (self.as_of - self.denied).days
        self.submitted = self.dos + timedelta(days=gap_to_submission)
        self.denied = self.submitted + timedelta(days=gap_to_denial)
        self.as_of = self.denied + timedelta(days=gap_to_as_of)

    # Payload builders --------------------------------------------------------

    def line(
        self,
        number: int,
        code: str,
        *,
        modifiers: tuple[str, ...] = (),
        pointers: tuple[int, ...] = (1,),
        units: int = 1,
    ) -> dict[str, Any]:
        return {
            "line_number": number,
            "service_date": self.dos.isoformat(),
            "procedure_code": code,
            "modifiers": list(modifiers),
            "diagnosis_pointers": list(pointers),
            "units": units,
            "charge_amount": str(Decimal(CHARGES[code]) * units),
        }

    def claim(
        self,
        lines: list[dict[str, Any]],
        diagnoses: tuple[str, ...],
        *,
        place_of_service: str = "11",
        authorization: str | None = None,
        original_claim_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "claim_id": self.claim_id,
            "payer_id": self.payer,
            "member_id": self.member_id,
            "patient_id": self.patient_id,
            "patient_date_of_birth": self._date_of_birth().isoformat(),
            "billing_provider_npi": self.npi,
            "place_of_service": place_of_service,
            "submitted_date": self.submitted.isoformat(),
            "diagnosis_codes": list(diagnoses),
            "lines": lines,
            "total_charge": str(
                sum((Decimal(line["charge_amount"]) for line in lines), Decimal(0))
            ),
        }
        if authorization is not None:
            payload["prior_authorization_number"] = authorization
        if original_claim_id is not None:
            payload["original_claim_id"] = original_claim_id
        return payload

    def denial(
        self,
        claim: dict[str, Any],
        carc: str,
        *,
        lines: tuple[int, ...] = (),
        remark: str | None = None,
    ) -> dict[str, Any]:
        denied_lines = [
            line for line in claim["lines"] if not lines or line["line_number"] in lines
        ]
        return {
            "claim_id": claim["claim_id"],
            "payer_id": claim["payer_id"],
            "group_code": "CO",
            "carc_code": carc,
            "rarc_codes": [],
            "denial_date": self.denied.isoformat(),
            "denied_line_numbers": list(lines),
            "denied_amount": str(
                sum((Decimal(line["charge_amount"]) for line in denied_lines), Decimal(0))
            ),
            "payer_remark": remark or REMARKS[carc],
        }

    def prior_claim(
        self,
        lines: list[dict[str, Any]],
        *,
        outcome: str,
        carc: str | None = None,
        received_before: int = 20,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "claim_id": self.new_claim_id(),
            "received_date": (self.submitted - timedelta(days=received_before)).isoformat(),
            "outcome": outcome,
            "lines": lines,
        }
        if carc is not None:
            payload["carc_code"] = carc
        return payload

    def note(self, complaint: str) -> Doc:
        """A visit note opened with the lines every note has."""
        doc = Doc()
        doc.add(f"Date of visit: {self.dos.isoformat()}")
        doc.add(f"Patient: {self.age}-year-old {self.sex}, established patient.")
        doc.add(f"Chief complaint: {complaint}")
        return doc

    def sign(self, doc: Doc) -> Doc:
        doc.add(
            self.pick(
                f"Electronically signed by the treating clinician, {self.dos.isoformat()}.",
                f"Signed: treating clinician. {self.dos.isoformat()}.",
            )
        )
        return doc

    def case_input(
        self,
        claim: dict[str, Any],
        denial: dict[str, Any],
        note: Doc,
        *,
        documents: tuple[tuple[Doc, str, date], ...] = (),
        prior_claims: tuple[dict[str, Any], ...] = (),
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "claim": claim,
            "denial": denial,
            "visit_note": {"encounter_date": self.dos.isoformat(), "text": note.text},
        }
        if documents:
            payload["supporting_documents"] = [
                {
                    "document_id": doc.document_id,
                    "kind": kind,
                    "document_date": document_date.isoformat(),
                    "text": doc.text,
                }
                for doc, kind, document_date in documents
            ]
        if prior_claims:
            payload["prior_claims"] = list(prior_claims)
        return payload

    def _date_of_birth(self) -> date:
        return self.dos - timedelta(days=int(self.age * 365.25) + self._birth_offset)
