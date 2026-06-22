from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MILESTONES = ROOT / "docs" / "reference" / "zorn-showcase-milestones.json"
SCENARIOS = ROOT / "docs" / "manifests" / "zorn-showcase-scenarios.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main() -> None:
    milestones = _load_json(MILESTONES)
    scenarios = _load_json(SCENARIOS)

    capabilities = {
        capability
        for milestone in milestones["milestones"]
        for capability in milestone["capabilities"]
    }
    covered = {
        milestone_id
        for scenario in scenarios["scenarios"]
        for milestone_id in scenario["milestones"]
    }

    print(f"milestones_schema={milestones['schema_version']}")
    print(f"scenarios_schema={scenarios['schema_version']}")
    print(f"milestones={len(milestones['milestones'])}")
    print(f"capabilities={len(capabilities)}")
    print(f"scenarios={len(scenarios['scenarios'])}")
    print("scenario_coverage:")
    for milestone in milestones["milestones"]:
        status = "covered" if milestone["id"] in covered else "planned"
        print(f"- {milestone['id']} {status}: {milestone['name']}")


if __name__ == "__main__":
    main()
