import pytest

from physical_harness.reasoning.context import project_context
from physical_harness.reasoning.context.conservative import ContextProjector
from physical_harness.reasoning.context.rich import RichContextBuilder
from physical_harness.world.state import WorldState


def test_state_profiles_preserve_existing_output(tmp_path):
    world = WorldState(tmp_path / "state.sqlite", episode="profiles")
    try:
        inputs = {"goal": "Find an object", "relevant_entities": (), "image_evidence": []}
        assert project_context("conservative", state=world, **inputs) == ContextProjector(world).build(**inputs)
        rich_inputs = {"goal": "Find an object", "focus_entities": (), "image_evidence": []}
        assert project_context("rich", state=world, **rich_inputs) == RichContextBuilder(world).build(**rich_inputs)
    finally:
        world.close()


def test_compact_profile_preserves_fail_closed_contract():
    with pytest.raises(ValueError, match="explicit facts"):
        project_context("compact", state=object())
    with pytest.raises(TypeError):
        project_context("compact")


@pytest.mark.parametrize("profile", ["unknown", "", "conservative", "rich"])
def test_profiles_never_fall_back(profile):
    with pytest.raises(ValueError):
        project_context(profile)
