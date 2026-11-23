#!/usr/bin/env python3
"""Behavioral contract for git-repo-sync through the public CLI and real Git."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skills/git-repo-sync/scripts/repo_sync.py"
GIT = shutil.which("git")
assert GIT, "git must be available on PATH"

spec = importlib.util.spec_from_file_location("repo_sync", TOOL)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules["repo_sync"] = module
spec.loader.exec_module(module)


class Fixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.origin = root / "origin.git"
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(
            {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_AUTHOR_NAME": "Repo Sync Test",
                "GIT_AUTHOR_EMAIL": "repo-sync@example.invalid",
                "GIT_COMMITTER_NAME": "Repo Sync Test",
                "GIT_COMMITTER_EMAIL": "repo-sync@example.invalid",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        self.git_run(root, "init", "--quiet", "--bare", "--initial-branch=main", str(self.origin))
        self.a = self.clone("device-a")
        self.write(self.a, "f.txt", "base\n")
        self.git_run(self.a, "add", "f.txt")
        self.commit(self.a, "base")
        self.push(self.a, "main")
        self.b = self.clone("device-b")

    def git_run(
        self,
        cwd: Path,
        *args: str,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [GIT, "-C", str(cwd), *args],
            env=self.env if env is None else env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if check and result.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
        return result

    def clone(self, name: str) -> Path:
        target = self.root / name
        subprocess.run(
            [GIT, "clone", "--quiet", str(self.origin), str(target)],
            env=self.env,
            check=True,
            capture_output=True,
        )
        self.git_run(target, "config", "user.name", "Repo Sync Test")
        self.git_run(target, "config", "user.email", "repo-sync@example.invalid")
        self.git_run(target, "config", "core.autocrlf", "false")
        self.git_run(target, "config", "commit.gpgsign", "false")
        return target

    def write(self, repo: Path, name: str, content: str) -> None:
        path = repo / name
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def commit(self, repo: Path, message: str, *, date: str | None = None) -> str:
        env = self.env if date is None else {**self.env, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        self.git_run(repo, "commit", "--quiet", "-m", message, env=env)
        return self.git_run(repo, "rev-parse", "HEAD").stdout.strip()

    def push(self, repo: Path, branch: str, *, force: bool = False) -> None:
        args = ["push", "--quiet"]
        if force:
            args.append("--force")
        self.git_run(repo, *args, "origin", branch)

    def switch(self, repo: Path, branch: str, *, create: bool = False, start: str = "main") -> None:
        args = ["switch", "--quiet"]
        if create:
            args += ["-c", branch, start]
        else:
            args.append(branch)
        self.git_run(repo, *args)

    def branch(self, repo: Path, name: str, start: str) -> None:
        self.git_run(repo, "branch", name, start)

    def sha(self, repo: Path, ref: str) -> str:
        return self.git_run(repo, "rev-parse", ref).stdout.strip()

    def remote_heads(self) -> dict[str, str]:
        result = self.git_run(self.b, "ls-remote", "--heads", "origin")
        heads: dict[str, str] = {}
        for line in result.stdout.splitlines():
            sha, _, ref = line.partition("\t")
            if ref.startswith("refs/heads/"):
                heads[ref[len("refs/heads/"):]] = sha
        return heads

    def tool(
        self,
        repo: Path,
        command: str,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOL), command, "--repo", str(repo), *args],
            env=self.env if env is None else env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def tool_json(self, repo: Path, command: str, *args: str) -> dict:
        result = self.tool(repo, command, *args, "--json")
        self.assert_exit(result, 0)
        return json.loads(result.stdout)

    @staticmethod
    def assert_exit(result: subprocess.CompletedProcess[str], expected: int) -> None:
        if result.returncode != expected:
            raise AssertionError(
                f"expected exit {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )

    def create_remote_branch(self, name: str, *, file: str | None = None, content: str = "") -> str:
        self.switch(self.a, name, create=True, start="main")
        if file:
            self.write(self.a, file, content)
            self.git_run(self.a, "add", file)
            self.commit(self.a, f"{name} commit")
        self.push(self.a, name)
        self.switch(self.a, "main")
        return self.sha(self.a, name)

    def fetch(self, repo: Path) -> None:
        self.git_run(repo, "fetch", "--quiet", "origin")


class RepoSyncCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="repo-sync-", ignore_cleanup_errors=True)
        self.addCleanup(self.temporary.cleanup)
        self.fx = Fixture(Path(self.temporary.name))

    def test_clean_clone_has_no_findings(self) -> None:
        result = self.fx.tool(self.fx.b, "audit", "--json")
        self.fx.assert_exit(result, 0)
        snapshot = json.loads(result.stdout)
        self.assertEqual(snapshot["schema"], 1)
        self.assertEqual(snapshot["repo"]["default_branch"], "main")
        self.assertEqual(snapshot["summary"]["local_branches"], 1)
        self.assertEqual(snapshot["summary"]["remote_branches"], 1)
        self.assertEqual(snapshot["findings"], [])
        self.fx.assert_exit(self.fx.tool(self.fx.b, "audit", "--strict"), 0)

    def test_behind_branch_is_fast_forwarded_and_idempotent(self) -> None:
        self.fx.write(self.fx.a, "next.txt", "next\n")
        self.fx.git_run(self.fx.a, "add", "next.txt")
        self.fx.commit(self.fx.a, "next")
        self.fx.push(self.fx.a, "main")

        before = self.fx.tool_json(self.fx.b, "audit")
        main = next(item for item in before["local_branches"] if item["name"] == "main")
        self.assertEqual(main["status"], "behind")
        self.assertEqual(main["behind"], 1)

        first = self.fx.tool(self.fx.b, "sync", "--apply")
        self.fx.assert_exit(first, 0)
        self.assertEqual(self.fx.sha(self.fx.b, "main"), self.fx.remote_heads()["main"])

        second = self.fx.tool(self.fx.b, "sync", "--apply", "--json")
        self.fx.assert_exit(second, 0)
        self.assertEqual(json.loads(second.stdout)["actions"], [])

    def test_non_current_branch_fast_forwards_without_checkout(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        self.fx.switch(self.fx.a, "topic")
        self.fx.write(self.fx.a, "next.txt", "next\n")
        self.fx.git_run(self.fx.a, "add", "next.txt")
        self.fx.commit(self.fx.a, "next")
        self.fx.push(self.fx.a, "topic")
        self.fx.switch(self.fx.a, "main")
        head_before = self.fx.sha(self.fx.b, "HEAD")

        result = self.fx.tool(self.fx.b, "sync", "--apply", "--json")
        self.fx.assert_exit(result, 0)
        payload = json.loads(result.stdout)
        self.assertEqual([item["branch"] for item in payload["actions"]], ["topic"])
        self.assertEqual(payload["actions"][0]["method"], "update-ref")
        self.assertEqual(self.fx.sha(self.fx.b, "topic"), self.fx.remote_heads()["topic"])
        self.assertEqual(self.fx.sha(self.fx.b, "HEAD"), head_before)

    def test_sync_skips_branch_checked_out_in_another_worktree(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        worktree_path = self.fx.root / "wt-sync"
        self.fx.git_run(
            self.fx.b, "worktree", "add", "--quiet", str(worktree_path), "topic"
        )
        self.addCleanup(
            lambda: self.fx.git_run(
                self.fx.b, "worktree", "remove", "--force", str(worktree_path), check=False
            )
        )
        before = self.fx.sha(self.fx.b, "topic")

        self.fx.switch(self.fx.a, "topic")
        self.fx.write(self.fx.a, "remote.txt", "remote\n")
        self.fx.git_run(self.fx.a, "add", "remote.txt")
        self.fx.commit(self.fx.a, "remote")
        self.fx.push(self.fx.a, "topic")
        self.fx.switch(self.fx.a, "main")

        result = self.fx.tool(self.fx.b, "sync", "--apply", "--json")
        self.fx.assert_exit(result, 0)
        actions = json.loads(result.stdout)["actions"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["status"], "skipped")
        self.assertIn("checked out in", actions[0]["reason"])
        self.assertEqual(self.fx.sha(self.fx.b, "topic"), before)

    def test_diverged_branch_is_not_rewritten_without_flag(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        self.fx.switch(self.fx.b, "topic")
        self.fx.write(self.fx.b, "local.txt", "local\n")
        self.fx.git_run(self.fx.b, "add", "local.txt")
        local_sha = self.fx.commit(self.fx.b, "local work")

        self.fx.switch(self.fx.a, "topic")
        self.fx.write(self.fx.a, "remote.txt", "remote\n")
        self.fx.git_run(self.fx.a, "add", "remote.txt")
        self.fx.commit(self.fx.a, "remote work")
        self.fx.push(self.fx.a, "topic")

        snapshot = self.fx.tool_json(self.fx.b, "audit")
        topic = next(item for item in snapshot["local_branches"] if item["name"] == "topic")
        self.assertEqual(topic["status"], "diverged")
        self.assertEqual((topic["ahead"], topic["behind"]), (1, 1))

        result = self.fx.tool(self.fx.b, "sync", "--apply")
        self.fx.assert_exit(result, 2)
        self.assertEqual(self.fx.sha(self.fx.b, "topic"), local_sha)
        self.assertEqual(self.fx.remote_heads()["topic"], self.fx.sha(self.fx.a, "topic"))

    def test_rebase_current_replays_and_archives(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        self.fx.switch(self.fx.b, "topic")
        self.fx.write(self.fx.b, "local.txt", "local\n")
        self.fx.git_run(self.fx.b, "add", "local.txt")
        old_sha = self.fx.commit(self.fx.b, "local work")
        self.fx.switch(self.fx.a, "topic")
        self.fx.write(self.fx.a, "remote.txt", "remote\n")
        self.fx.git_run(self.fx.a, "add", "remote.txt")
        self.fx.commit(self.fx.a, "remote work")
        self.fx.push(self.fx.a, "topic")

        result = self.fx.tool(self.fx.b, "sync", "--apply", "--rebase-current")
        self.fx.assert_exit(result, 0)
        self.assertEqual(self.fx.sha(self.fx.b, "origin/topic"), self.fx.remote_heads()["topic"])
        self.assertEqual(self.fx.sha(self.fx.b, "topic^"), self.fx.sha(self.fx.b, "origin/topic"))
        archive = f"refs/repo-sync/archive/topic/{old_sha}"
        self.assertEqual(self.fx.sha(self.fx.b, archive), old_sha)

    def test_rebase_conflict_aborts_and_restores(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        self.fx.switch(self.fx.b, "topic")
        self.fx.write(self.fx.b, "f.txt", "local change\n")
        self.fx.git_run(self.fx.b, "add", "f.txt")
        old_sha = self.fx.commit(self.fx.b, "local change")

        self.fx.switch(self.fx.a, "topic")
        self.fx.write(self.fx.a, "f.txt", "remote change\n")
        self.fx.git_run(self.fx.a, "add", "f.txt")
        self.fx.commit(self.fx.a, "remote change")
        self.fx.push(self.fx.a, "topic")

        result = self.fx.tool(self.fx.b, "sync", "--apply", "--rebase-current")
        self.fx.assert_exit(result, 2)
        self.assertEqual(self.fx.sha(self.fx.b, "topic"), old_sha)
        self.assertEqual(self.fx.git_run(self.fx.b, "status", "--porcelain").stdout, "")
        self.assertFalse((self.fx.b / ".git/rebase-merge").exists())
        self.assertFalse((self.fx.b / ".git/rebase-apply").exists())
        self.assertIn("conflicted and was aborted", result.stderr + result.stdout)
        self.assertEqual(
            self.fx.sha(self.fx.b, f"refs/repo-sync/archive/topic/{old_sha}"), old_sha
        )

    def test_tracked_changes_block_fast_forward(self) -> None:
        self.fx.write(self.fx.a, "next.txt", "next\n")
        self.fx.git_run(self.fx.a, "add", "next.txt")
        self.fx.commit(self.fx.a, "next")
        self.fx.push(self.fx.a, "main")
        self.fx.write(self.fx.b, "f.txt", "local edit\n")
        head = self.fx.sha(self.fx.b, "HEAD")

        result = self.fx.tool(self.fx.b, "sync", "--apply")
        self.fx.assert_exit(result, 2)
        self.assertEqual(self.fx.sha(self.fx.b, "HEAD"), head)
        self.assertEqual((self.fx.b / "f.txt").read_text(encoding="utf-8"), "local edit\n")

    def test_untracked_only_allows_fast_forward(self) -> None:
        self.fx.write(self.fx.a, "next.txt", "next\n")
        self.fx.git_run(self.fx.a, "add", "next.txt")
        self.fx.commit(self.fx.a, "next")
        self.fx.push(self.fx.a, "main")
        self.fx.write(self.fx.b, "scratch.txt", "keep\n")

        result = self.fx.tool(self.fx.b, "sync", "--apply")
        self.fx.assert_exit(result, 0)
        self.assertEqual(self.fx.sha(self.fx.b, "main"), self.fx.remote_heads()["main"])
        self.assertEqual((self.fx.b / "scratch.txt").read_text(encoding="utf-8"), "keep\n")

    def test_untracked_file_that_blocks_fast_forward_is_preserved(self) -> None:
        """An untracked file on the fast-forward path cannot be preserved silently.

        Git refuses the merge when the upstream commit adds the same path, so the
        documented rule is that the run fails with the file and the tip intact,
        not that the fast-forward succeeds.
        """
        old_sha = self.fx.sha(self.fx.b, "main")
        self.fx.write(self.fx.a, "clash.txt", "upstream\n")
        self.fx.git_run(self.fx.a, "add", "clash.txt")
        self.fx.commit(self.fx.a, "upstream adds clash.txt")
        self.fx.push(self.fx.a, "main")
        self.fx.write(self.fx.b, "clash.txt", "mine\n")

        result = self.fx.tool(self.fx.b, "sync", "--apply")
        self.fx.assert_exit(result, 2)
        self.assertEqual(self.fx.sha(self.fx.b, "main"), old_sha)
        self.assertEqual((self.fx.b / "clash.txt").read_text(encoding="utf-8"), "mine\n")
        self.assertIn("FAILED", result.stdout)

    def test_rewritten_upstream_is_detected_and_reset(self) -> None:
        self.fx.create_remote_branch("topic", file="topic.txt", content="topic\n")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        old_sha = self.fx.sha(self.fx.b, "topic")

        self.fx.switch(self.fx.a, "topic")
        self.fx.git_run(self.fx.a, "commit", "--quiet", "--amend", "-m", "topic reworded")
        self.fx.push(self.fx.a, "topic", force=True)

        snapshot = self.fx.tool_json(self.fx.b, "audit")
        topic = next(item for item in snapshot["local_branches"] if item["name"] == "topic")
        self.assertEqual(topic["status"], "rewritten-upstream")
        self.assertEqual(topic["unique_patches"], 0)

        blocked = self.fx.tool(self.fx.b, "sync", "--apply")
        self.fx.assert_exit(blocked, 2)
        self.assertEqual(self.fx.sha(self.fx.b, "topic"), old_sha)

        reset = self.fx.tool(self.fx.b, "sync", "--apply", "--reset-rewritten")
        self.fx.assert_exit(reset, 0)
        self.assertEqual(self.fx.sha(self.fx.b, "topic"), self.fx.remote_heads()["topic"])
        self.assertEqual(
            self.fx.sha(self.fx.b, f"refs/repo-sync/archive/topic/{old_sha}"), old_sha
        )

    def test_rebase_blocked_before_start_leaves_branch_intact(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        self.fx.switch(self.fx.b, "topic")
        self.fx.write(self.fx.b, "local.txt", "local\n")
        self.fx.git_run(self.fx.b, "add", "local.txt")
        old_sha = self.fx.commit(self.fx.b, "local work")

        self.fx.switch(self.fx.a, "topic")
        self.fx.write(self.fx.a, "extra.txt", "remote adds this file\n")
        self.fx.git_run(self.fx.a, "add", "extra.txt")
        self.fx.commit(self.fx.a, "remote adds extra")
        self.fx.push(self.fx.a, "topic")

        # An untracked file at the same path makes git refuse before rebasing.
        self.fx.write(self.fx.b, "extra.txt", "untracked local copy\n")

        result = self.fx.tool(self.fx.b, "sync", "--apply", "--rebase-current")
        self.fx.assert_exit(result, 2)
        self.assertEqual(self.fx.sha(self.fx.b, "topic"), old_sha)
        self.assertFalse((self.fx.b / ".git/rebase-merge").exists())
        self.assertFalse((self.fx.b / ".git/rebase-apply").exists())
        combined = result.stdout + result.stderr
        self.assertNotIn("resolve the rebase", combined)
        self.assertIn("nothing to abort", combined)
        self.assertEqual(
            (self.fx.b / "extra.txt").read_text(encoding="utf-8"), "untracked local copy\n"
        )

    def test_squash_merged_remote_branch_is_deleted_with_archive(self) -> None:
        self.fx.create_remote_branch("squashed", file="squashed.txt", content="squashed\n")
        topic_sha = self.fx.sha(self.fx.a, "squashed")
        self.fx.switch(self.fx.a, "main")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--squash", "squashed")
        self.fx.commit(self.fx.a, "squash merge")
        self.fx.push(self.fx.a, "main")

        snapshot = self.fx.tool_json(self.fx.b, "audit")
        remote = next(item for item in snapshot["remote_branches"] if item["name"] == "squashed")
        self.assertTrue(remote["merged"])
        self.assertEqual(remote["merge_state"], "noop")

        result = self.fx.tool(self.fx.b, "prune", "--target", "remote", "--apply")
        self.fx.assert_exit(result, 0)
        self.assertNotIn("squashed", self.fx.remote_heads())
        self.assertEqual(
            self.fx.sha(self.fx.b, f"refs/repo-sync/archive/squashed/{topic_sha}"), topic_sha
        )
        tracking = self.fx.git_run(
            self.fx.b, "show-ref", "--verify", "--quiet", "refs/remotes/origin/squashed", check=False
        )
        self.assertNotEqual(tracking.returncode, 0)
        again = self.fx.tool(self.fx.b, "prune", "--target", "remote", "--apply", "--json")
        self.fx.assert_exit(again, 0)
        self.assertEqual(json.loads(again.stdout)["deleted"], [])

    def test_reverted_squash_branch_is_not_deleted(self) -> None:
        self.fx.create_remote_branch("reverted", file="reverted.txt", content="reverted\n")
        self.fx.switch(self.fx.a, "main")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--squash", "reverted")
        squash = self.fx.commit(self.fx.a, "squash merge")
        self.fx.git_run(self.fx.a, "revert", "--no-edit", squash)
        self.fx.push(self.fx.a, "main")

        snapshot = self.fx.tool_json(self.fx.b, "audit")
        remote = next(item for item in snapshot["remote_branches"] if item["name"] == "reverted")
        self.assertFalse(remote["merged"])
        self.assertEqual(remote["merge_state"], "changes")

        result = self.fx.tool(self.fx.b, "prune", "--target", "remote", "--apply", "--json")
        self.fx.assert_exit(result, 0)
        self.assertEqual(json.loads(result.stdout)["deleted"], [])
        self.assertIn("reverted", self.fx.remote_heads())

    def test_local_prune_archives_and_restore_recreates(self) -> None:
        self.fx.create_remote_branch("merged-a", file="a.txt", content="a\n")
        a_sha = self.fx.sha(self.fx.a, "merged-a")
        self.fx.switch(self.fx.a, "main")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--no-ff", "merged-a", "-m", "merge a")
        self.fx.push(self.fx.a, "main")

        self.fx.create_remote_branch("squashed-b", file="b.txt", content="b\n")
        b_sha = self.fx.sha(self.fx.a, "squashed-b")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--squash", "squashed-b")
        self.fx.commit(self.fx.a, "squash b")
        self.fx.push(self.fx.a, "main")

        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "merged-a", "origin/merged-a")
        self.fx.branch(self.fx.b, "squashed-b", "origin/squashed-b")

        result = self.fx.tool(self.fx.b, "prune", "--target", "local", "--apply")
        self.fx.assert_exit(result, 0)
        branches = self.fx.git_run(self.fx.b, "branch", "--format=%(refname:short)").stdout.split()
        self.assertNotIn("merged-a", branches)
        self.assertNotIn("squashed-b", branches)
        self.assertEqual(
            self.fx.sha(self.fx.b, f"refs/repo-sync/archive/merged-a/{a_sha}"), a_sha
        )

        archive = self.fx.tool_json(self.fx.b, "archive")
        self.assertGreaterEqual(len(archive["archives"]), 2)
        restored = self.fx.tool(self.fx.b, "restore", "squashed-b", "--json")
        self.fx.assert_exit(restored, 0)
        payload = json.loads(restored.stdout)
        self.assertEqual(payload["branch"], "squashed-b")
        self.assertEqual(self.fx.sha(self.fx.b, "squashed-b"), b_sha)

        duplicate = self.fx.tool(self.fx.b, "restore", "squashed-b")
        self.fx.assert_exit(duplicate, 1)
        self.assertIn("already exists", duplicate.stderr)

    def test_prune_protects_current_and_checked_out_branches(self) -> None:
        self.fx.create_remote_branch("develop")
        self.fx.create_remote_branch("worktree-topic", file="w.txt", content="w\n")
        self.fx.switch(self.fx.a, "main")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--no-ff", "worktree-topic", "-m", "merge w")
        self.fx.push(self.fx.a, "main")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "develop", "origin/develop")
        self.fx.branch(self.fx.b, "worktree-topic", "origin/worktree-topic")

        worktree_path = self.fx.root / "wt"
        self.fx.git_run(
            self.fx.b, "worktree", "add", "--quiet", str(worktree_path), "worktree-topic"
        )
        self.addCleanup(
            lambda: self.fx.git_run(
                self.fx.b, "worktree", "remove", "--force", str(worktree_path), check=False
            )
        )

        result = self.fx.tool(self.fx.b, "prune", "--target", "local", "--apply", "--json")
        self.fx.assert_exit(result, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["deleted"], [])
        skipped = {item["name"]: item["blockers"] for item in payload["skipped"]}
        self.assertIn("worktree-topic", skipped)
        self.assertTrue(any("checked out in" in blocker for blocker in skipped["worktree-topic"]))
        branches = self.fx.git_run(self.fx.b, "branch", "--format=%(refname:short)").stdout.split()
        self.assertIn("main", branches)
        self.assertIn("worktree-topic", branches)

    def test_custom_default_branch_is_protected_from_prune(self) -> None:
        self.fx.create_remote_branch("production")
        self.fx.git_run(self.fx.origin, "symbolic-ref", "HEAD", "refs/heads/production")
        self.fx.create_remote_branch("feature", file="feature.txt", content="feature\n")
        self.fx.switch(self.fx.a, "production")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--no-ff", "feature", "-m", "merge feature")
        self.fx.push(self.fx.a, "production")
        self.fx.switch(self.fx.a, "main")

        snapshot = self.fx.tool_json(self.fx.b, "audit")
        self.assertEqual(snapshot["repo"]["default_branch"], "production")
        production = next(
            item for item in snapshot["remote_branches"] if item["name"] == "production"
        )
        self.assertTrue(production["protected"])
        feature = next(item for item in snapshot["remote_branches"] if item["name"] == "feature")
        self.assertTrue(feature["cleanup_candidate"])

        result = self.fx.tool(self.fx.b, "prune", "--target", "remote", "--apply", "--json")
        self.fx.assert_exit(result, 0)
        self.assertEqual([item["name"] for item in json.loads(result.stdout)["deleted"]], ["feature"])
        self.assertIn("production", self.fx.remote_heads())

        explicit = self.fx.tool(
            self.fx.b,
            "prune",
            "--target",
            "remote",
            "--branch",
            "production",
            "--allow-unmerged",
            "--apply",
        )
        self.fx.assert_exit(explicit, 2)
        self.assertIn("production", self.fx.remote_heads())

    def test_default_branch_override_keeps_detected_default_protected(self) -> None:
        self.fx.create_remote_branch("production")
        self.fx.git_run(self.fx.origin, "symbolic-ref", "HEAD", "refs/heads/production")
        self.fx.create_remote_branch("feature", file="feature.txt", content="feature\n")
        self.fx.switch(self.fx.a, "production")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--no-ff", "feature", "-m", "merge feature")
        self.fx.push(self.fx.a, "production")
        self.fx.git_run(self.fx.a, "push", "--quiet", "origin", "production:main")
        self.fx.switch(self.fx.a, "main")

        snapshot = self.fx.tool_json(self.fx.b, "audit", "--default-branch", "main")
        self.assertEqual(snapshot["repo"]["default_branch"], "main")
        self.assertEqual(snapshot["repo"]["detected_default_branch"], "production")
        production = next(
            item for item in snapshot["remote_branches"] if item["name"] == "production"
        )
        self.assertTrue(production["protected"])

        result = self.fx.tool(
            self.fx.b, "prune", "--target", "remote", "--default-branch", "main", "--apply", "--json"
        )
        self.fx.assert_exit(result, 0)
        deleted = [item["name"] for item in json.loads(result.stdout)["deleted"]]
        self.assertEqual(deleted, ["feature"])
        self.assertIn("production", self.fx.remote_heads())

    def test_remote_prune_protects_current_and_checked_out_branches(self) -> None:
        self.fx.create_remote_branch("topic", file="t.txt", content="t\n")
        self.fx.create_remote_branch("held", file="h.txt", content="h\n")
        self.fx.switch(self.fx.a, "main")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--no-ff", "topic", "-m", "merge topic")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--no-ff", "held", "-m", "merge held")
        self.fx.push(self.fx.a, "main")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        self.fx.branch(self.fx.b, "held", "origin/held")
        self.fx.switch(self.fx.b, "topic")

        worktree_path = self.fx.root / "remote-wt"
        self.fx.git_run(self.fx.b, "worktree", "add", "--quiet", str(worktree_path), "held")
        self.addCleanup(
            lambda: self.fx.git_run(
                self.fx.b, "worktree", "remove", "--force", str(worktree_path), check=False
            )
        )

        result = self.fx.tool(self.fx.b, "prune", "--target", "remote", "--apply", "--json")
        self.fx.assert_exit(result, 0)
        self.assertEqual(json.loads(result.stdout)["deleted"], [])
        heads = self.fx.remote_heads()
        self.assertIn("topic", heads)
        self.assertIn("held", heads)

    def test_unmerged_branch_requires_explicit_selection_and_flag(self) -> None:
        self.fx.create_remote_branch("unmerged", file="u.txt", content="u\n")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "unmerged", "origin/unmerged")

        bulk = self.fx.tool(self.fx.b, "prune", "--target", "local", "--merged", "--apply")
        self.fx.assert_exit(bulk, 0)
        self.assertIn(
            "unmerged", self.fx.git_run(self.fx.b, "branch", "--format=%(refname:short)").stdout
        )

        named = self.fx.tool(self.fx.b, "prune", "--target", "local", "--branch", "unmerged", "--apply")
        self.fx.assert_exit(named, 2)
        self.assertIn(
            "unmerged", self.fx.git_run(self.fx.b, "branch", "--format=%(refname:short)").stdout
        )

        missing_flag = self.fx.tool(
            self.fx.b, "prune", "--target", "local", "--allow-unmerged", "--apply"
        )
        self.fx.assert_exit(missing_flag, 2)
        self.assertIn("requires one or more --branch", missing_flag.stderr)

        deleted = self.fx.tool(
            self.fx.b,
            "prune",
            "--target",
            "local",
            "--branch",
            "unmerged",
            "--allow-unmerged",
            "--apply",
        )
        self.fx.assert_exit(deleted, 0)
        self.assertNotIn(
            "unmerged", self.fx.git_run(self.fx.b, "branch", "--format=%(refname:short)").stdout
        )

    def test_remote_prune_refetches_before_deleting(self) -> None:
        self.fx.create_remote_branch("squashed", file="squashed.txt", content="squashed\n")
        self.fx.switch(self.fx.a, "main")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--squash", "squashed")
        self.fx.commit(self.fx.a, "squash merge")
        self.fx.push(self.fx.a, "main")

        audit = self.fx.tool_json(self.fx.b, "audit")
        remote = next(item for item in audit["remote_branches"] if item["name"] == "squashed")
        self.assertTrue(remote["cleanup_candidate"])

        self.fx.switch(self.fx.a, "squashed")
        self.fx.write(self.fx.a, "new.txt", "new\n")
        self.fx.git_run(self.fx.a, "add", "new.txt")
        self.fx.commit(self.fx.a, "new work")
        self.fx.push(self.fx.a, "squashed")

        result = self.fx.tool(self.fx.b, "prune", "--target", "remote", "--apply", "--json")
        self.fx.assert_exit(result, 0)
        self.assertEqual(json.loads(result.stdout)["deleted"], [])
        self.assertIn("squashed", self.fx.remote_heads())

    def test_shallow_clone_refuses_cleanup(self) -> None:
        self.fx.create_remote_branch("merged", file="m.txt", content="m\n")
        self.fx.switch(self.fx.a, "main")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--no-ff", "merged", "-m", "merge")
        self.fx.push(self.fx.a, "main")
        shallow = self.fx.root / "shallow"
        subprocess.run(
            [GIT, "clone", "--quiet", "--depth", "1", self.fx.origin.as_uri(), str(shallow)],
            env=self.fx.env,
            check=True,
            capture_output=True,
        )
        self.assertEqual(
            self.fx.git_run(shallow, "rev-parse", "--is-shallow-repository").stdout.strip(), "true"
        )
        result = self.fx.tool(shallow, "prune", "--target", "remote", "--apply")
        self.fx.assert_exit(result, 2)
        self.assertIn("shallow clone", result.stderr)
        self.assertIn("merged", self.fx.remote_heads())

    def test_repository_operation_in_progress_blocks_mutation(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        self.fx.switch(self.fx.b, "topic")
        self.fx.write(self.fx.b, "f.txt", "b\n")
        self.fx.git_run(self.fx.b, "add", "f.txt")
        self.fx.commit(self.fx.b, "b change")
        self.fx.switch(self.fx.a, "topic")
        self.fx.write(self.fx.a, "f.txt", "a\n")
        self.fx.git_run(self.fx.a, "add", "f.txt")
        self.fx.commit(self.fx.a, "a change")
        self.fx.push(self.fx.a, "topic")
        self.fx.git_run(self.fx.b, "fetch", "--quiet", "origin")
        rebase = self.fx.git_run(self.fx.b, "rebase", "origin/topic", check=False)
        self.assertNotEqual(rebase.returncode, 0)
        self.addCleanup(
            lambda: self.fx.git_run(self.fx.b, "rebase", "--abort", check=False)
        )

        sync = self.fx.tool(self.fx.b, "sync", "--apply")
        self.fx.assert_exit(sync, 2)
        self.assertIn("rebase operation", sync.stderr)
        prune = self.fx.tool(self.fx.b, "prune", "--target", "local", "--apply")
        self.fx.assert_exit(prune, 2)
        self.assertIn("rebase operation", prune.stderr)
        audit = self.fx.tool(self.fx.b, "audit", "--json")
        self.fx.assert_exit(audit, 0)
        self.assertEqual(json.loads(audit.stdout)["repo"]["in_progress"], "rebase")

    def test_gone_upstream_prunes_only_merged_local_branches(self) -> None:
        self.fx.create_remote_branch("gone-merged", file="gm.txt", content="gm\n")
        merged_sha = self.fx.sha(self.fx.a, "gone-merged")
        self.fx.switch(self.fx.a, "main")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--no-ff", "gone-merged", "-m", "merge gm")
        self.fx.push(self.fx.a, "main")
        self.fx.create_remote_branch("gone-unmerged", file="gu.txt", content="gu\n")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "gone-merged", "origin/gone-merged")
        self.fx.branch(self.fx.b, "gone-unmerged", "origin/gone-unmerged")

        self.fx.git_run(self.fx.a, "push", "--quiet", "origin", "--delete", "gone-merged", "gone-unmerged")
        snapshot = self.fx.tool_json(self.fx.b, "audit")
        merged = next(item for item in snapshot["local_branches"] if item["name"] == "gone-merged")
        unmerged = next(item for item in snapshot["local_branches"] if item["name"] == "gone-unmerged")
        self.assertEqual(merged["status"], "upstream-gone")
        self.assertTrue(merged["merged"])
        self.assertFalse(unmerged["merged"])

        result = self.fx.tool(self.fx.b, "prune", "--target", "local", "--gone", "--apply", "--json")
        self.fx.assert_exit(result, 0)
        payload = json.loads(result.stdout)
        self.assertEqual([item["name"] for item in payload["deleted"]], ["gone-merged"])
        self.assertEqual([item["name"] for item in payload["skipped"]], ["gone-unmerged"])
        branches = self.fx.git_run(self.fx.b, "branch", "--format=%(refname:short)").stdout.split()
        self.assertNotIn("gone-merged", branches)
        self.assertIn("gone-unmerged", branches)
        self.assertEqual(
            self.fx.sha(self.fx.b, f"refs/repo-sync/archive/gone-merged/{merged_sha}"), merged_sha
        )

    def test_stale_unmerged_branch_is_reported_but_not_deleted(self) -> None:
        self.fx.switch(self.fx.a, "topic", create=True, start="main")
        self.fx.write(self.fx.a, "old.txt", "old\n")
        self.fx.git_run(self.fx.a, "add", "old.txt")
        self.fx.commit(self.fx.a, "old work", date="2024-01-01T00:00:00Z")
        self.fx.push(self.fx.a, "topic")
        self.fx.switch(self.fx.a, "main")

        snapshot = self.fx.tool_json(self.fx.b, "audit", "--stale-days", "90")
        topic = next(item for item in snapshot["remote_branches"] if item["name"] == "topic")
        self.assertTrue(topic["stale"])
        self.assertTrue(topic["review_candidate"])
        self.assertFalse(topic["cleanup_candidate"])

        result = self.fx.tool(
            self.fx.b, "prune", "--target", "remote", "--stale-days", "90", "--apply", "--json"
        )
        self.fx.assert_exit(result, 0)
        self.assertEqual(json.loads(result.stdout)["deleted"], [])
        self.assertIn("topic", self.fx.remote_heads())

    def test_stale_tracking_ref_is_reported_and_pruned(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.assertEqual(self.fx.sha(self.fx.b, "refs/remotes/origin/topic"), self.fx.sha(self.fx.a, "topic"))
        self.fx.git_run(self.fx.a, "push", "--quiet", "origin", "--delete", "topic")

        snapshot = self.fx.tool_json(self.fx.b, "audit")
        self.assertIn("topic", snapshot["stale_tracking"])
        self.assertTrue(any("stale remote-tracking" in finding for finding in snapshot["findings"]))
        self.fx.assert_exit(self.fx.tool(self.fx.b, "audit", "--strict"), 2)

        synced = self.fx.tool(self.fx.b, "sync", "--apply", "--json")
        self.fx.assert_exit(synced, 0)
        missing = self.fx.git_run(
            self.fx.b, "show-ref", "--verify", "--quiet", "refs/remotes/origin/topic", check=False
        )
        self.assertNotEqual(missing.returncode, 0)

    def test_default_branch_fallback_and_override(self) -> None:
        self.fx.git_run(self.fx.b, "remote", "set-head", "origin", "-d")
        snapshot = self.fx.tool_json(self.fx.b, "audit")
        self.assertEqual(snapshot["repo"]["default_branch"], "main")

        self.fx.create_remote_branch("base-topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "base-topic", "origin/base-topic")
        self.fx.create_remote_branch("feature", file="feature.txt", content="feature\n")
        self.fx.switch(self.fx.a, "base-topic")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--no-ff", "feature", "-m", "merge feature")
        self.fx.push(self.fx.a, "base-topic")

        with_main = self.fx.tool_json(self.fx.b, "audit")
        feature = next(item for item in with_main["remote_branches"] if item["name"] == "feature")
        self.assertFalse(feature["merged"])

        with_topic = self.fx.tool_json(self.fx.b, "audit", "--default-branch", "base-topic")
        self.assertEqual(with_topic["repo"]["default_branch"], "base-topic")
        feature = next(item for item in with_topic["remote_branches"] if item["name"] == "feature")
        self.assertTrue(feature["merged"])

        self.fx.create_remote_branch("develop")
        self.fx.git_run(self.fx.origin, "symbolic-ref", "HEAD", "refs/heads/develop")
        changed = self.fx.tool_json(self.fx.b, "audit")
        self.assertEqual(changed["repo"]["default_branch"], "develop")

    def test_missing_remote_and_bare_repository_fail(self) -> None:
        bare = self.fx.root / "bare.git"
        self.fx.git_run(self.fx.root, "init", "--quiet", "--bare", str(bare))
        bare_result = self.fx.tool(bare, "audit")
        self.fx.assert_exit(bare_result, 1)
        self.assertIn("not a Git worktree", bare_result.stderr)

        solo = self.fx.root / "solo"
        self.fx.git_run(self.fx.root, "init", "--quiet", "-b", "main", str(solo))
        self.fx.git_run(solo, "config", "user.name", "Solo")
        self.fx.git_run(solo, "config", "user.email", "solo@example.invalid")
        self.fx.write(solo, "s.txt", "s\n")
        self.fx.git_run(solo, "add", "s.txt")
        self.fx.git_run(solo, "commit", "--quiet", "-m", "solo")
        solo_result = self.fx.tool(solo, "audit")
        self.fx.assert_exit(solo_result, 1)
        self.assertIn("cannot choose a remote", solo_result.stderr)


class RepoSyncUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="repo-sync-unit-", ignore_cleanup_errors=True)
        self.addCleanup(self.temporary.cleanup)
        self.fx = Fixture(Path(self.temporary.name))
        self.repo = module.Repository(path=self.fx.b, git=module.Git(self.fx.b), remote="origin")

    def snapshot(self, *, check_prs: bool = False) -> dict:
        return module.build_snapshot(
            self.repo,
            offline=False,
            prune_remote_refs=True,
            stale_days=90,
            check_prs=check_prs,
            protected_extra=[],
        )

    def test_protected_patterns(self) -> None:
        self.assertTrue(module.is_protected("release/1.0", "main", []))
        self.assertTrue(module.is_protected("hotfix/urgent", "main", []))
        self.assertTrue(module.is_protected("develop", "main", []))
        self.assertTrue(module.is_protected("gh-pages", "main", []))
        self.assertTrue(module.is_protected("production", "production", []))
        self.assertFalse(module.is_protected("production", "main", []))
        self.assertTrue(module.is_protected("feature/x", "main", ["feature/*"]))
        self.assertFalse(module.is_protected("feature/x", "main", []))

    def test_open_pull_request_blocks_deletion(self) -> None:
        self.fx.create_remote_branch("squashed", file="squashed.txt", content="squashed\n")
        self.fx.switch(self.fx.a, "main")
        self.fx.git_run(self.fx.a, "merge", "--quiet", "--squash", "squashed")
        self.fx.commit(self.fx.a, "squash merge")
        self.fx.push(self.fx.a, "main")

        with mock.patch.object(module, "open_pull_requests", return_value={"squashed": [17]}):
            snapshot = self.snapshot(check_prs=True)
        record = next(item for item in snapshot["remote_branches"] if item["name"] == "squashed")
        self.assertEqual(record["open_prs"], [17])
        self.assertFalse(record["cleanup_candidate"])
        self.assertTrue(any("open pull request #17" in blocker for blocker in record["blockers"]))

        args = mock.Mock(
            branch=[],
            merged=True,
            gone=False,
            stale_days=None,
            allow_unmerged=False,
            target="remote",
        )
        plan = module.build_prune_plan(snapshot, args)
        item = next(item for item in plan if item["name"] == "squashed")
        self.assertEqual(item["action"], "skip")

    def test_check_prs_without_gh_fails_closed(self) -> None:
        with mock.patch.object(module.shutil, "which", return_value=None):
            with self.assertRaises(module.Refusal):
                module.open_pull_requests(module.Git(self.fx.b))

    def test_remote_lease_rejects_moved_branch(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        stale_sha = self.fx.remote_heads()["topic"]
        self.fx.switch(self.fx.a, "topic")
        self.fx.write(self.fx.a, "after.txt", "after\n")
        self.fx.git_run(self.fx.a, "add", "after.txt")
        self.fx.commit(self.fx.a, "after")
        self.fx.push(self.fx.a, "topic")
        moved_sha = self.fx.remote_heads()["topic"]
        self.assertNotEqual(stale_sha, moved_sha)

        with self.assertRaises(module.GitError):
            module.delete_remote_branch(module.Git(self.fx.b), "origin", "topic", stale_sha)
        self.assertEqual(self.fx.remote_heads()["topic"], moved_sha)

    def test_archive_failure_aborts_deletion(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        sha = self.fx.sha(self.fx.b, "topic")
        snapshot = self.snapshot()
        plan = [
            {
                "target": "local",
                "name": "topic",
                "sha": sha,
                "merged": True,
                "merge_state": "ancestor",
                "age_days": 0,
                "blockers": [],
                "action": "delete",
                "archive_ref": f"refs/repo-sync/archive/topic/{sha}",
            }
        ]

        with mock.patch.object(module, "archive_tip", side_effect=module.GitError("archive failed")):
            result = module.apply_prune_plan(
                self.repo, snapshot, plan, apply=True, target="local"
            )
        self.assertEqual(len(result["failed"]), 1)
        self.assertIn(
            "topic", self.fx.git_run(self.fx.b, "branch", "--format=%(refname:short)").stdout
        )

    def test_moved_branch_after_plan_keeps_archive_and_branch(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        old_sha = self.fx.sha(self.fx.b, "topic")
        snapshot = self.snapshot()
        plan = [
            {
                "target": "local",
                "name": "topic",
                "sha": old_sha,
                "merged": True,
                "merge_state": "ancestor",
                "age_days": 0,
                "blockers": [],
                "action": "delete",
                "archive_ref": f"refs/repo-sync/archive/topic/{old_sha}",
            }
        ]

        self.fx.switch(self.fx.b, "topic")
        self.fx.write(self.fx.b, "move.txt", "move\n")
        self.fx.git_run(self.fx.b, "add", "move.txt")
        self.fx.commit(self.fx.b, "move")
        moved_sha = self.fx.sha(self.fx.b, "topic")
        self.fx.switch(self.fx.b, "main")

        result = module.apply_prune_plan(self.repo, snapshot, plan, apply=True, target="local")
        self.assertEqual(len(result["failed"]), 1)
        self.assertEqual(self.fx.sha(self.fx.b, "topic"), moved_sha)
        self.assertEqual(self.fx.sha(self.fx.b, f"refs/repo-sync/archive/topic/{old_sha}"), old_sha)

    def test_delete_local_branch_requires_current_tip(self) -> None:
        self.fx.create_remote_branch("topic")
        self.fx.fetch(self.fx.b)
        self.fx.branch(self.fx.b, "topic", "origin/topic")
        stale = self.fx.sha(self.fx.b, "topic")
        self.fx.switch(self.fx.b, "topic")
        self.fx.write(self.fx.b, "move.txt", "move\n")
        self.fx.git_run(self.fx.b, "add", "move.txt")
        self.fx.commit(self.fx.b, "move")
        self.fx.switch(self.fx.b, "main")
        self.fx.git_run(self.fx.b, "fetch", "--quiet", "origin")

        with self.assertRaises(module.GitError):
            module.delete_local_branch(module.Git(self.fx.b), "topic", stale)
        self.assertIn(
            "topic", self.fx.git_run(self.fx.b, "branch", "--format=%(refname:short)").stdout
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
