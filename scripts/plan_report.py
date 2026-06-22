from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs" / "reference" / "zorn-next-milestone-plan.json"


def load_roadmap() -> dict[str, Any]:
    with ROADMAP.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    ####
    assert isinstance(data, dict)
    return data
####


def main() -> None:
    data = load_roadmap()
    milestones = data["milestones"]
    lanes = data["lanes"]
    backlog = data["backlog"]
    tests = data["acceptance_tests"]
    risks = data["risks"]

    print("Zorn Next Milestone Plan")
    print(f"Sources: {len(data['sources'])}")
    print(f"Lanes: {len(lanes)}")
    print(f"Milestones: {len(milestones)}")
    print(f"Backlog stories: {len(backlog)}")
    print(f"Acceptance tests: {len(tests)}")
    print(f"Risks: {len(risks)}")
    print("\nMilestones:")
    for milestone in milestones:
        print(f"  {milestone['id']}: {milestone['name']} [{milestone['lane']}]")
    ####
####


if __name__ == "__main__":
    main()
####
