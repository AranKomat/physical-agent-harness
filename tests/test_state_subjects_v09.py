from physical_harness.state import WorldState


def test_world_state_subjects_returns_current_subject_roster(tmp_path):
    with WorldState(tmp_path / "world.sqlite", "ep") as state:
        state.add_evidence("e1", 1.0, "perception", "a.png")
        state.update("ball_1", "label", "tennis ball", "e1")
        state.update("ball_2", "visibility", "visible", "e1")
        assert state.subjects() == ("ball_1", "ball_2")
