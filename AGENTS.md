# Repository Instructions

Scope: the entire repository.

## Quality Bar

Do not ship prototype-level implementations unless the user explicitly asks for a prototype, draft, experiment, or quick validation.

When completing a task, prioritize:

1. Correct behavior.
2. Preserving existing behavior.
3. Reasonable edge-case coverage.
4. Passing existing tests, build checks, and lint where practical.
5. Adding focused tests when behavior changes, or clearly documenting manual verification.
6. Real fixes instead of workarounds.
7. No unfinished TODOs that can be closed within the task scope.

Do not expand the task without bounds. If a complete fix clearly requires a larger redesign, explain the risk and recommended path first.

## Test Policy

The Python tests under `tests/test_*.py` are the active regression suite for the current refactor. Do not delete or weaken them just to make a change pass.

Safe cleanup:

- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- other generated cache artifacts already ignored by `.gitignore`

Before deleting or materially rewriting a test source file, verify all of the following:

- The behavior it covered is genuinely removed or replaced.
- Equivalent coverage exists elsewhere, or new coverage is added in the same change.
- The reason is documented in the change summary.

For normal code changes, prefer targeted tests first, then run the full suite before a broad handoff, release, or commit.

Suggested targeted commands:

```powershell
# Visual recognition / perception
.\.venv\Scripts\python.exe -m pytest tests/test_roi.py tests/test_level_recognition.py tests/test_world_state.py

# Strategy / aiming / swap / coins / discard / static decision
.\.venv\Scripts\python.exe -m pytest tests/test_strategy_targets.py tests/test_target_selection.py tests/test_line_of_sight.py tests/test_strategy_coins.py tests/test_strategy_swap.py tests/test_strategy_discard.py tests/test_static_frame_decision.py

# Runtime orchestration
.\.venv\Scripts\python.exe -m pytest tests/test_runtime_static_runtime.py tests/test_runtime_session.py tests/test_runtime_loop.py

# Full regression suite
.\.venv\Scripts\python.exe -m pytest

# Lint
.\.venv\Scripts\python.exe -m ruff check .
```

Run the full suite when a change touches shared data models, public behavior across modules, runtime execution flow, or multiple test categories.
