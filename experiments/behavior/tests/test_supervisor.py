import json

import numpy as np
import pytest
from jsonschema.exceptions import ValidationError

from experiments.behavior.contracts import Observation, Stamp
from experiments.behavior.observations import EvidenceStore
from experiments.behavior.supervisor import BLOCK, STEPS, SkillSupervisor, current_packet


def observation(store, sequence=0, session="test"):
    stamp = Stamp(session=session, epoch=0, sequence=sequence)
    return Observation(
        stamp=stamp, observed_at=float(sequence), proprio=tuple([0.] * 61),
        rgb={camera: store.put(np.zeros((8, 8, 3), dtype=np.uint8), "rgb", stamp,
                               float(sequence))
             for camera in ("head", "left_wrist", "right_wrist")},
        depth={},
    )


class Model:
    def __init__(self):
        self.calls = []
        self.unsafe = False
        self.skill = "approach_table_radio"
        self.instructions = []

    def call(self, ident, role, instruction, context, images, schema):
        self.calls.append((role, context, images))
        self.instructions.append(instruction)
        if role == "executive":
            return {"skill": self.skill, "reason": "visible evidence"}
        return {"power": "uncertain", "unsafe_to_continue": self.unsafe,
                "reason": "no visible power indicator"}


def setup(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")
    model = Model()
    supervisor = SkillSupervisor(model, tmp_path / "supervisor.jsonl")
    return store, model, supervisor


def test_nine_blocks_exact_action_and_model_call_budget(tmp_path):
    store, model, supervisor = setup(tmp_path)
    sequence = 0
    while sequence < STEPS:
        _, n = supervisor.choose(observation(store, sequence), store)
        assert 0 < n <= BLOCK
        sequence += n
    supervisor.verify(observation(store, sequence), store)
    assert sequence == 3224 and len(model.calls) == 18
    assert [c[0] for c in model.calls] == ["executive", "verifier"] * 9
    with pytest.raises(ValueError):
        supervisor.choose(observation(store, sequence), store)


def test_verifier_is_separate_fresh_current_context_only(tmp_path):
    store, model, supervisor = setup(tmp_path)
    supervisor.choose(observation(store), store)
    supervisor.choose(observation(store, BLOCK), store)
    _, verifier_context, images = model.calls[1]
    assert verifier_context["sequence"] == BLOCK
    assert all(image.captured_at == BLOCK / 30 for image in images)
    assert "skills" not in verifier_context and "latest_verification" not in verifier_context
    assert "native_success" not in json.dumps(verifier_context)
    assert model.calls[2][1]["latest_verification"]["power"] == "uncertain"


@pytest.mark.parametrize("session,sequence", [("test", 0), ("foreign", BLOCK)])
def test_stale_or_foreign_verification_fails(tmp_path, session, sequence):
    store, model, supervisor = setup(tmp_path)
    supervisor.choose(observation(store), store)
    with pytest.raises(ValueError):
        supervisor.verify(observation(store, sequence, session), store)
    assert len(model.calls) == 1


def test_safety_stop_does_not_dispatch_next_executive(tmp_path):
    store, model, supervisor = setup(tmp_path)
    supervisor.choose(observation(store), store)
    model.unsafe = True
    assert supervisor.choose(observation(store, BLOCK), store) == (None, 0)
    assert len(model.calls) == 2 and supervisor.stop_reason == "verifier_safety_stop"


def test_executive_stop_and_invalid_skill(tmp_path):
    store, model, supervisor = setup(tmp_path)
    model.skill = "privileged_teleport"
    with pytest.raises(ValidationError):
        supervisor.choose(observation(store), store)
    assert supervisor.pending is None
    model.skill = "stop"
    assert supervisor.choose(observation(store), store) == (None, 0)


def test_tampered_image_rejected_before_dispatch(tmp_path):
    store, model, supervisor = setup(tmp_path)
    obs = observation(store)
    (store.root / obs.rgb["head"].uri).write_bytes(b"tampered")
    with pytest.raises(ValueError):
        supervisor.choose(obs, store)
    assert not model.calls


def test_packet_ignores_nonallowlisted_state(tmp_path):
    store, _, _ = setup(tmp_path)
    context, images = current_packet(observation(store), store)
    assert set(context) == {"episode", "sequence", "sim_time", "goal",
                            "current_proprioception", "current_images"}
    assert len(images) == 3


def test_matched_prompt_preserves_budget_and_is_backend_neutral(tmp_path):
    from experiments.behavior.supervisor import MATCHED_EXECUTIVE, VERIFIER

    store = EvidenceStore(tmp_path / "evidence")
    model = Model()
    supervisor = SkillSupervisor(model, tmp_path / "supervisor.jsonl", MATCHED_EXECUTIVE)
    supervisor.choose(observation(store), store)
    supervisor.choose(observation(store, BLOCK), store)
    assert model.instructions == [MATCHED_EXECUTIVE, VERIFIER, MATCHED_EXECUTIVE]
    assert "every 32 steps" not in MATCHED_EXECUTIVE
    assert "384 control steps (12.8 simulated seconds)" in MATCHED_EXECUTIVE


def test_matched_prefix_cannot_silently_change_a_motor_recipe():
    from experiments.behavior.radio import supervised_prefix

    assert supervised_prefix("behavior-skill") == 32
    assert supervised_prefix("corvid") == 1
    with pytest.raises(ValueError):
        supervised_prefix("unknown")
