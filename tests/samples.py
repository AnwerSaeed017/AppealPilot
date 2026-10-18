"""Hand-written synthetic payloads shared by tests. No real patient or payer data."""

from typing import Any


def claim_payload() -> dict[str, Any]:
    return {
        "claim_id": "CLM-2026-000123",
        "payer_id": "ACME",
        "member_id": "ACM-88120045",
        "patient_id": "PT-000417",
        "patient_date_of_birth": "1961-03-14",
        "billing_provider_npi": "1234567893",
        "place_of_service": "11",
        "submitted_date": "2026-06-09",
        "diagnosis_codes": ["M17.11", "E11.9"],
        "lines": [
            {
                "line_number": 1,
                "service_date": "2026-06-02",
                "procedure_code": "99214",
                "modifiers": ["25"],
                "diagnosis_pointers": [1, 2],
                "units": 1,
                "charge_amount": "185.00",
            },
            {
                "line_number": 2,
                "service_date": "2026-06-02",
                "procedure_code": "20610",
                "modifiers": ["RT"],
                "diagnosis_pointers": [1],
                "units": 1,
                "charge_amount": "140.00",
            },
        ],
        "total_charge": "325.00",
    }


def denial_payload() -> dict[str, Any]:
    return {
        "claim_id": "CLM-2026-000123",
        "payer_id": "ACME",
        "group_code": "CO",
        "carc_code": "197",
        "rarc_codes": ["N54"],
        "denial_date": "2026-06-23",
        "denied_line_numbers": [2],
        "denied_amount": "140.00",
        "payer_remark": "Precertification/authorization/notification absent.",
    }


def visit_note_payload() -> dict[str, Any]:
    return {
        "encounter_date": "2026-06-02",
        "text": (
            "Established patient seen for right knee pain.\n"
            "Assessment: primary osteoarthritis, right knee. Type 2 diabetes, stable.\n"
            "Procedure: arthrocentesis and injection, right knee, performed today.\n"
            "Authorization obtained by phone on 2026-05-29."
        ),
    }


def case_input_payload() -> dict[str, Any]:
    return {
        "claim": claim_payload(),
        "denial": denial_payload(),
        "visit_note": visit_note_payload(),
    }


def policy_clause_payload() -> dict[str, Any]:
    return {
        "clause_id": "ACME-PA-4.2",
        "policy_id": "ACME-PA",
        "payer_id": "ACME",
        "policy_title": "Prior Authorization Requirements",
        "section_heading": "Retrospective authorization",
        "text": (
            "A claim denied for absent authorization may be reconsidered when the "
            "provider supplies the authorization number issued before the date of service."
        ),
        "effective_from": "2026-01-01",
    }
