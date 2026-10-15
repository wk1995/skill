#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/pr_review_boundaries_test.py"
