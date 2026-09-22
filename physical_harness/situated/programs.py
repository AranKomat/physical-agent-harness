"""Review custom programs through the EXISTING catalog/runtime, never a new actuator."""
from __future__ import annotations

import time
from dataclasses import replace

from ..action_compiler.compiler import Catalog, CompiledAction
from ..action_compiler.runtime import StepReview
from ..action_compiler.types import Basis, Check, Program, Review, ids, number


def catalog_for_programs(basis: Basis, programs: tuple[Program, ...], *, review, deadline,
                         ttl_s=2., clock=time.monotonic) -> Catalog:
    number(ttl_s, low=.001, high=120)
    if type(programs) is not tuple or not 1 <= len(programs) <= 64:
        raise ValueError("Bounded immutable programs required")
    ids(tuple(p.proposal.id for p in programs))
    actions = []
    for program in programs:
        basis.require_same(program.proposal.basis)
        if clock() >= deadline:
            raise TimeoutError("Program review deadline")
        result = review(program, basis, deadline)
        if not isinstance(result, Review):
            raise ValueError("Typed native review required")
        actions.append(CompiledAction(program, result, result.failures(program, basis)))
    if clock() >= deadline:
        raise TimeoutError("Late review")
    return Catalog(basis, programs[0].proposal.gripper_fingerprint, tuple(actions),
                   basis.captured_wall + ttl_s)


def enforce_extra_step_checks(driver, checks: dict):
    """Extend a native Driver, retaining every original gate and callback.

    Each situated_* check in the program must be established again per step.
    Missing/unknown checks block. Keys and callbacks are installed by the operator,
    never supplied by a graph, model, or confidence score. This is no sandbox.
    """
    if not all(isinstance(k, str) and callable(v) for k, v in checks.items()):
        raise ValueError("Named reviewed callbacks required")
    original = driver.review_step

    def review(program, index, basis, deadline):
        old = original(program, index, basis, deadline)
        if not isinstance(old, StepReview):
            raise ValueError("Original StepReview required")
        old.require(program, index, basis)
        values = {c.name: c for c in old.checks}
        for name in program.required_checks:
            if not name.startswith("situated_"):
                continue
            fn = checks.get(name)
            new = fn(program, index, basis, deadline) if fn else Check(
                name, None, basis.evidence_ids, "Situated native reviewer is absent")
            if not isinstance(new, Check) or new.name != name or new.passed is not True:
                raise PermissionError("Situated per-step gate not established: " + name)
            values[name] = new
        return StepReview(program.fingerprint, index, basis.fingerprint, tuple(values.values()))

    return replace(driver, review_step=review)
