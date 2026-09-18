import pytest

from physical_harness.contracts import VerificationRequest
from physical_harness.visual_verifier import EvidenceVisualVerifier


@pytest.mark.parametrize(
    "qualified,citation,expected",
    [
        (False, "after", "uncertain"),
        (True, "before", "uncertain"),
        (True, "invented", "uncertain"),
        (True, "after", "verified"),
    ],
)
def test_visual_citations_and_qualification(qualified, citation, expected):
    def judge(packet):
        assert packet["world"] == {}
        assert packet["expected"] == ["radio is on table"]
        return {
            "verdict": "verified",
            "confidence": 0.95,
            "evidence_ids": [citation],
            "reason": "visible",
            "tier": 2,
        }

    verifier = EvidenceVisualVerifier(
        judge, before=[{"id": "before"}], after=[{"id": "after"}], qualified=qualified
    )
    result = verifier.verify(
        VerificationRequest("r", "s", ("radio is on table",), ("before",), ("after",))
    )
    assert result.verdict == expected


def test_foreign_frame_rejected_before_model_call():
    verifier = EvidenceVisualVerifier(
        lambda _: pytest.fail("model called"), before=[], after=[{"id": "foreign"}]
    )
    with pytest.raises(ValueError):
        verifier.verify(VerificationRequest("r", "s", ("claim",), after_evidence_ids=("after",)))


@pytest.mark.parametrize(
    "field,value",
    [
        ("confidence", float("nan")),
        ("confidence", True),
        ("confidence", 1.1),
        ("tier", 3),
        ("evidence_ids", "after"),
        ("reason", None),
    ],
)
def test_malformed_result_is_not_accepted(field, value):
    raw = {
        "verdict": "verified",
        "confidence": 0.9,
        "tier": 2,
        "evidence_ids": ["after"],
        "reason": "visible",
    }
    raw[field] = value
    verifier = EvidenceVisualVerifier(
        lambda _: raw, before=[], after=[{"id": "after"}], qualified=True
    )
    with pytest.raises(ValueError):
        verifier.verify(VerificationRequest("r", "s", ("claim",), after_evidence_ids=("after",)))
