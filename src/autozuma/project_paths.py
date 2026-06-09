"""Project-relative path helpers."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Return the repository root that contains the package source tree."""
    return Path(__file__).resolve().parents[2]


def project_path(*parts: str) -> Path:
    """Return a path under the project root."""
    return project_root().joinpath(*parts)
