#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
command -v node >/dev/null 2>&1 || { echo "FAIL: Node.js 18+ is required for workbench tests" >&2; exit 1; }
for module in "$ROOT"/skills/ci-package-test/assets/workbench/*.mjs; do
  node --check "$module"
done
node --test "$ROOT"/skills/ci-package-test/tests/*.test.mjs
