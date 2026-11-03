"""Build-input fingerprints and Git origin evidence; no persistent state writes."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


IGNORED = {".git", "dist", "node_modules", "__pycache__", ".pytest_cache", ".DS_Store"}


def input_digest(skill: Path, adapter: Path, sync_id: str) -> str:
    """Include source, overrides, adapter inputs and execute bits, without local policy."""
    digest = hashlib.sha256()
    producer = adapter.parent.parent / "scripts" / "agent_build.py"
    if producer.is_symlink():
        raise ValueError(f"build producer must not be a symbolic link: {producer}")
    producer_bytes = producer.read_bytes() if producer.is_file() else b""
    digest.update(len(producer_bytes).to_bytes(8, "big"))
    digest.update(producer_bytes)
    for label, root in (("skill", skill), ("adapter", adapter)):
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f"build input must be a regular directory: {root}")
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if any(part in IGNORED for part in relative.parts) or path.suffix in {".pyc", ".pyo"}:
                continue
            if label == "skill" and sync_id == "pr-review-loop" and relative.as_posix() == "pr-review-loop.yml":
                continue
            if path.is_symlink():
                raise ValueError(f"build input must not be a symbolic link: {path}")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError(f"unsupported build input: {path}")
            data = path.read_bytes()
            header = json.dumps([label, relative.as_posix(), path.stat().st_mode & 0o111, len(data)]).encode()
            digest.update(len(header).to_bytes(8, "big"))
            digest.update(header)
            digest.update(data)
    return digest.hexdigest()


def git_source(root: Path) -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return os.fsdecode(result.stdout).removesuffix("\n") if result.returncode == 0 else None

    commit = git("rev-parse", "--verify", "HEAD")
    branch = git("symbolic-ref", "--quiet", "--short", "HEAD")
    default = git("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    default = default.removeprefix("origin/") if default else None
    status = git("status", "--porcelain", "--untracked-files=all")
    dirty = bool(status) if status is not None else None
    return {
        "repository_url": git("remote", "get-url", "origin"),
        "commit": commit,
        "branch": branch,
        "default_branch": default,
        "dirty": dirty,
        # A mainline checkout is not, by itself, proof of an official release.
        "channel": "mainline" if commit and default and branch == default and dirty is False else "development" if commit else "unknown",
    }
