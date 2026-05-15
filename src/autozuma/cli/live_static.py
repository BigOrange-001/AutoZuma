"""Command-line entry point for the static live loop."""

from __future__ import annotations

import argparse
from pathlib import Path

from autozuma.runtime.config import load_runtime_values, parse_runtime_overrides
from autozuma.runtime.host import StaticHostFrameParams
from autozuma.runtime.live import LiveStaticSessionParams, build_live_static_session_context
from autozuma.runtime.loop import LiveLoopParams, run_live_loop
from autozuma.runtime.session import StaticSessionParams
from autozuma.runtime.static_runtime import StaticRuntimeFrameParams


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AutoZuma static live loop.")
    parser.add_argument("--config", type=Path, default=None, help="Path to strategy INI file.")
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a runtime parameter; can be supplied multiple times.",
    )
    parser.add_argument("--window-title", default="zuma deluxe", help="Game window title match.")
    parser.add_argument("--fps", type=float, default=10.0, help="Target loop FPS.")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Stop after N iterations; omit to run until interrupted.",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Plan commands without executing mouse input.",
    )
    parser.add_argument(
        "--virtual-mouse",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Use virtual/background mouse messages; defaults to config VIRTUAL_MOUSE.",
    )
    parser.add_argument(
        "--map-redetect-interval",
        type=float,
        default=4.0,
        help="Seconds between static map redetection checks.",
    )
    parser.add_argument(
        "--level-min-confidence",
        type=float,
        default=0.25,
        help="Minimum static level recognition confidence.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        overrides = parse_runtime_overrides(args.overrides)
        raw_values = load_runtime_values(args.config, overrides=overrides)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    use_virtual_mouse = (
        bool(raw_values.get("virtual_mouse", 0.0))
        if args.virtual_mouse is None
        else args.virtual_mouse
    )
    params = _build_loop_params(
        raw_values=raw_values,
        dry_run=args.dry_run,
        use_virtual_mouse=use_virtual_mouse,
        window_title=args.window_title,
        fps=args.fps,
        map_redetect_interval=args.map_redetect_interval,
        level_min_confidence=args.level_min_confidence,
    )

    context = build_live_static_session_context()
    result = run_live_loop(
        context=context,
        params=params,
        max_iterations=args.max_iterations,
    )
    status = "armed" if result.state.hotkeys.is_armed else "safe"
    level = result.state.session.level_id or "none"
    print(f"AutoZuma static live loop stopped: iterations={result.iterations}, state={status}, level={level}")
    return 0


def _build_loop_params(
    *,
    raw_values: dict[str, float],
    dry_run: bool,
    use_virtual_mouse: bool,
    window_title: str,
    fps: float,
    map_redetect_interval: float,
    level_min_confidence: float,
) -> LiveLoopParams:
    return LiveLoopParams(
        live=LiveStaticSessionParams(
            session=StaticSessionParams(
                host=StaticHostFrameParams(
                    runtime=StaticRuntimeFrameParams(raw_values=raw_values),
                    execute_commands=not dry_run,
                ),
                level_min_confidence=level_min_confidence,
                map_redetect_interval=map_redetect_interval,
            ),
            window_title=window_title,
            use_virtual_mouse=use_virtual_mouse,
        ),
        target_fps=fps,
    )


if __name__ == "__main__":
    raise SystemExit(main())
