from autozuma.assets.paths import default_asset_paths
from autozuma.assets.validator import validate_assets


def test_migrated_assets_validate_successfully():
    report = validate_assets(default_asset_paths())

    assert report.ok is True
    assert report.errors == ()


def test_asset_counts_match_migration_baseline():
    report = validate_assets(default_asset_paths())

    assert report.background_count == 21
    assert report.topology_count == 22
    assert len(report.level_refs) == 22


def test_space_without_static_background_is_allowed():
    report = validate_assets(default_asset_paths())
    space_refs = [ref for ref in report.level_refs if ref.level_id.lower() == "space"]

    assert len(space_refs) == 1
    assert space_refs[0].background_path is None
    assert space_refs[0].requires_special_detection is True
    assert any(issue.code == "special_detection_no_background" for issue in report.notes)


def test_static_levels_have_matching_backgrounds():
    report = validate_assets(default_asset_paths())

    for ref in report.level_refs:
        if ref.requires_special_detection:
            continue
        assert ref.background_path is not None


def test_required_templates_exist():
    paths = default_asset_paths()

    assert (paths.launcher_templates / "SMALLFROGonPAD.png").exists()
    assert (paths.ui_templates / "ui_ok.png").exists()
    assert (paths.ui_templates / "ui_continue.png").exists()
