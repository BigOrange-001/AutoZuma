import numpy as np
import pytest

from autozuma.assets.registry import load_asset_registry
from autozuma.vision.launcher_templates import (
    DEFAULT_LAUNCHER_SEARCH_RADIUS,
    build_launcher_template_set,
)


def test_builds_default_launcher_template_angles():
    registry = load_asset_registry()

    template_set = build_launcher_template_set(registry.templates.launcher_frog)

    assert template_set.search_radius == DEFAULT_LAUNCHER_SEARCH_RADIUS
    assert template_set.step_degrees == 5
    assert len(template_set.templates) == 72
    assert set(template_set.templates) == set(range(0, 360, 5))


def test_launcher_templates_have_expected_shapes_and_masks():
    registry = load_asset_registry()
    template_set = build_launcher_template_set(registry.templates.launcher_frog)
    expected_shape = (DEFAULT_LAUNCHER_SEARCH_RADIUS * 2, DEFAULT_LAUNCHER_SEARCH_RADIUS * 2)

    for angle, template in template_set.templates.items():
        assert template.angle_degrees == angle
        assert template.gray.shape == expected_shape
        assert template.match_mask.shape == expected_shape
        assert template.sub_mask.shape == expected_shape
        assert np.count_nonzero(template.gray) > 0
        assert np.count_nonzero(template.match_mask) > 0
        assert np.count_nonzero(template.sub_mask) > 0


def test_launcher_template_generation_accepts_custom_radius_and_step():
    registry = load_asset_registry()

    template_set = build_launcher_template_set(
        registry.templates.launcher_frog,
        search_radius=60,
        step_degrees=10,
    )

    assert template_set.search_radius == 60
    assert template_set.step_degrees == 10
    assert set(template_set.templates) == set(range(0, 360, 10))
    assert template_set.templates[0].gray.shape == (120, 120)


def test_launcher_template_generation_rejects_invalid_parameters():
    registry = load_asset_registry()

    with pytest.raises(ValueError, match="search_radius"):
        build_launcher_template_set(registry.templates.launcher_frog, search_radius=0)

    with pytest.raises(ValueError, match="step_degrees"):
        build_launcher_template_set(registry.templates.launcher_frog, step_degrees=7)
