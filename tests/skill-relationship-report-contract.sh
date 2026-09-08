#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCHEMA="$ROOT/skills/sync-skills/references/skill-relationships.schema.json"
VALIDATOR="$ROOT/scripts/validate_skill_relationship_report.py"
FIXTURE="$ROOT/tests/fixtures/skill-relationships/valid.json"
PRD="$ROOT/docs/skill-relationship-report-prd.zh-CN.md"
TECHNICAL_DESIGN="$ROOT/docs/skill-relationship-report-technical-design.zh-CN.md"
TEST_PLAN="$ROOT/docs/skill-relationship-report-test-plan.zh-CN.md"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

for file in "$SCHEMA" "$VALIDATOR" "$FIXTURE" "$PRD" "$TECHNICAL_DESIGN" "$TEST_PLAN"; do
  if [[ ! -f "$file" ]]; then
    fail "missing relationship report contract file: $file"
  fi
done

grep -Fq 'skill-relationship-report-technical-design.zh-CN.md' "$PRD" || fail "PRD does not link the technical design"
grep -Fq 'skill-relationship-report-test-plan.zh-CN.md' "$PRD" || fail "PRD does not link the test plan"
grep -Fq 'schemas/skill-relationships.schema.json' "$ROOT/README.md" || fail "README does not link the report schema"
grep -Fq 'schemas/skill-relationships.schema.json' "$ROOT/README.zh-CN.md" || fail "Chinese README does not link the report schema"

PYTHONDONTWRITEBYTECODE=1 python3 "$VALIDATOR" "$FIXTURE"

PYTHONDONTWRITEBYTECODE=1 python3 - "$SCHEMA" "$VALIDATOR" "$FIXTURE" <<'PY'
import copy
import importlib.util
import json
import sys
from pathlib import Path

schema_path = Path(sys.argv[1])
validator_path = Path(sys.argv[2])
fixture_path = Path(sys.argv[3])

spec = importlib.util.spec_from_file_location("relationship_report_validator", validator_path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

schema = json.loads(schema_path.read_text(encoding="utf-8"))
fixture = json.loads(fixture_path.read_text(encoding="utf-8"))


def resolve_local_ref(document, reference):
    assert reference.startswith("#/"), f"only local schema refs are allowed: {reference}"
    value = document
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        value = value[part]
    return value


def assert_refs_resolve(value):
    if isinstance(value, dict):
        if "$ref" in value:
            resolve_local_ref(schema, value["$ref"])
        for child in value.values():
            assert_refs_resolve(child)
    elif isinstance(value, list):
        for child in value:
            assert_refs_resolve(child)


assert_refs_resolve(schema)
assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
assert schema["properties"]["schema_version"]["const"] == 1
agent_builds_schema = schema["$defs"]["logicalSkill"]["properties"]["agent_builds"]
assert agent_builds_schema["additionalProperties"]["$ref"] == "#/$defs/agentBuild"
assert "properties" not in agent_builds_schema, "Builder columns must not be a fixed Agent enumeration"
assert "missing-sync-id" in schema["$defs"]["status"]["enum"]
assert schema["$defs"]["localInstall"]["allOf"], "missing sync_id must have a structural condition"


def expect_valid(name, report):
    try:
        module.validate_report(report, schema_path)
    except module.ContractError as error:
        raise AssertionError(f"{name} should be valid, got: {error}") from error


def expect_invalid(name, report, fragment):
    try:
        module.validate_report(report, schema_path)
    except module.ContractError as error:
        if fragment not in str(error):
            raise AssertionError(f"{name} failed for the wrong reason: {error}") from error
    else:
        raise AssertionError(f"{name} should be rejected")


expect_valid("baseline", copy.deepcopy(fixture))

unresolved_root = copy.deepcopy(fixture)
unresolved_root["agent_builders"][1]["local_skill_roots"] = [
    {"resolver": "env:WORKBUDDY_SKILLS_ROOT", "status": "unresolved-root", "source": "adapter"}
]
workbuddy_source = next(
    source
    for source in unresolved_root["scan_sources"]
    if source["kind"] == "local" and source["id"] == "workbuddy"
)
del workbuddy_source["path"]
workbuddy_source["resolver"] = "env:WORKBUDDY_SKILLS_ROOT"
workbuddy_source["status"] = "unresolved-root"
expect_valid("unresolved optional Builder root", unresolved_root)

missing_portable = copy.deepcopy(fixture)
missing_delta = missing_portable["skills"][2]
missing_delta["portable"] = {
    "present": False,
    "project_id": "personal-skills",
    "path": "/projects/skill/skills/delta",
}
missing_delta["statuses"] = ["agent-build-missing", "missing-copy"]
missing_portable["summary"]["current_project_skill_count"] = 3
expect_valid("registered missing portable source", missing_portable)

external_location = copy.deepcopy(fixture)
external_location["skills"][0]["locations"].append(
    {
        "location_id": "external:upstream",
        "kind": "external",
        "path": "/sources/upstream/alpha",
        "source_id": "upstream",
        "core_version": "1.0.0",
        "digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }
)
external_location["skills"][0]["locations"].sort(key=lambda item: item["location_id"])
expect_valid("explicit external location", external_location)

# Different output digests across Agents are expected adapter output, not portable divergence.
alpha = fixture["skills"][0]
assert alpha["agent_builds"]["codex"]["output_digest"] != alpha["agent_builds"]["workbuddy"]["output_digest"]
assert alpha["statuses"] == ["synced"]

# Adding a future Builder requires data only; the contract and validator have no fixed Agent list.
future = copy.deepcopy(fixture)
future["agent_builders"].append(
    {
        "id": "zcode",
        "adapter_version": "1.0.0",
        "artifact_version": "0.1.0",
        "adapter_manifest": "/projects/skill/platforms/zcode/adapter.json",
        "local_skill_roots": [
            {"resolver": "home-relative:.zcode/skills", "path": "/Users/example/.zcode/skills", "status": "resolved", "source": "adapter"}
        ],
    }
)
for skill in future["skills"]:
    portable = skill["portable"]
    if skill["sync_id"] in {"beta", "delta"}:
        zcode_build = {"present": False, "sync_id": skill["sync_id"], "agent_id": "zcode"}
    else:
        zcode_build = {
            "present": True,
            "sync_id": skill["sync_id"],
            "agent_id": "zcode",
            "build_id": "build:zcode",
            "core_version": portable["core_version"],
            "portable_digest": portable["digest"],
            "adapter_version": "1.0.0",
            "artifact_version": "0.1.0",
            "output_digest": "7777777777777777777777777777777777777777777777777777777777777777",
            "path": f"/projects/skill/dist/zcode/{skill['name']}",
            "manifest_path": "/projects/skill/dist/zcode/.agent-build.json",
        }
    skill["agent_builds"]["zcode"] = zcode_build
future["scan_sources"].append(
    {"kind": "adapter", "id": "zcode", "path": "/projects/skill/platforms/zcode/adapter.json", "status": "scanned", "skill_count": 0}
)
future["scan_sources"].append(
    {"kind": "agent-build", "id": "zcode", "path": "/projects/skill/dist/zcode", "status": "scanned", "skill_count": 2}
)
future["scan_sources"].append(
    {"kind": "local", "id": "zcode", "path": "/Users/example/.zcode/skills", "status": "scanned", "skill_count": 0}
)
future["scan_sources"].sort(key=lambda item: (item["kind"], item["id"], item["path"]))
expect_valid("future Builder", future)

duplicate_builder = copy.deepcopy(fixture)
duplicate_builder["agent_builders"].append(copy.deepcopy(duplicate_builder["agent_builders"][-1]))
expect_invalid("duplicate Builder", duplicate_builder, "must be unique and sorted")

no_builder = copy.deepcopy(fixture)
no_builder["agent_builders"] = []
expect_invalid("missing supported Builder declaration", no_builder, "must declare at least one supported Builder")

unknown_builder = copy.deepcopy(fixture)
unknown_builder["skills"][0]["agent_builds"]["zcode"] = {
    "present": False,
    "sync_id": "alpha",
    "agent_id": "zcode",
}
expect_invalid("undeclared Builder reference", unknown_builder, "unknown fields: zcode")

wrong_build_identity = copy.deepcopy(fixture)
wrong_build_identity["skills"][0]["agent_builds"]["codex"]["sync_id"] = "not-alpha"
expect_invalid("build sync identity", wrong_build_identity, "must match the logical Skill sync_id")

wrong_derivation = copy.deepcopy(fixture)
wrong_derivation["skills"][0]["local_installs"][0]["derived_from"] = "build:workbuddy"
expect_invalid("cross-Agent install derivation", wrong_derivation, "must reference the build for the same Agent")

missing_identity_marked_synced = copy.deepcopy(fixture)
missing_identity_marked_synced["skills"][3]["statuses"] = ["synced"]
expect_invalid("missing sync_id marked synced", missing_identity_marked_synced, "cannot be synced")

missing_install_status = copy.deepcopy(fixture)
missing_install_status["skills"][3]["local_installs"][0]["statuses"] = ["agent-install-diverged"]
expect_invalid("missing sync_id without local status", missing_install_status, "must contain missing-sync-id")

unreported_version_divergence = copy.deepcopy(fixture)
unreported_version_divergence["skills"][3]["statuses"].remove("agent-version-diverged")
expect_invalid("unreported Builder version divergence", unreported_version_divergence, "must contain agent-version-diverged")

unreported_partial_coverage = copy.deepcopy(fixture)
unreported_partial_coverage["skills"][1]["statuses"] = ["project-only"]
expect_invalid("unreported partial coverage", unreported_partial_coverage, "must contain agent-build-partial")

relative_path = copy.deepcopy(fixture)
relative_path["project"]["root"] = "projects/skill"
expect_invalid("relative path", relative_path, "must be a normalized absolute path")

unstable_order = copy.deepcopy(fixture)
unstable_order["skills"] = list(reversed(unstable_order["skills"]))
expect_invalid("unstable Skill order", unstable_order, "must be unique and sorted")

wrong_summary = copy.deepcopy(fixture)
wrong_summary["summary"]["build_partial_count"] = 99
expect_invalid("non-derived summary", wrong_summary, "must equal derived value 1")

unknown_top_level = copy.deepcopy(fixture)
unknown_top_level["machine_username"] = "must-not-be-added"
expect_invalid("unknown top-level field", unknown_top_level, "unknown fields: machine_username")

# The root schema is a compatibility reference to the distributed vocabulary.
root = validator_path.parent.parent
module.validate_report(copy.deepcopy(fixture), root / "schemas/skill-relationships.schema.json")
for name in ("README.md", "README.zh-CN.md", "SKILL.md"):
    text = (root / "skills/sync-skills" / name).read_text()
    assert "Draft 2020-12" in text and "scripts/validate_skill_relationship_report.py" in text
    assert "informative" in text or "互操作文档" in text
print("PASS: Skill relationship report structural and semantic contract")
PY
