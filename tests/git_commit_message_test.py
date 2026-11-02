#!/usr/bin/env python3
"""Behavioral contract through the public CLI and real Git commit-msg execution."""

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
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("COMMIT_MESSAGE_TOOL", ROOT / "skills/git-commit-message/scripts/commit_message.py"))
spec = importlib.util.spec_from_file_location("commit_message", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
GIT = shutil.which("git")


class CommitMessageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="commit message 测试 ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("GIT_", "AI_AGENT_"))}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT="0")
        self.git("init", "--template=", "-b", "main")
        self.git("config", "user.name", "Hook Test")
        self.git("config", "user.email", "hook-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.message = self.root / "message.txt"
        self.message.write_bytes(b"fix: login\n\nBody\nSigned-off-by: Test\n")
        self.hook = self.repo / ".git/hooks/commit-msg"

    def run_command(self, args, *, ok=True, env=None, cwd=None):
        result = subprocess.run([str(a) for a in args], cwd=cwd or self.repo,
                                env=self.env if env is None else env, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout.decode(errors="replace"))
        return result

    def git(self, *args, **kwargs):
        return self.run_command([GIT, "-C", self.repo, *args], **kwargs)

    def tool(self, command, *args, **kwargs):
        return self.run_command([sys.executable, TOOL, "--repo", self.repo, command, *args], **kwargs)

    def identity(self, **overrides):
        return {**self.env, "AI_AGENT_CLIENT": "Test Agent", "AI_AGENT_CLIENT_VERSION": "2.3.4",
                "AI_AGENT_MODEL": "test-model", **overrides}

    def policy(self, **values):
        (self.repo / module.POLICY).write_text(json.dumps(values), encoding="utf-8")

    def commit(self, *args, **kwargs):
        # Disposable fixture identity and state are inspected before every commit.
        self.git("status", "--short", "--branch")
        self.git("config", "user.name")
        self.git("config", "user.email")
        return self.git("commit", "--allow-empty", *args, **kwargs)

    def test_identity_matrix_and_idempotency(self):
        for client, version, expected in (
            ("Test Agent", "2.3.4", "[Test Agent 2.3.4][test-model]"),
            ("Test Agent", "", "[Test Agent][test-model]"),
            ("", "", "[test-model]"),
            ("", "2.3.4", "[test-model]"),
        ):
            with self.subTest(client=client, version=version):
                self.message.write_text("修复登录\n\n正文\n", encoding="utf-8")
                env = self.identity(AI_AGENT_CLIENT=client, AI_AGENT_CLIENT_VERSION=version)
                self.tool("check", self.message, env=env, ok=False)
                self.assertEqual(self.message.read_text(), "修复登录\n\n正文\n")
                self.tool("fix", self.message, env=env)
                fixed = self.message.read_bytes()
                self.assertEqual(fixed.decode(), expected + " 修复登录\n\n正文\n")
                self.tool("fix", self.message, env=env)
                self.tool("check", self.message, env=env)
                self.assertEqual(self.message.read_bytes(), fixed)

    def test_extra_prefix_order_and_duplicates(self):
        self.policy(extra_prefixes=["PROJ-42", "backend"])
        self.message.write_bytes(b"[test-model][backend] [PROJ-42][test-model] fix: login\r\n\r\nBody\r\n")
        self.tool("fix", self.message, env=self.identity(AI_AGENT_CLIENT="", AI_AGENT_CLIENT_VERSION=""))
        self.assertEqual(self.message.read_bytes(),
                         b"[PROJ-42][backend][test-model] fix: login\r\n\r\nBody\r\n")
        self.tool("check", self.message, env=self.identity(AI_AGENT_CLIENT="", AI_AGENT_CLIENT_VERSION=""))

    def test_disabled_ai_and_no_prefix_policies(self):
        for config, expected in (
            ({"ai_prefix": False, "extra_prefixes": ["project"]}, b"[project] fix: login\n"),
            ({"ai_prefix": False}, b"fix: login\n"),
            ({"enabled": False}, b"fix: login\n"),
        ):
            with self.subTest(config=config):
                self.policy(**config)
                self.message.write_bytes(b"fix: login\n")
                self.tool("hook", self.message)
                self.assertEqual(self.message.read_bytes(), expected)

    def test_unknown_model_and_invalid_identity_preserve_message(self):
        raw = self.message.read_bytes()
        for env in (self.env, self.identity(AI_AGENT_MODEL=""),
                    self.identity(AI_AGENT_CLIENT="bad\nclient"),
                    self.identity(AI_AGENT_MODEL="[model]"),
                    self.identity(AI_AGENT_CLIENT_VERSION=" 1")):
            for command in ("hook", "check", "fix"):
                with self.subTest(env=env.get("AI_AGENT_MODEL"), command=command):
                    self.tool(command, self.message, env=env, ok=False)
                    self.assertEqual(self.message.read_bytes(), raw)

    def test_invalid_config_blocks_every_entry_even_early_success(self):
        self.tool("install")
        hook_bytes = self.hook.read_bytes()
        raw = self.message.read_bytes()
        configs = ["{", "[]", '{"enabled":false,"extra_prefixes":"x"}',
                   '{"enabled":false,"enabled":true}', '{"unknown":true}',
                   '{"enabled":0}', '{"ai_prefix":"false"}', '{"schema_version":true}',
                   '{"mode":"oops"}', '{"skip_autosquash":0}',
                   '{"extra_prefixes":["x","x"]}', '{"extra_prefixes":["[x]"]}',
                   '{"extra_prefixes":[null]}']
        for config in configs:
            (self.repo / module.POLICY).write_text(config)
            for command in ("install", "uninstall", "hook", "check", "fix"):
                with self.subTest(config=config, command=command):
                    args = () if command in ("install", "uninstall") else (self.message,)
                    self.tool(command, *args, env=self.identity(), ok=False)
                    self.assertEqual(self.hook.read_bytes(), hook_bytes)
                    self.assertEqual(self.message.read_bytes(), raw)

    def test_invalid_config_does_not_create_hooks_directory(self):
        self.policy(enabled=False, mode="bad")
        self.tool("install", ok=False)
        self.assertFalse(self.hook.parent.exists())

    def test_check_only_then_manual_fix_and_policy_reload(self):
        self.policy(mode="check")
        raw = self.message.read_bytes()
        self.tool("hook", self.message, env=self.identity(), ok=False)
        self.assertEqual(self.message.read_bytes(), raw)
        self.tool("fix", self.message, env=self.identity())
        self.tool("hook", self.message, env=self.identity())
        self.policy(mode="fix", ai_prefix=False, extra_prefixes=["new"])
        self.tool("hook", self.message)
        self.assertTrue(self.message.read_text().startswith("[new] [Test Agent"))

    def test_comments_body_trailers_and_line_endings(self):
        for ending in (b"\n", b"\r\n"):
            raw = ending.join([b"", b"fix: login", b"", b"Body", b"# template", b"Signed-off-by: Test", b""])
            self.message.write_bytes(raw)
            self.tool("fix", self.message, env=self.identity())
            self.assertEqual(self.message.read_bytes(), raw.replace(b"fix: login", b"[Test Agent 2.3.4][test-model] fix: login", 1))
        self.git("config", "core.commentChar", ";")
        self.message.write_text("fix: login\n; comment")
        self.tool("fix", self.message, env=self.identity())
        self.assertEqual(self.message.read_text(), "[Test Agent 2.3.4][test-model] fix: login\n; comment")

    def test_invalid_message_never_turns_into_prefix_only_commit(self):
        for raw in (b"", b" \n# comment\n", b"[test-model]\n", b"[test-model] # comment\n", b"a\x00b", b"\xff"):
            for command in ("hook", "check", "fix"):
                with self.subTest(raw=raw, command=command):
                    self.message.write_bytes(raw)
                    self.tool(command, self.message, env=self.identity(AI_AGENT_CLIENT="", AI_AGENT_CLIENT_VERSION=""), ok=False)
                    self.assertEqual(self.message.read_bytes(), raw)

    def test_conflicting_git_comments_rejected_before_write(self):
        for value in ("auto", "["):
            self.git("config", "core.commentChar", value)
            raw = self.message.read_bytes()
            self.tool("fix", self.message, env=self.identity(), ok=False)
            self.assertEqual(self.message.read_bytes(), raw)

    def test_comment_aliases_follow_git_configuration_order(self):
        for first, second, literal in (
            (("core.commentString", "#"), ("core.commentChar", ";"), "# literal subject"),
            (("core.commentChar", ";"), ("core.commentString", "#"), "; literal subject"),
        ):
            self.git("config", "--add", *first)
            self.git("config", "--add", *second)
            self.message.write_text(literal + "\n")
            self.tool("fix", self.message, env=self.identity())
            self.assertEqual(self.message.read_text(), "[Test Agent 2.3.4][test-model] " + literal + "\n")

    def test_leading_comments_rejected_instead_of_prefixing_body(self):
        raw = b"# comment\n\nfix: body subject\n"
        self.message.write_bytes(raw)
        for command in ("hook", "fix", "check"):
            self.tool(command, self.message, env=self.identity(), ok=False)
            self.assertEqual(self.message.read_bytes(), raw)
        self.tool("install")
        self.commit("-F", self.message, env=self.identity(), ok=False)
        self.git("rev-parse", "--verify", "HEAD", ok=False)

    def test_autosquash_exemption_and_opt_in(self):
        for marker in ("fixup!", "squash!", "amend!"):
            raw = f"{marker} [older-model] target\n\nbody\n".encode()
            self.message.write_bytes(raw)
            self.tool("hook", self.message)  # No identity needed for the documented exemption.
            self.assertEqual(self.message.read_bytes(), raw)
        self.policy(skip_autosquash=False)
        self.tool("hook", self.message, env=self.identity())
        self.assertTrue(self.message.read_text().startswith("[Test Agent 2.3.4][test-model] amend!"))

    def test_unknown_brackets_are_preserved(self):
        self.message.write_text("[BUG][old-model] fix: login\n")
        self.tool("fix", self.message, env=self.identity())
        self.assertEqual(self.message.read_text(), "[Test Agent 2.3.4][test-model] [BUG][old-model] fix: login\n")

    def test_install_reinstall_mode_repair_uninstall_repeat(self):
        self.tool("install")
        self.assertEqual(self.hook.read_bytes(), TOOL.read_bytes())
        self.assertTrue(os.access(self.hook, os.X_OK))
        first = self.hook.stat().st_mtime_ns
        self.tool("install")
        self.assertEqual(self.hook.stat().st_mtime_ns, first)
        self.hook.chmod(0o644)
        self.tool("install")
        self.assertTrue(os.access(self.hook, os.X_OK))
        self.tool("uninstall")
        self.tool("uninstall")
        self.assertFalse(self.hook.exists())

    def test_existing_differing_hook_preserved(self):
        self.hook.parent.mkdir()
        self.hook.write_bytes(b"#!/bin/sh\nexit 42\n")
        before = self.hook.read_bytes()
        for command in ("install", "uninstall"):
            self.tool(command, ok=False)
            self.assertEqual(self.hook.read_bytes(), before)

    def test_custom_hooks_path_refuses_without_touching_configuration(self):
        for value in (".husky", "/dev/null", str(self.root / "external hooks"), ""):
            self.git("config", "core.hooksPath", value)
            before = (self.repo / ".git/config").read_bytes()
            for command in ("install", "uninstall"):
                self.tool(command, ok=False)
                self.assertEqual((self.repo / ".git/config").read_bytes(), before)
                self.assertFalse(self.hook.exists())

    def test_symlink_and_hardlink_hook_paths(self):
        external = self.root / "external"
        external.mkdir()
        self.hook.parent.symlink_to(external, target_is_directory=True)
        for command in ("install", "uninstall"):
            self.tool(command, ok=False)
        self.assertEqual(list(external.iterdir()), [])
        self.hook.parent.unlink()
        self.hook.parent.mkdir()
        for kind in ("symlink", "hardlink", "directory"):
            with self.subTest(kind=kind):
                other = external / "original"
                other.write_bytes(TOOL.read_bytes())
                if kind == "symlink":
                    self.hook.symlink_to(other)
                elif kind == "hardlink":
                    os.link(other, self.hook)
                else:
                    self.hook.mkdir()
                for command in ("install", "uninstall"):
                    self.tool(command, ok=False)
                    self.assertEqual(other.read_bytes(), TOOL.read_bytes())
                self.hook.rmdir() if kind == "directory" else self.hook.unlink()

    def test_message_aliases_and_config_symlink_rejected(self):
        alias = self.root / "alias"
        raw = self.message.read_bytes()
        for kind in ("symlink", "hardlink"):
            if kind == "symlink":
                alias.symlink_to(self.message)
            else:
                os.link(self.message, alias)
            for command in ("hook", "fix", "check"):
                self.tool(command, alias, env=self.identity(), ok=False)
                self.assertEqual(self.message.read_bytes(), raw)
            alias.unlink()
        config = self.repo / module.POLICY
        config.symlink_to(self.message)
        for command in ("install", "uninstall", "hook", "fix", "check"):
            self.tool(command, *(() if command in ("install", "uninstall") else (self.message,)),
                      env=self.identity(), ok=False)
        self.assertEqual(self.message.read_bytes(), raw)

    def test_protected_input_identity_including_case_alias(self):
        self.policy(ai_prefix=False)
        config = self.repo / module.POLICY
        for command in ("hook", "check", "fix"):
            self.tool(command, config, ok=False)
            self.tool(command, TOOL, ok=False)
        case_alias = self.repo / module.POLICY.upper()
        if case_alias.exists() and case_alias.samefile(config):
            self.tool("fix", case_alias, ok=False)
        else:
            # Controlled alias substitute on case-sensitive filesystems.
            with patch.object(Path, "samefile", return_value=True):
                with self.assertRaises(module.PolicyError):
                    module.process(self.repo, module.policy(self.repo), self.message, "fix")

    def test_real_commits_message_file_amend_and_check_rejection(self):
        self.tool("install")
        self.commit("-m", "fix: login", env=self.identity())
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.decode().strip(),
                         "[Test Agent 2.3.4][test-model] fix: login")
        self.commit("--amend", "-F", self.message, env=self.identity())
        self.assertIn(b"Body\nSigned-off-by: Test", self.git("log", "-1", "--format=%B").stdout)
        head = self.git("rev-parse", "HEAD").stdout
        self.policy(mode="check")
        self.commit("-m", "bad", env=self.identity(), ok=False)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, head)
        self.commit("-m", "[Test Agent 2.3.4][test-model] valid", env=self.identity())
        self.policy(enabled=False)
        self.commit("-m", "human commit")
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), b"human commit")

    def test_real_fixup_retains_target(self):
        self.tool("install")
        self.commit("-m", "target", env=self.identity())
        target = self.git("rev-parse", "HEAD").stdout.decode().strip()
        subject = self.git("log", "-1", "--format=%s").stdout.strip()
        self.commit("--fixup", target)
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), b"fixup! " + subject)

    def test_real_commit_missing_identity_and_invalid_policy_do_not_create_head(self):
        self.tool("install")
        self.commit("-m", "must fail", ok=False)
        self.git("rev-parse", "--verify", "HEAD", ok=False)
        self.policy(enabled=False, mode="invalid")
        self.commit("-m", "must fail", env=self.identity(), ok=False)
        self.git("rev-parse", "--verify", "HEAD", ok=False)
        self.policy(ai_prefix=False, extra_prefixes=["project"])
        self.commit("-m", "[project]", ok=False)
        self.git("rev-parse", "--verify", "HEAD", ok=False)

    def test_real_merge_message_and_repository_prefix(self):
        self.tool("install")
        self.commit("-m", "base", env=self.identity())
        self.git("switch", "-c", "side")
        self.commit("-m", "side", env=self.identity())
        self.git("switch", "main")
        self.policy(ai_prefix=False, extra_prefixes=["project"])
        self.git("merge", "--no-ff", "side", "-m", "merge side")
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), b"[project] merge side")

    def test_real_git_comment_cleanup_preserves_attribution(self):
        self.tool("install")
        self.git("config", "core.commentChar", ";")
        self.commit("--cleanup=strip", "-m", "fix: subject\n; comment\n\nBody", env=self.identity())
        result = self.git("log", "-1", "--format=%B").stdout
        self.assertTrue(result.startswith(b"[Test Agent 2.3.4][test-model] fix: subject\n"))
        self.assertIn(b"Body", result)
        self.assertNotIn(b"; comment", result)

    def test_standalone_copy_survives_source_deletion(self):
        source = self.root / "source.py"
        shutil.copyfile(TOOL, source)
        self.run_command([sys.executable, source, "install"])
        source.unlink()
        self.commit("-m", "standalone", env=self.identity())
        self.assertIn(b"[test-model] standalone", self.git("log", "-1", "--format=%s").stdout)

    def test_subdirectory_symlink_root_and_linked_worktree(self):
        self.tool("install")
        self.commit("-m", "base", env=self.identity())
        linked = self.root / "linked worktree"
        self.git("worktree", "add", "-b", "other", linked)
        (linked / module.POLICY).write_text('{"ai_prefix":false,"extra_prefixes":["linked"]}')
        nested = linked / "nested"
        nested.mkdir()
        alias = self.root / "root alias"
        alias.symlink_to(linked, target_is_directory=True)
        self.run_command([sys.executable, TOOL, "--repo", alias, "install"])
        self.run_command([GIT, "status", "--short", "--branch"], cwd=nested)
        self.run_command([GIT, "config", "user.name"], cwd=nested)
        self.run_command([GIT, "config", "user.email"], cwd=nested)
        self.run_command([GIT, "commit", "--allow-empty", "-m", "linked subject"], cwd=nested)
        result = self.run_command([GIT, "log", "-1", "--format=%s"], cwd=linked)
        self.assertEqual(result.stdout.strip(), b"[linked] linked subject")
        self.assertTrue(self.hook.exists())

    def test_missing_git_fails_before_any_mutation(self):
        empty_path = self.root / "empty-path"
        empty_path.mkdir()
        env = {**self.identity(), "PATH": str(empty_path)}
        raw = self.message.read_bytes()
        for command in ("install", "uninstall", "hook", "fix", "check"):
            self.tool(command, *(() if command in ("install", "uninstall") else (self.message,)), env=env, ok=False)
            self.assertEqual(self.message.read_bytes(), raw)
            self.assertFalse(self.hook.exists())

    def test_old_git_rejected_by_every_entry_before_mutation(self):
        raw = self.message.read_bytes()
        with patch.object(module, "git", return_value="git version 2.44.0"):
            for command in ("install", "uninstall", "hook", "fix", "check"):
                args = ["--repo", str(self.repo), command]
                if command not in ("install", "uninstall"):
                    args.append(str(self.message))
                self.assertEqual(module.main(args), 1)
                self.assertEqual(self.message.read_bytes(), raw)
                self.assertFalse(self.hook.exists())

    def test_missing_python_aborts_real_commit(self):
        self.tool("install")
        empty_path = self.root / "empty-path"
        empty_path.mkdir()
        self.commit("-m", "must fail", env={**self.identity(), "PATH": str(empty_path)}, ok=False)
        self.git("rev-parse", "--verify", "HEAD", ok=False)

    def test_atomic_failure_preserves_original_and_cleans_staging(self):
        raw = self.message.read_bytes()
        with patch.object(module.os, "replace", side_effect=OSError("injected replacement failure")):
            with self.assertRaises(OSError):
                module.atomic_write(self.message, b"changed", 0o600)
        self.assertEqual(self.message.read_bytes(), raw)
        self.assertEqual(list(self.root.glob(".commit-message-*")), [])

    def test_exclusive_install_preserves_hook_appearing_during_staging(self):
        self.hook.parent.mkdir()
        self.hook.write_bytes(b"another installer")
        with self.assertRaises(FileExistsError):
            module.atomic_write(self.hook, TOOL.read_bytes(), 0o755, replace=False)
        self.assertEqual(self.hook.read_bytes(), b"another installer")
        self.assertEqual(list(self.hook.parent.glob(".commit-message-*")), [])

    def test_atomic_creation_failure_cleans_staging(self):
        self.hook.parent.mkdir()
        with patch.object(module.os, "link", side_effect=OSError("injected creation failure")):
            with self.assertRaises(OSError):
                module.atomic_write(self.hook, TOOL.read_bytes(), 0o755, replace=False)
        self.assertFalse(self.hook.exists())
        self.assertEqual(list(self.hook.parent.glob(".commit-message-*")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
