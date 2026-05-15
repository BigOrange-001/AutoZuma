from types import SimpleNamespace

from autozuma.cli import live_static
from autozuma.runtime.loop import LiveLoopParams


def test_live_static_cli_builds_dry_run_loop_params(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / "strategy.ini"
    config_path.write_text(
        "[STRATEGY]\nvirtual_mouse = 1\nn_fire_cooldown = 0.25\n",
        encoding="utf-8",
    )
    calls = {}

    monkeypatch.setattr(
        live_static,
        "build_live_static_session_context",
        lambda: "context",
    )

    def fake_run_live_loop(**kwargs):
        calls["loop"] = kwargs
        return SimpleNamespace(
            iterations=3,
            state=SimpleNamespace(
                hotkeys=SimpleNamespace(is_armed=False),
                session=SimpleNamespace(level_id="spiral"),
            ),
        )

    monkeypatch.setattr(live_static, "run_live_loop", fake_run_live_loop)

    exit_code = live_static.main(
        [
            "--config",
            str(config_path),
            "--set",
            "r_fire_cooldown=0.4",
            "--window-title",
            "zuma",
            "--fps",
            "12",
            "--max-iterations",
            "3",
            "--map-redetect-interval",
            "2",
            "--level-min-confidence",
            "0.5",
        ]
    )

    assert exit_code == 0
    assert calls["loop"]["context"] == "context"
    assert calls["loop"]["max_iterations"] == 3
    params = calls["loop"]["params"]
    assert isinstance(params, LiveLoopParams)
    assert params.target_fps == 12
    assert params.live.window_title == "zuma"
    assert params.live.use_virtual_mouse is True
    assert params.live.session.map_redetect_interval == 2
    assert params.live.session.level_min_confidence == 0.5
    assert params.live.session.host.execute_commands is False
    assert params.live.session.host.runtime.raw_values["n_fire_cooldown"] == 0.25
    assert params.live.session.host.runtime.raw_values["r_fire_cooldown"] == 0.4
    assert "iterations=3" in capsys.readouterr().out


def test_live_static_cli_can_enable_command_execution_and_override_virtual_mouse(
    monkeypatch,
    tmp_path,
):
    config_path = tmp_path / "strategy.ini"
    config_path.write_text("[STRATEGY]\nvirtual_mouse = 1\n", encoding="utf-8")
    calls = {}

    monkeypatch.setattr(live_static, "build_live_static_session_context", lambda: object())

    def fake_run_live_loop(**kwargs):
        calls["params"] = kwargs["params"]
        return SimpleNamespace(
            iterations=0,
            state=SimpleNamespace(
                hotkeys=SimpleNamespace(is_armed=False),
                session=SimpleNamespace(level_id=None),
            ),
        )

    monkeypatch.setattr(live_static, "run_live_loop", fake_run_live_loop)

    exit_code = live_static.main(
        [
            "--config",
            str(config_path),
            "--no-dry-run",
            "--no-virtual-mouse",
            "--max-iterations",
            "0",
        ]
    )

    assert exit_code == 0
    assert calls["params"].live.session.host.execute_commands is True
    assert calls["params"].live.use_virtual_mouse is False
