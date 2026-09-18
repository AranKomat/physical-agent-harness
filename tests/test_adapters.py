import copy
import json

import pytest

from physical_harness.adapters.behavior import BehaviorAdapter, LegalObservation
from physical_harness.adapters.rtsm import RTSMWorldAdapter
from physical_harness.state import WorldState


def raw(at=0, episode="episode"):
    return dict(
        schema_version=1,
        episode_id=episode,
        observation_id=f"frame-{at}",
        sim_time=at,
        rgb_refs={"head": "sha256:rgb"},
        depth_refs={"head": "sha256:depth"},
        proprioception={"joint_positions": [0.0, 0.1]},
        camera_frames={"head": "head_optical"},
        camera_intrinsics={
            "head": dict(width=640, height=480, fx=500, fy=500, cx=320, cy=240, depth_scale_m=0.001)
        },
    )


def pose(observation):
    return dict(
        method="rgbd_odometry",
        frame="local_map",
        camera="head",
        confidence=0.9,
        evidence_ids=[observation.observation_id],
        transform=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    )


def observation(at=0, episode="episode"):
    value = raw(at, episode)
    value["estimated_pose"] = pose(LegalObservation.from_envelope(value))
    return LegalObservation.from_envelope(value)


class Source:
    def __init__(self):
        self.at = 0
        self.actions = []

    def reset(self):
        return raw()

    def step(self, action):
        self.actions.append(action)
        self.at += 1
        return raw(self.at)


def obj(entity="candle-1", x=1):
    return dict(
        entity_id=entity,
        label="candle",
        position=[x, 0, 1],
        confidence=0.95,
        identity_candidates=[],
    )


def snapshot(at=0, objects=None, relations=None, episode="episode"):
    return dict(
        schema_version=1,
        episode_id=episode,
        observation_id=f"frame-{at}",
        sim_time=at,
        objects=[obj()] if objects is None else objects,
        relations=[] if relations is None else relations,
    )


@pytest.fixture
def world():
    with WorldState(":memory:", "episode") as value:
        yield value


def ingest(adapter, at, objects=None, relations=None):
    adapter.build_request(observation(at))
    assert adapter.ingest_snapshot(snapshot(at, objects, relations), now=at)


def test_behavior_source_codec_logging_and_roundtrip():
    source, logs = Source(), []
    adapter = BehaviorAdapter(
        source,
        episode_id="episode",
        action_bounds=[[-1, 1]],
        action_codec=lambda action: tuple(action),
        pose_estimator=pose,
        logger=logs.append,
    )
    first = adapter.reset()
    first.proprioception["joint_positions"][0] = 999
    assert adapter.current.proprioception["joint_positions"][0] == 0
    second = adapter.step([0.5], source_observation_id="frame-0")
    assert source.actions == [(0.5,)]
    assert second.estimated_pose["evidence_ids"] == ["frame-1"]
    assert LegalObservation.from_envelope(json.loads(json.dumps(logs[1]))).to_envelope() == logs[1]
    with pytest.raises(ValueError):
        adapter.reset()
    with pytest.raises(RuntimeError):
        adapter.score_out_of_band()


@pytest.mark.parametrize(
    "key",
    [
        "score",
        "reward",
        "termination",
        "segmentation",
        "global_pose",
        "target_pose",
        "point_cloud",
        "scene_objects",
        "cam_rel_poses",
    ],
)
def test_privileged_observation_fields_rejected(key):
    value = raw()
    value[key] = {"secret": 123}
    with pytest.raises(ValueError):
        LegalObservation.from_envelope(value)


@pytest.mark.parametrize("section", ["proprioception", "camera_intrinsics"])
def test_nested_privileged_fields_rejected(section):
    value = raw()
    target = value[section] if section == "proprioception" else value[section]["head"]
    target["global_pose"] = [1, 2, 3]
    with pytest.raises(ValueError):
        LegalObservation.from_envelope(value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("fx", 0),
        ("fy", float("nan")),
        ("width", True),
        ("height", -1),
        ("cx", 640),
        ("depth_scale_m", -1),
    ],
)
def test_bad_calibration_rejected(key, value):
    envelope = raw()
    envelope["camera_intrinsics"]["head"][key] = value
    with pytest.raises(ValueError):
        LegalObservation.from_envelope(envelope)


def test_camera_and_proprio_alignment():
    value = raw()
    value["depth_refs"] = {"wrist": "depth"}
    with pytest.raises(ValueError):
        LegalObservation.from_envelope(value)
    value = raw()
    value["proprioception"]["joint_velocities"] = [1]
    with pytest.raises(ValueError):
        LegalObservation.from_envelope(value)


@pytest.mark.parametrize(
    "mutation", ["method", "frame", "evidence", "reflection", "scale", "last_row"]
)
def test_pose_provenance_and_rigidity(mutation):
    envelope = observation().to_envelope()
    estimate = envelope["estimated_pose"]
    if mutation == "method":
        estimate["method"] = "simulator"
    elif mutation == "frame":
        estimate["frame"] = "global"
    elif mutation == "evidence":
        estimate["evidence_ids"] = ["another-frame"]
    elif mutation == "reflection":
        estimate["transform"][0][0] = -1
    elif mutation == "scale":
        estimate["transform"][0][0] = 2
    else:
        estimate["transform"][3][0] = 1
    with pytest.raises(ValueError):
        LegalObservation.from_envelope(envelope)


def test_pose_may_cite_previous_and_current_legal_frames():
    envelope = observation(1).to_envelope()
    envelope["estimated_pose"]["evidence_ids"] = ["frame-0", "frame-1"]
    assert LegalObservation.from_envelope(envelope).estimated_pose["evidence_ids"] == [
        "frame-0",
        "frame-1",
    ]


def test_source_cannot_supply_pose_and_rejected_source_poisoned():
    source = Source()
    source.reset = lambda: observation().to_envelope()
    adapter = BehaviorAdapter(source, episode_id="episode", action_bounds=[[-1, 1]])
    with pytest.raises(ValueError):
        adapter.reset()
    with pytest.raises(ValueError):
        adapter.step([0])
    assert not source.actions


@pytest.mark.parametrize("action", [[2], [float("inf")], [True], [], [0, 0], {"torque": 1}])
def test_invalid_action_never_dispatched(action):
    source = Source()
    adapter = BehaviorAdapter(source, episode_id="episode", action_bounds=[[-1, 1]])
    adapter.reset()
    with pytest.raises(ValueError):
        adapter.step(action)
    assert not source.actions


def test_stale_action_and_episode_observation_rejected():
    source = Source()
    adapter = BehaviorAdapter(source, episode_id="episode", action_bounds=[[-1, 1]])
    adapter.reset()
    with pytest.raises(ValueError):
        adapter.step([0], source_observation_id="old")
    assert not source.actions
    source.step = lambda action: raw(1, "other")
    with pytest.raises(ValueError):
        adapter.step([0])


def test_identity_viewpoint_occlusion_and_move(world):
    adapter = RTSMWorldAdapter(world)
    ingest(adapter, 0, [obj(), obj("candle-2", 2)])
    moving_camera = observation(1).to_envelope()
    moving_camera["estimated_pose"]["transform"][0][3] = 0.5
    adapter.build_request(LegalObservation.from_envelope(moving_camera))
    adapter.ingest_snapshot(snapshot(1, [obj(), obj("candle-2", 2)]), now=1)
    assert json.loads(world.belief("candle-1", "location")["object"])["position"] == [1, 0, 1]
    ingest(adapter, 2, [obj("candle-2", 2)])
    assert world.belief("candle-1", "visibility")["object"] == "not_observed"
    assert world.belief("candle-1", "location")["sim_time"] == 1
    ingest(adapter, 3, [obj(x=4), obj("candle-2", 2)])
    assert json.loads(world.belief("candle-1", "location")["object"])["position"] == [4, 0, 1]
    assert json.loads(world.belief("candle-2", "location")["object"])["position"] == [2, 0, 1]
    history = [row for row in world.history("candle-1") if row["predicate"] == "location"]
    assert history[0]["valid_until"] is not None


def test_stale_out_of_order_expired_and_replayed_replies(world):
    adapter = RTSMWorldAdapter(world, max_age_s=2)
    adapter.build_request(observation(1))
    adapter.build_request(observation(2))
    assert adapter.ingest_snapshot(snapshot(2), now=2)
    assert not adapter.ingest_snapshot(snapshot(1, [obj(x=99)]), now=2)
    with pytest.raises(ValueError):
        adapter.ingest_snapshot(snapshot(2), now=2)
    adapter.build_request(observation(3))
    assert not adapter.ingest_snapshot(snapshot(3), now=6)
    assert world.belief("candle-1", "location")["sim_time"] == 2


def test_unsolicited_cross_episode_and_forged_timestamp(world):
    adapter = RTSMWorldAdapter(world)
    with pytest.raises(ValueError):
        adapter.ingest_snapshot(snapshot(), now=0)
    with pytest.raises(ValueError):
        adapter.build_request(observation(0, "other"))
    adapter.build_request(observation())
    for value in [snapshot(episode="other"), dict(snapshot(), sim_time=1)]:
        with pytest.raises(ValueError):
            adapter.ingest_snapshot(value, now=1)
    assert world.history("candle-1") == []


@pytest.mark.parametrize("section", ["root", "object", "relation"])
def test_snapshot_privileged_fields_rejected_before_writes(world, section):
    adapter = RTSMWorldAdapter(world)
    adapter.build_request(observation())
    value = snapshot(
        relations=[dict(subject="candle-1", predicate="HELD_BY", object="robot", confidence=0.99)]
    )
    target = (
        value if section == "root" else value["objects" if section == "object" else "relations"][0]
    )
    target["gt_segmentation"] = [0]
    with pytest.raises(ValueError):
        adapter.ingest_snapshot(value, now=0)
    assert world.history("candle-1") == []
    assert world.project("test", [], [], max_events=100)["recent_events"] == []


def test_predicate_evidence_freshness_contradiction_and_ambiguity(world):
    clock = [0]
    adapter = RTSMWorldAdapter(world, sim_clock=lambda: clock[0], max_age_s=2)
    relation = dict(subject="candle-1", predicate="HELD_BY", object="robot", confidence=0.99)
    expression = "HELD_BY(candle-1,robot)"
    ingest(adapter, 0, relations=[relation])
    assert len(adapter.predicate_evidence(expression)) == 1
    assert adapter.predicate_confidence(expression) == 0.99
    clock[0] = 3
    assert adapter.predicate_evidence(expression) == ()
    assert adapter.predicate_confidence(expression) is None
    clock[0] = 1
    world.add_evidence("contradiction", 1, "perception", "new-frame")
    world.update("candle-1", "HELD_BY", "nobody", "contradiction")
    assert not adapter.predicate_evidence(expression)
    ambiguous = obj()
    ambiguous["identity_candidates"] = ["candle-2"]
    ingest(adapter, 2, [ambiguous], [relation])
    clock[0] = 2
    assert not adapter.predicate_evidence(expression)
    ingest(adapter, 3, relations=[relation])
    clock[0] = 3
    assert adapter.predicate_evidence(expression)
    ingest(adapter, 4, [])
    assert not adapter.predicate_evidence(expression)
    assert world.belief("candle-1", "HELD_BY")["object"] == "robot"


def test_unbacked_confidence_never_has_evidence_and_bound_setter_rejected(world):
    stub = RTSMWorldAdapter()
    stub.set_predicate_confidence("OPEN(cabinet)", 0.99)
    assert stub.predicate_evidence("OPEN(cabinet)") == ()
    bound = RTSMWorldAdapter(world)
    with pytest.raises(ValueError):
        bound.set_predicate_confidence("OPEN(cabinet)", 0.99)
    ingest(
        bound,
        0,
        relations=[dict(subject="candle-1", predicate="OPEN", object="true", confidence=1)],
    )
    assert bound.predicate_confidence("OPEN(candle-1)") is None


@pytest.mark.parametrize(
    "key,value",
    [
        ("HELD_BY", "nobody"),
        ("visibility", "not_observed"),
        ("identity_candidates", '["candle-2"]'),
    ],
)
def test_same_time_conflict_invalidates_support_until_new_evidence(world, key, value):
    clock = [0]
    adapter = RTSMWorldAdapter(world, sim_clock=lambda: clock[0])
    relation = dict(subject="candle-1", predicate="HELD_BY", object="robot", confidence=0.99)
    expression = "HELD_BY(candle-1,robot)"
    ingest(adapter, 0, relations=[relation])
    assert adapter.predicate_evidence(expression)
    previous = world.belief("candle-1", key)
    world.add_evidence("same-time-conflict", 0, "perception", "conflicting-frame")
    assert not world.update("candle-1", key, value, "same-time-conflict")
    assert world.belief("candle-1", key) == previous
    assert adapter.predicate_evidence(expression) == ()
    assert adapter.predicate_confidence(expression) is None
    ingest(adapter, 1, relations=[relation])
    clock[0] = 1
    assert adapter.predicate_evidence(expression)


def test_source_injection_copy_isolation_and_pending_limit(world):
    calls = []

    def source(request):
        calls.append(copy.deepcopy(request))
        request["observation"]["proprioception"]["joint_positions"][0] = 123
        return snapshot()

    adapter = RTSMWorldAdapter(world, source=source, max_pending=1)
    assert adapter.observe(observation(), now=0)
    assert calls[0]["type"] == "rtsm.observe"
    query = adapter.query({})
    query["snapshot"]["objects"].clear()
    assert adapter.query({})["snapshot"]["objects"]
    adapter.build_request(observation(1))
    with pytest.raises(ValueError):
        adapter.build_request(observation(2))


def test_action_conditioned_containment_persists_as_noncurrent_memory(world):
    clock = [0]
    adapter = RTSMWorldAdapter(world, sim_clock=lambda: clock[0], max_age_s=5)
    cabinet = obj("cabinet-1", 2)
    cabinet["label"] = "cabinet"
    ingest(adapter, 0, [obj(), cabinet])
    prior_evidence = world.belief("candle-1", "visibility")["evidence_id"]
    adapter.begin_relation_transition(
        skill_id="place-1",
        subject="candle-1",
        predicate="IN",
        object_value="cabinet-1",
        before_evidence_ids=(prior_evidence,),
    )
    assert world.belief("candle-1", "IN") is None

    relation = dict(subject="candle-1", predicate="IN", object="cabinet-1", confidence=0.97)
    ingest(adapter, 1, [obj(), cabinet], [relation])
    clock[0] = 1
    current = adapter.relation_memory()[0]
    assert current["expression"] == "IN(candle-1,cabinet-1)"
    assert current["currently_verifiable"]
    assert current["action_provenance"]["skill_id"] == "place-1"
    assert current["action_provenance"]["outcome"] == "matched"
    assert current["action_provenance"]["before_evidence_ids"] == [prior_evidence]

    ingest(adapter, 2, [obj(), cabinet], [relation])
    clock[0] = 2
    assert adapter.relation_memory()[0]["action_provenance"]["skill_id"] == "place-1"

    ingest(adapter, 3, [cabinet], [])
    clock[0] = 3
    retained = adapter.relation_memory()[0]
    assert retained["subject_visibility"] == "not_observed"
    assert retained["epistemic"] == "remembered_from_observation"
    assert not retained["currently_verifiable"]
    assert world.belief("candle-1", "IN")["object"] == "cabinet-1"
    assert adapter.query({})["snapshot"]["relations"] == []
    assert adapter.query({})["relation_memory"] == [retained]


def test_unobserved_expected_relation_never_becomes_state(world):
    adapter = RTSMWorldAdapter(world)
    cabinet = obj("cabinet-1", 2)
    ingest(adapter, 0, [obj(), cabinet])
    adapter.begin_relation_transition(
        skill_id="place-1",
        subject="candle-1",
        predicate="IN",
        object_value="cabinet-1",
    )
    ingest(adapter, 1, [obj(), cabinet], [])
    assert world.belief("candle-1", "IN") is None
    assert adapter.relation_memory() == ()
    assert adapter.cancel_relation_transition("place-1")
    assert not adapter.cancel_relation_transition("place-1")


def test_observed_relation_can_contradict_pending_action_effect(world):
    adapter = RTSMWorldAdapter(world)
    cabinet, shelf = obj("cabinet-1", 2), obj("shelf-1", 3)
    ingest(adapter, 0, [obj(), cabinet, shelf])
    adapter.begin_relation_transition(
        skill_id="place-1",
        subject="candle-1",
        predicate="IN",
        object_value="cabinet-1",
    )
    observed = dict(subject="candle-1", predicate="IN", object="shelf-1", confidence=0.9)
    ingest(adapter, 1, [obj(), cabinet, shelf], [observed])
    memory = adapter.relation_memory()[0]
    assert memory["object"] == "shelf-1"
    assert memory["action_provenance"]["outcome"] == "contradicted"
    assert not adapter.cancel_relation_transition("place-1")


def test_no_pickle_or_nonfinite_envelopes():
    for value in [object(), b"pickle", float("nan")]:
        envelope = raw()
        envelope["proprioception"]["joint_positions"] = [value]
        with pytest.raises(ValueError):
            LegalObservation.from_envelope(envelope)
