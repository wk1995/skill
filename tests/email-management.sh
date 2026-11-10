#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
python3 -B -m unittest discover -s "$ROOT/skills/email-management/tests" -p 'test_*.py' -v
