from dataclasses import replace

import pytest

from physical_harness.core.contracts import VerificationRequest, VerificationResult
from physical_harness.core.contracts import VerificationVerdict as V
from physical_harness.reasoning.verification import VerificationPolicy, VerificationRouter


class World:
    name = "world"

    def __init__(self, confidence=0.99, evidence=("world-e",)):
        self.confidence, self.evidence = confidence, evidence

    def predicate_confidence(self, predicate):
        return self.confidence

    def predicate_evidence(self, predicate):
        return self.evidence


class Verifier:
    def __init__(self, verdict=V.VERIFIED, confidence=0.99, **changes):
        self.calls = 0
        self.result = replace(
            VerificationResult("r", "verifier", verdict, confidence, ("request-e",)), **changes
        )

    def verify(self, request):
        self.calls += 1
        return self.result


def request(**changes):
    return replace(
        VerificationRequest("r", "s", ("IN(cup,cabinet)",), after_evidence_ids=("request-e",)),
        **changes,
    )


def test_tier_one_requires_own_evidence_and_avoids_models():
    cheap, frontier = Verifier(), Verifier()
    result = VerificationRouter(World(), cheap, frontier).verify(request())
    assert result.verdict == V.VERIFIED
    assert result.evidence_ids == ("world-e",)
    assert cheap.calls == frontier.calls == 0
    assert VerificationRouter(World(evidence=())).verify(request()).verdict == V.UNCERTAIN


def test_missing_evidence_api_and_empty_predicates():
    class LegacyWorld:
        name = "legacy"

        def predicate_confidence(self, predicate):
            return 0.99

    assert VerificationRouter(LegacyWorld()).verify(request()).verdict == V.UNCERTAIN
    cheap = Verifier()
    assert (
        VerificationRouter(World(), cheap).verify(request(expected_predicates=())).verdict
        == V.UNCERTAIN
    )
    assert cheap.calls == 0


def test_rejection_has_world_support():
    result = VerificationRouter(World(0.01)).verify(request())
    assert result.verdict == V.REJECTED
    assert result.evidence_ids == ("world-e",)


def test_cheap_then_frontier_only_when_needed():
    cheap, frontier = Verifier(), Verifier()
    router = VerificationRouter(World(0.5), cheap, frontier)
    assert router.verify(request()).verdict == V.VERIFIED
    assert cheap.calls == 1 and frontier.calls == 0
    cheap.result = replace(cheap.result, verdict=V.UNCERTAIN)
    assert router.verify(request()).verdict == V.VERIFIED
    assert cheap.calls == 2 and frontier.calls == 1


def test_high_consequence_escalates_even_confident_world():
    cheap, frontier = Verifier(), Verifier()
    assert (
        VerificationRouter(World(), cheap, frontier).verify(request(high_consequence=True)).verdict
        == V.VERIFIED
    )
    assert cheap.calls == frontier.calls == 1
    assert (
        VerificationRouter(World(), Verifier()).verify(request(high_consequence=True)).verdict
        == V.UNCERTAIN
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"request_id": "other"},
        {"confidence": float("nan")},
        {"confidence": float("inf")},
        {"confidence": -1},
        {"confidence": True},
        {"verdict": "bogus"},
    ],
)
def test_invalid_model_response_rejected(changes):
    with pytest.raises(ValueError):
        VerificationRouter(World(0.5), Verifier(**changes)).verify(request())


def test_unsupported_or_low_confidence_model_result_uncertain():
    assert (
        VerificationRouter(World(0.5), Verifier(evidence_ids=())).verify(request()).verdict
        == V.UNCERTAIN
    )
    result = VerificationRouter(World(0.5), frontier=Verifier(confidence=0.5)).verify(request())
    assert result.verdict == V.UNCERTAIN


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -0.1, 1.1, True])
def test_invalid_world_confidence_and_policy_rejected(confidence):
    with pytest.raises(ValueError):
        VerificationRouter(World(confidence)).verify(request())
    with pytest.raises(ValueError):
        VerificationPolicy(world_verified_threshold=confidence)


@pytest.mark.parametrize(
    "changes", [{"request_id": ""}, {"skill_id": ""}, {"high_consequence": "false"}]
)
def test_invalid_request_rejected(changes):
    with pytest.raises(ValueError):
        VerificationRouter(World()).verify(request(**changes))


def test_frontier_response_validation_and_uncertainty():
    with pytest.raises(ValueError, match="request ID"):
        VerificationRouter(World(0.5), frontier=Verifier(request_id="other")).verify(request())
    result = VerificationRouter(World(0.5), frontier=Verifier(V.UNCERTAIN)).verify(request())
    assert result.verdict == V.UNCERTAIN


@pytest.mark.parametrize("verdict", [V.VERIFIED, V.REJECTED])
@pytest.mark.parametrize("tier", ["cheap_vlm", "frontier"])
def test_forged_model_evidence_cannot_decide(verdict, tier):
    router = VerificationRouter(World(0.5), **{tier: Verifier(verdict, evidence_ids=("forged",))})
    assert router.verify(request()).verdict == V.UNCERTAIN


def test_invalid_cheap_evidence_escalates_to_supported_frontier():
    cheap = Verifier(evidence_ids=("forged",))
    frontier = Verifier()
    result = VerificationRouter(World(0.5), cheap, frontier).verify(request())
    assert result.verdict == V.VERIFIED
    assert cheap.calls == frontier.calls == 1


def test_before_reference_is_allowed():
    router = VerificationRouter(World(0.5), Verifier(V.REJECTED, evidence_ids=("before",)))
    assert router.verify(request(before_evidence_ids=("before",))).verdict == V.REJECTED


@pytest.mark.parametrize("identifier", ["stale", "other-episode", "inferred", "missing", "fresh"])
def test_stateful_validator_rejects_invalid_supplied_evidence(identifier):
    from physical_harness.world.state import WorldState

    with WorldState(":memory:", "ep") as state:
        state.add_evidence("stale", 1, "perception", "old.png")
        state.add_evidence("fresh", 10, "perception", "new.png")
        state.add_evidence("inferred", 10, "inference", "inference.json")

        def validate(evidence_id, req):
            assert req.request_id == "r"
            try:
                evidence = state._evidence(evidence_id)
            except ValueError:
                return False
            return (
                evidence["kind"] in {"perception", "telemetry"}
                and 0 <= 10 - evidence["sim_time"] <= 5
            )

        router = VerificationRouter(
            World(0.5),
            Verifier(evidence_ids=(identifier,)),
            frontier=Verifier(evidence_ids=(identifier,)),
            evidence_validator=validate,
        )
        result = router.verify(request(after_evidence_ids=(identifier,)))
        assert result.verdict == (V.VERIFIED if identifier == "fresh" else V.UNCERTAIN)
