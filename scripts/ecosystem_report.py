from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "reference" / "lattice-ecosystem-registry.json"
REQUIREMENTS = ROOT / "docs" / "reference" / "lattice-ecosystem-requirements.json"
MODULES = ROOT / "docs" / "manifests" / "zorn-modules.yaml"


def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    requirements = json.loads(REQUIREMENTS.read_text())
    modules = yaml.safe_load(MODULES.read_text())

    print(f"registry={registry['schema_version']}")
    print(f"requirements={requirements['schema_version']}")
    print(f"modules={modules['schema_version']}")
    print("lanes:")
    for lane in registry["lanes"]:
        print(f"- {lane['module']}: {lane['id']}")
    ####
    print("requirements:")
    for requirement in requirements["requirements"]:
        print(f"- {requirement['id']} {requirement['priority']}")
    ####
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
