from physical_harness.hybrid_v0.contracts import Regime
from physical_harness.hybrid_v0.integration import policy_exposure_diagnostic_routes


def test_short_diagnostics_equalize_policy_exposure_not_total_horizon():
    routes = policy_exposure_diagnostic_routes(
        target="radio", policy_instruction="turn on the radio",
        policy_steps=384, navigation_steps=60, staging_steps=80,
    )
    assert set(routes) == {"A-short", "B-short", "C-short"}
    policy_steps = {
        key: next(p.max_steps for p in route.phases if p.regime == Regime.POLICY)
        for key, route in routes.items()
    }
    assert set(policy_steps.values()) == {384}
    totals = {key: sum(p.max_steps for p in route.phases) for key, route in routes.items()}
    assert totals["A-short"] < totals["B-short"] < totals["C-short"]
    assert routes["A-short"].phases[0].policy_entry == "ordinary_start"
    assert routes["B-short"].phases[-1].policy_entry == "handoff"
