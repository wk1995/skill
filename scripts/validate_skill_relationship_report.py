#!/usr/bin/env python3
"""Repository CLI for the portable relationship-report contract validator."""
import runpy
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[1] / "skills/sync-skills/scripts/validate_skill_relationship_report.py"
globals().update({key: value for key, value in runpy.run_path(str(_RUNTIME)).items()
                  if not key.startswith("__")})

if __name__ == "__main__":
    raise SystemExit(main())
