from autozuma.assets.registry import load_asset_registry


def test_registry_loads_all_levels():
    registry = load_asset_registry()

    assert len(registry.levels) == 22
    assert "space" in registry.levels
    assert "spiral" in registry.levels


def test_static_levels_have_background_images():
    registry = load_asset_registry()

    for level in registry.levels.values():
        if level.requires_special_detection:
            continue
        assert level.background is not None
        assert level.background.bgr.size > 0
        assert level.background.gray.size > 0
        assert level.background.bgr.shape[:2] == level.background.gray.shape


def test_space_has_geometry_without_static_background():
    registry = load_asset_registry()
    space = registry.levels["space"]

    assert space.requires_special_detection is True
    assert space.background is None
    assert len(space.geometry.tracks) == len(space.topology.tracks)


def test_launcher_template_is_loaded():
    registry = load_asset_registry()
    launcher = registry.templates.launcher_frog

    assert launcher.path.name == "SMALLFROGonPAD.png"
    assert launcher.bgr.size > 0
    assert launcher.gray.size > 0
    assert launcher.bgr.shape[:2] == launcher.gray.shape


def test_ui_templates_are_loaded():
    registry = load_asset_registry()

    assert set(registry.templates.ui) == {"ok", "continue"}
    for template in registry.templates.ui.values():
        assert template.bgr.size > 0
        assert template.gray.size > 0
        assert template.bgr.shape[:2] == template.gray.shape
