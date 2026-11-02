#!/usr/bin/env python3
"""Machine and repository commit prefixes; also a standalone commit-msg hook."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile


POLICY = ".git-commit-message.json"
DEFAULTS = {
    "schema_version": 1,
    "machine_prefix": False,
    "repo_prefix": True,
    "ai_prefix": True,
    "extra_prefixes": [],
    "mode": "fix",
    "skip_autosquash": True,
}
MACHINE_DEFAULTS = {"schema_version": 1, "extra_prefixes": []}


class PolicyError(Exception):
    """An invalid input; callers must not proceed with the commit."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyError(message)


def git(repo: Path, *args: str, optional: bool = False) -> str | None:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if optional and result.returncode == 1:
        return None
    require(result.returncode == 0,
            f"git {' '.join(args)} failed: {os.fsdecode(result.stderr).strip()}")
    return os.fsdecode(result.stdout).rstrip("\n")


def repository(location: str) -> Path:
    version = git(Path(location), "--version")
    match = re.match(r"git version (\d+)\.(\d+)", version)
    require(match is not None and tuple(map(int, match.groups())) >= (2, 45),
            "Git 2.45+ is required for consistent commentChar/commentString handling")
    root = git(Path(location), "rev-parse", "--show-toplevel")
    return Path(root).resolve()


def regular(path: Path) -> None:
    require(not path.is_symlink() and path.is_file(), f"expected a regular non-symlink file: {path}")
    require(path.stat().st_nlink == 1, f"refusing a hard-linked file: {path}")


def unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate configuration key: {key}")
        result[key] = value
    return result


def token(value: object, name: str) -> str:
    require(isinstance(value, str) and bool(value) and value == value.strip(),
            f"{name} must be a non-empty string without surrounding whitespace")
    require(not any(c in "[]" or not c.isprintable() for c in value),
            f"{name} must not contain brackets or control characters")
    return value


def machine_policy_path() -> Path:
    configured = os.environ.get("XDG_CONFIG_HOME")
    root = Path(configured) if configured else Path.home() / ".config"
    require(root.is_absolute(), "XDG_CONFIG_HOME must be an absolute path")
    return root / "git-commit-message" / "config.json"


def read_policy(path: Path, defaults: dict) -> dict:
    data = {}
    if path.exists() or path.is_symlink():
        regular(path)
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    require(not (set(data) - set(defaults)), f"unknown {path} keys: {set(data) - set(defaults)}")
    result = {**defaults, **data}
    require(type(result["schema_version"]) is int and result["schema_version"] == 1,
            "schema_version must be 1")
    prefixes = result["extra_prefixes"]
    require(isinstance(prefixes, list), "extra_prefixes must be an array")
    for value in prefixes:
        token(value, "extra_prefixes item")
    require(len(prefixes) == len(set(prefixes)), "extra_prefixes must not contain duplicates")
    return result


def policy(repo: Path) -> dict:
    result = read_policy(repo / POLICY, DEFAULTS)
    for key in ("machine_prefix", "repo_prefix", "ai_prefix", "skip_autosquash"):
        require(type(result[key]) is bool, f"{key} must be boolean")
    require(result["mode"] in ("fix", "check"), "mode must be fix or check")
    machine = read_policy(machine_policy_path(), MACHINE_DEFAULTS)
    result["machine_prefixes"] = machine["extra_prefixes"]
    return result


def prefix_parts(config: dict) -> list[str]:
    machine = config["machine_prefixes"] if config["machine_prefix"] else []
    project = config["extra_prefixes"] if config["repo_prefix"] else []
    parts = list(dict.fromkeys([*machine, *project]))
    if config["ai_prefix"]:
        client = os.environ.get("AI_AGENT_CLIENT", "")
        version = os.environ.get("AI_AGENT_CLIENT_VERSION", "")
        model = os.environ.get("AI_AGENT_MODEL", "")
        token(model, "AI_AGENT_MODEL (required when ai_prefix is true)")
        if client:
            token(client, "AI_AGENT_CLIENT")
        if version:
            token(version, "AI_AGENT_CLIENT_VERSION")
        if client:
            parts.append(f"{client} {version}" if version else client)
        parts.append(model)
    require(len(parts) == len(set(parts)), "identity and extra_prefixes must have distinct values")
    return [f"[{part}]" for part in parts]


def comment_prefix(repo: Path) -> str:
    # They are aliases: the last occurrence across all config scopes wins.
    entries = git(repo, "config", "--null", "--get-regexp", r"^core\.comment(char|string)$", optional=True)
    comment = entries.split("\0")[-2].partition("\n")[2] if entries is not None else "#"
    require(bool(comment) and all(c.isprintable() for c in comment),
            "Git comment prefix must be non-empty and printable")
    require(comment != "auto", "core.commentChar=auto is unsupported; select an explicit comment character")
    return comment


def normalized(raw: bytes, repo: Path, config: dict) -> bytes:
    if not any(config[key] for key in ("machine_prefix", "repo_prefix", "ai_prefix")):
        return raw
    text = raw.decode("utf-8")
    require("\x00" not in text, "commit message must not contain NUL")
    lines = text.splitlines(keepends=True)
    comment = comment_prefix(repo)
    subject_index = next((i for i, line in enumerate(lines)
                          if line.strip()), None)
    require(subject_index is not None, "commit message has no subject")
    line = lines[subject_index]
    require(not line.startswith(comment),
            "subject must precede comment lines; Git cleanup modes handle leading comments differently")
    ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
    subject = line[:-len(ending)] if ending else line
    if config["skip_autosquash"] and subject.startswith(("fixup! ", "squash! ", "amend! ")):
        return raw
    parts = prefix_parts(config)
    if not parts:
        return raw
    expected = "".join(parts) + " "
    require(not expected.startswith(comment), "required prefix would be removed by Git's comment cleanup")
    remainder = subject.lstrip()
    # Only consume known tokens. Unknown bracketed content remains part of the subject.
    while True:
        found = next((part for part in parts if remainder.startswith(part)), None)
        if found is None:
            break
        remainder = remainder[len(found):].lstrip()
    require(bool(remainder.strip()) and not remainder.startswith(comment),
            "commit message must include a meaningful subject after prefixes")
    lines[subject_index] = expected + remainder + ending
    return "".join(lines).encode("utf-8")


def atomic_write(path: Path, content: bytes, mode: int, *, replace: bool = True) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".commit-message-", delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
            output.flush()
            os.fchmod(output.fileno(), mode)
        if replace:
            os.replace(temporary, path)
        else:
            # Create exclusively: a hook appearing after validation must never be overwritten.
            os.link(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def process(repo: Path, config: dict, message: Path, mode: str) -> None:
    regular(message)
    # Direct commands may receive any message file, but must not overwrite their policy or executable.
    for protected in (repo / POLICY, machine_policy_path(), Path(__file__)):
        require(not protected.exists() or not message.samefile(protected),
                f"message file aliases a protected input: {protected}")
    raw = message.read_bytes()
    updated = normalized(raw, repo, config)
    if updated == raw:
        return
    require(mode == "fix", "commit message prefix is missing or noncanonical; correct it or use fix")
    atomic_write(message, updated, stat.S_IMODE(message.stat().st_mode))


def default_hook(repo: Path) -> Path:
    custom = git(repo, "config", "--get", "core.hooksPath", optional=True)
    require(custom is None,
            "core.hooksPath is configured; integrate the hook command with the existing hook manager")
    common = Path(git(repo, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = repo / common
    directory = common.resolve() / "hooks"
    require(not directory.is_symlink(), f"refusing a symlink hooks directory: {directory}")
    require(not directory.exists() or directory.is_dir(), f"not a hooks directory: {directory}")
    target = directory / "commit-msg"
    require(not target.is_symlink(), f"refusing a symlink hook: {target}")
    return target


def install(repo: Path, remove: bool = False) -> None:
    target = default_hook(repo)
    payload = Path(__file__).read_bytes()
    if target.exists():
        regular(target)
        require(target.read_bytes() == payload,
                f"existing hook differs; preserved {target}. Integrate manually instead of replacing it")
        if remove:
            target.unlink()
        elif not os.access(target, os.X_OK):
            target.chmod(target.stat().st_mode | 0o111)
        return
    if remove:
        return
    target.parent.mkdir(exist_ok=True)
    atomic_write(target, payload, 0o755, replace=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="target worktree (default: current directory)")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("install", "uninstall"):
        commands.add_parser(name)
    for name in ("hook", "check", "fix"):
        commands.add_parser(name).add_argument("message", type=Path)
    args = parser.parse_args(argv)
    try:
        repo = repository(args.repo)
        config = policy(repo)  # Shared validation precedes every mutation and early success.
        if args.command in ("install", "uninstall"):
            install(repo, remove=args.command == "uninstall")
        else:
            mode = config["mode"] if args.command == "hook" else args.command
            process(repo, config, args.message, mode)
    except (PolicyError, OSError, UnicodeError, ValueError) as error:
        print(f"git-commit-message: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if Path(__file__).name == "commit-msg":
        arguments = ["hook", *arguments]
    sys.exit(main(arguments))
