import pytest

from physical_harness.core.contracts import VerificationRequest
from physical_harness.reasoning.visual_verifier import EvidenceVisualVerifier, GPT6EvidenceVerifier


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
        assert packet["verifier"]["role"] == "frontier_semantic_verifier"
        return {
            "verdict": "verified",
            "confidence": 0.95,
            "evidence_ids": [citation],
            "reason": "visible",
            "tier": 3,
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
        ("tier", 2),
        ("evidence_ids", "after"),
        ("reason", None),
    ],
)
def test_malformed_result_is_not_accepted(field, value):
    raw = {
        "verdict": "verified",
        "confidence": 0.9,
        "tier": 3,
        "evidence_ids": ["after"],
        "reason": "visible",
    }
    raw[field] = value
    verifier = EvidenceVisualVerifier(
        lambda _: raw, before=[], after=[{"id": "after"}], qualified=True
    )
    with pytest.raises(ValueError):
        verifier.verify(VerificationRequest("r", "s", ("claim",), after_evidence_ids=("after",)))


def test_gpt6_verifier_has_explicit_tier_role_and_model_metadata():
    def judge(packet):
        assert packet["verifier"] == {
            "name": "gpt6-evidence-verifier",
            "role": "frontier_semantic_verifier",
            "model": "gpt-6-astra",
        }
        assert "tier (3)" in packet["instruction"]
        return {
            "verdict": "uncertain",
            "confidence": 0.8,
            "evidence_ids": ["after"],
            "reason": "Electrical state is not visible.",
            "tier": 3,
        }

    verifier = GPT6EvidenceVerifier(
        judge, before=[], after=[{"id": "after"}], qualified=True
    )
    result = verifier.verify(
        VerificationRequest("r", "s", ("radio powered",), after_evidence_ids=("after",))
    )
    assert result.verifier == "gpt6-evidence-verifier"
    assert result.metadata["tier"] == 3
    assert result.metadata["role"] == "frontier_semantic_verifier"
    assert result.metadata["model"] == "gpt-6-astra"


@pytest.mark.parametrize("tier", [True, 0, 1, 4, "3"])
def test_invalid_visual_verifier_tier_rejected(tier):
    with pytest.raises(ValueError):
        EvidenceVisualVerifier(lambda _: {}, before=[], after=[], tier=tier)
