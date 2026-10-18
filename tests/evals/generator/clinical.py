"""Routine clinical pictures for services whose medical detail does not decide the case.

Scenarios about authorization, filing or duplicates use these so the note reads like a
real visit. Scenarios that turn on the clinical detail write their own note.
"""

from collections.abc import Callable
from dataclasses import dataclass

from tests.evals.generator.kit import Doc, Kit


@dataclass(frozen=True)
class Service:
    code: str
    label: str
    complaint: str
    diagnoses: tuple[str, ...]
    modifiers: tuple[str, ...]
    # (text, tag) pairs; the line that orders or performs the service is tagged "service".
    lines: tuple[tuple[str, str | None], ...]

    def write_note(self, kit: Kit) -> Doc:
        note = kit.note(self.complaint)
        for text, tag in self.lines:
            note.add(text, tag)
        return kit.sign(note)


def knee_mri(kit: Kit) -> Service:
    weeks = kit.between(2, 5)
    return Service(
        code="73721",
        label=f"MRI of the {kit.side} knee without contrast",
        complaint=f"{kit.side} knee pain",
        diagnoses=(kit.knee_pain_code,),
        modifiers=(kit.side_modifier,),
        lines=(
            (
                f"History: {kit.side} knee pain for {weeks} weeks after a twisting injury. "
                + kit.pick(
                    "The knee has locked several times.",
                    "Reports the knee catching and briefly locking.",
                ),
                None,
            ),
            (
                "Examination: medial joint-line tenderness, positive McMurray test, no effusion.",
                None,
            ),
            ("Assessment: suspected medial meniscal tear.", None),
            (f"Plan: MRI of the {kit.side} knee without contrast.", "service"),
        ),
    )


def lumbar_mri(kit: Kit) -> Service:
    weeks = kit.between(7, 12)
    return Service(
        code="72148",
        label="MRI of the lumbar spine without contrast",
        complaint="low back pain radiating to the leg",
        diagnoses=("M54.16",),
        modifiers=(),
        lines=(
            (
                f"History: low back pain for {weeks} weeks, radiating below the knee. "
                f"Naproxen and a home exercise programme for {weeks - 1} weeks "
                "without improvement.",
                None,
            ),
            (
                "Examination: straight-leg raise positive; ankle reflex reduced on the "
                "affected side.",
                None,
            ),
            ("Assessment: lumbar radiculopathy.", None),
            ("Plan: MRI of the lumbar spine without contrast.", "service"),
        ),
    )


def sleep_study(kit: Kit) -> Service:
    return Service(
        code="95810",
        label="attended sleep study",
        complaint="daytime sleepiness and loud snoring",
        diagnoses=("G47.10", "R06.83"),
        modifiers=(),
        lines=(
            (
                "History: partner reports loud snoring and pauses in breathing. "
                + kit.pick(
                    "Falls asleep at work most afternoons.",
                    "Struggles to stay awake while driving.",
                ),
                None,
            ),
            ("Examination: crowded oropharynx; neck circumference 44 cm.", None),
            ("Assessment: suspected obstructive sleep apnea.", None),
            ("Plan: attended overnight sleep study.", "service"),
        ),
    )


def hyaluronan(kit: Kit) -> Service:
    return Service(
        code="J7325",
        label=f"hyaluronan injection of the {kit.side} knee",
        complaint=f"{kit.side} knee pain from osteoarthritis",
        diagnoses=(kit.knee_oa_code,),
        modifiers=(kit.side_modifier,),
        lines=(
            (
                f"History: osteoarthritis of the {kit.side} knee, confirmed on radiograph. "
                "Pain persists despite regular analgesics and a course of physical therapy.",
                None,
            ),
            ("Examination: crepitus, small effusion, reduced flexion.", None),
            (f"Assessment: primary osteoarthritis, {kit.side} knee.", None),
            (f"Procedure: hyaluronan injected into the {kit.side} knee.", "service"),
        ),
    )


def arthroscopy(kit: Kit) -> Service:
    return Service(
        code="29881",
        label=f"arthroscopic meniscectomy of the {kit.side} knee",
        complaint=f"locked {kit.side} knee",
        diagnoses=("S83.241A" if kit.side == "right" else "S83.242A",),
        modifiers=(kit.side_modifier,),
        lines=(
            (
                f"History: {kit.side} knee locked in flexion since a twisting injury; "
                "unable to straighten it or bear weight.",
                None,
            ),
            ("Examination: knee held at 30 degrees, block to extension.", None),
            ("Assessment: displaced medial meniscal tear with a locked knee.", None),
            (
                f"Procedure: arthroscopic partial medial meniscectomy, {kit.side} knee.",
                "service",
            ),
        ),
    )


def joint_injection(kit: Kit) -> Service:
    return Service(
        code="20610",
        label=f"injection of the {kit.side} knee",
        complaint=f"{kit.side} knee pain",
        diagnoses=(kit.knee_oa_code,),
        modifiers=(kit.side_modifier,),
        lines=(
            (
                f"History: osteoarthritis of the {kit.side} knee; "
                + kit.pick("pain worse on stairs.", "pain limits walking to one block."),
                None,
            ),
            ("Examination: crepitus and a small effusion.", None),
            (f"Assessment: primary osteoarthritis, {kit.side} knee.", None),
            (
                f"Procedure: {kit.side} knee aspirated and injected with corticosteroid.",
                "service",
            ),
        ),
    )


def office_visit(kit: Kit) -> Service:
    systolic = kit.between(128, 146)
    return Service(
        code="99213",
        label="office visit",
        complaint="blood pressure follow-up",
        diagnoses=("I10",),
        modifiers=(),
        lines=(
            ("History: hypertension, taking lisinopril daily. No headaches.", None),
            (f"Examination: blood pressure {systolic}/{kit.between(78, 88)}.", None),
            ("Assessment: essential hypertension.", None),
            ("Plan: continue current dose; review in three months.", "service"),
        ),
    )


SERVICES: dict[str, Callable[[Kit], Service]] = {
    "knee_mri": knee_mri,
    "lumbar_mri": lumbar_mri,
    "sleep_study": sleep_study,
    "hyaluronan": hyaluronan,
    "arthroscopy": arthroscopy,
    "joint_injection": joint_injection,
    "office_visit": office_visit,
}
