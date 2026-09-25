import numpy as np
import pytest

from physical_harness.perception.image_quality import assess_rgb_image


def test_image_quality_accepts_bright_structured_current_image():
    image = np.full((40, 40, 3), 220, dtype=np.uint8)
    image[10:30, 10:30] = [180, 20, 20]
    result = assess_rgb_image(image)
    assert result["usable"] is True
    assert result["reasons"] == []


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        (2, "near_black_frame"),
        (255, "near_white_frame"),
        (120, "insufficient_dynamic_range"),
    ],
)
def test_image_quality_rejects_uninformative_frames(value, reason):
    result = assess_rgb_image(np.full((20, 20, 3), value, dtype=np.uint8))
    assert result["usable"] is False
    assert reason in result["reasons"]


def test_image_quality_rejects_invalid_shapes_and_ranges():
    with pytest.raises(ValueError, match="shape"):
        assess_rgb_image(np.zeros((10, 10), dtype=np.uint8))
    with pytest.raises(ValueError, match=r"\[0, 255\]"):
        assess_rgb_image(np.full((10, 10, 3), 300.0))
