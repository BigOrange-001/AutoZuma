"""CLI entry point for asset validation."""

from __future__ import annotations

from autozuma.assets.paths import default_asset_paths
from autozuma.assets.validator import AssetValidationIssue, validate_assets


def main() -> int:
    report = validate_assets(default_asset_paths())

    status = "passed" if report.ok else "failed"
    print(f"Asset validation {status}.")
    print(f"Backgrounds: {report.background_count}")
    print(f"Topologies: {report.topology_count}")
    print(f"Levels: {len(report.level_refs)}")

    if report.issues:
        print("")
        print("Issues:")
        for issue in report.issues:
            print(_format_issue(issue))

    return 0 if report.ok else 1


def _format_issue(issue: AssetValidationIssue) -> str:
    location = f" ({issue.path})" if issue.path else ""
    return f"- [{issue.severity}] {issue.code}: {issue.message}{location}"


if __name__ == "__main__":
    raise SystemExit(main())
