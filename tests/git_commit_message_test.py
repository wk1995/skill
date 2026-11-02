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
                        GIT_TERMINAL_PROMPT="0", XDG_CONFIG_HOME=str(self.root / "config"))
        self.machine = self.root / "config/git-commit-message/config.json"
        isolated_config = patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.root / "config")})
        isolated_config.start()
        self.addCleanup(isolated_config.stop)
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

    def machine_policy(self, **values):
        self.machine.parent.mkdir(parents=True, exist_ok=True)
        self.machine.write_text(json.dumps(values), encoding="utf-8")

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

    def test_machine_is_opt_in_and_repository_prefixes_default_empty(self):
        self.machine_policy(extra_prefixes=["work"])
        self.tool("fix", self.message, env=self.identity())
        self.assertEqual(self.message.read_text(),
                         "[Test Agent 2.3.4][test-model] fix: login\n\nBody\nSigned-off-by: Test\n")
        self.assertFalse((self.repo / module.POLICY).exists())
        self.assertEqual(module.policy(self.repo)["extra_prefixes"], [])
        self.assertFalse(module.policy(self.repo)["machine_prefix"])

    def test_machine_repository_ai_switch_matrix(self):
        self.machine_policy(extra_prefixes=["work"])
        raw = b"fix: login\n\nBody\n"
        for machine in (False, True):
            for project in (False, True):
                for ai in (False, True):
                    with self.subTest(machine=machine, project=project, ai=ai):
                        self.policy(machine_prefix=machine, repo_prefix=project,
                                    ai_prefix=ai, extra_prefixes=["project"])
                        self.message.write_bytes(raw)
                        groups = (["work"] if machine else []) + (["project"] if project else [])
                        if ai:
                            groups.extend(["Test Agent 2.3.4", "test-model"])
                        expected = ("".join(f"[{value}]" for value in groups) + " ").encode() + raw if groups else raw
                        env = self.identity() if ai else self.env
                        self.tool("check", self.message, env=env, ok=not groups)
                        self.assertEqual(self.message.read_bytes(), raw)
                        self.tool("fix", self.message, env=env)
                        self.assertEqual(self.message.read_bytes(), expected)
                        self.tool("hook", self.message, env=env)
                        self.tool("check", self.message, env=env)
                        self.assertEqual(self.message.read_bytes(), expected)

    def test_shared_machine_repository_values_emitted_once_in_first_position(self):
        self.machine_policy(extra_prefixes=["work", "shared"])
        self.policy(machine_prefix=True, extra_prefixes=["shared", "project"])
        self.message.write_text("[project][shared] [work] fix: login\n")
        self.tool("hook", self.message, env=self.identity())
        expected = "[work][shared][project][Test Agent 2.3.4][test-model] fix: login\n"
        self.assertEqual(self.message.read_text(), expected)
        self.tool("hook", self.message, env=self.identity())
        self.assertEqual(self.message.read_text(), expected)

    def test_machine_reload_check_only_and_all_groups_off(self):
        self.machine_policy(extra_prefixes=["work"])
        self.policy(machine_prefix=True, ai_prefix=False, mode="check")
        raw = self.message.read_bytes()
        self.tool("hook", self.message, ok=False)
        self.assertEqual(self.message.read_bytes(), raw)
        self.tool("fix", self.message)
        self.tool("hook", self.message)
        self.machine_policy(extra_prefixes=["home"])
        self.message.write_bytes(raw)
        self.tool("fix", self.message)
        self.assertTrue(self.message.read_bytes().startswith(b"[home] "))
        self.policy(machine_prefix=False, repo_prefix=False, ai_prefix=False, extra_prefixes=["project"])
        self.message.write_bytes(raw)
        self.tool("hook", self.message)
        self.assertEqual(self.message.read_bytes(), raw)

    def test_all_groups_off_preserves_arbitrary_bytes_without_identity(self):
        self.machine_policy(extra_prefixes=["work"])
        self.policy(machine_prefix=False, repo_prefix=False, ai_prefix=False,
                    extra_prefixes=["project"], mode="check")
        for raw in (b"", b"# comment\n", b"\xff\x00\n", b"subject\r\n\r\nBody\r\n"):
            self.message.write_bytes(raw)
            before = self.message.stat().st_mtime_ns
            for command in ("hook", "fix", "check"):
                self.tool(command, self.message)
                self.assertEqual(self.message.read_bytes(), raw)
                self.assertEqual(self.message.stat().st_mtime_ns, before)

    def test_removed_enabled_rejected_before_every_entry_and_migration_succeeds(self):
        self.tool("install")
        before = self.hook.read_bytes()
        raw = self.message.read_bytes()
        for old_value in (True, False):
            self.policy(enabled=old_value, machine_prefix=False, repo_prefix=False, ai_prefix=False)
            config = (self.repo / module.POLICY).read_bytes()
            for command in ("install", "uninstall", "hook", "fix", "check"):
                args = () if command in ("install", "uninstall") else (self.message,)
                result = self.tool(command, *args, ok=False)
                self.assertIn(b"unknown", result.stderr)
                self.assertIn(b"enabled", result.stderr)
                self.assertEqual(self.hook.read_bytes(), before)
                self.assertEqual(self.message.read_bytes(), raw)
                self.assertEqual((self.repo / module.POLICY).read_bytes(), config)
        self.policy(machine_prefix=False, repo_prefix=False, ai_prefix=False)
        self.commit("-m", "migrated human message")
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), b"migrated human message")

    def test_machine_invalid_configuration_blocks_all_commands_even_disabled(self):
        self.tool("install")
        self.machine.parent.mkdir(parents=True)
        self.policy(machine_prefix=False, repo_prefix=False, ai_prefix=False)
        hook_bytes = self.hook.read_bytes()
        raw = self.message.read_bytes()
        for value in ("{", "[]", '{"extra_prefixes":"work"}', '{"schema_version":true}',
                      '{"extra_prefixes":["work","work"]}', '{"extra_prefixes":["[work]"]}',
                      '{"extra_prefixes":[null]}', '{"enabled":false}',
                      '{"extra_prefixes":[],"extra_prefixes":["work"]}'):
            self.machine.write_text(value)
            for command in ("install", "uninstall", "hook", "check", "fix"):
                with self.subTest(config=value, command=command):
                    args = () if command in ("install", "uninstall") else (self.message,)
                    self.tool(command, *args, ok=False)
                    self.assertEqual(self.hook.read_bytes(), hook_bytes)
                    self.assertEqual(self.message.read_bytes(), raw)
                    self.assertEqual(self.machine.read_text(), value)

    def test_machine_config_symlink_hardlink_and_directory_rejected(self):
        self.tool("install")
        self.machine.parent.mkdir(parents=True)
        external = self.root / "machine-original.json"
        external.write_text('{"extra_prefixes":["work"]}')
        for kind in ("symlink", "hardlink", "directory"):
            if kind == "symlink":
                self.machine.symlink_to(external)
            elif kind == "hardlink":
                os.link(external, self.machine)
            else:
                self.machine.mkdir()
            for command in ("install", "uninstall", "hook", "check", "fix"):
                args = () if command in ("install", "uninstall") else (self.message,)
                self.tool(command, *args, env=self.identity(), ok=False)
                self.assertTrue(self.hook.exists())
                self.assertEqual(external.read_text(), '{"extra_prefixes":["work"]}')
            self.machine.rmdir() if kind == "directory" else self.machine.unlink()

    def test_machine_file_cannot_be_a_message_output_including_case_alias(self):
        self.machine_policy(extra_prefixes=["work"])
        before = self.machine.read_bytes()
        alias = self.machine.with_name("CONFIG.JSON")
        paths = [self.machine]
        if alias.exists() and alias.samefile(self.machine):
            paths.append(alias)
        for path in paths:
            for command in ("hook", "fix", "check"):
                self.tool(command, path, env=self.identity(), ok=False)
                self.assertEqual(self.machine.read_bytes(), before)

    def test_xdg_path_resolution_empty_unset_and_relative_rejection(self):
        fake_home = self.root / "home"
        with patch.object(Path, "home", return_value=fake_home):
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": ""}):
                self.assertEqual(module.machine_policy_path(), fake_home / ".config/git-commit-message/config.json")
            with patch.dict(os.environ):
                os.environ.pop("XDG_CONFIG_HOME", None)
                self.assertEqual(module.machine_policy_path(), fake_home / ".config/git-commit-message/config.json")
        self.tool("install")
        before = self.hook.read_bytes()
        raw = self.message.read_bytes()
        env = {**self.identity(), "XDG_CONFIG_HOME": "relative/config"}
        for command in ("install", "uninstall", "hook", "check", "fix"):
            args = () if command in ("install", "uninstall") else (self.message,)
            self.tool(command, *args, env=env, ok=False)
            self.assertEqual(self.hook.read_bytes(), before)
            self.assertEqual(self.message.read_bytes(), raw)

    def test_real_commit_machine_prefix_opt_in_and_body_preservation(self):
        self.machine_policy(extra_prefixes=["work"])
        self.policy(machine_prefix=True, extra_prefixes=["project"])
        self.tool("install")
        machine_before = self.machine.read_bytes()
        policy_before = (self.repo / module.POLICY).read_bytes()
        self.commit("-F", self.message, env=self.identity())
        result = self.git("log", "-1", "--format=%B").stdout
        self.assertTrue(result.startswith(b"[work][project][Test Agent 2.3.4][test-model] fix: login\n"))
        self.assertIn(b"Body\nSigned-off-by: Test", result)
        self.assertEqual(self.machine.read_bytes(), machine_before)
        self.assertEqual((self.repo / module.POLICY).read_bytes(), policy_before)
        self.policy(machine_prefix=False, repo_prefix=False, ai_prefix=False, extra_prefixes=["project"])
        self.commit("-m", "human subject")
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), b"human subject")

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
            ({"machine_prefix": False, "repo_prefix": False, "ai_prefix": False}, b"fix: login\n"),
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
                   '{"machine_prefix":"true"}', '{"repo_prefix":1}',
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
        self.policy(machine_prefix=False, repo_prefix=False, ai_prefix=False, mode="bad")
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
        self.policy(machine_prefix=False, repo_prefix=False, ai_prefix=False)
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
        self.policy(machine_prefix=False, repo_prefix=False, ai_prefix=False, mode="invalid")
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
        self.machine_policy(extra_prefixes=["work"])
        self.policy(machine_prefix=True)
        source = self.root / "source.py"
        shutil.copyfile(TOOL, source)
        self.run_command([sys.executable, source, "install"])
        source.unlink()
        self.commit("-m", "standalone", env=self.identity())
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(),
                         b"[work][Test Agent 2.3.4][test-model] standalone")

    def test_subdirectory_symlink_root_and_linked_worktree(self):
        self.machine_policy(extra_prefixes=["work"])
        self.tool("install")
        self.commit("-m", "base", env=self.identity())
        linked = self.root / "linked worktree"
        self.git("worktree", "add", "-b", "other", linked)
        (linked / module.POLICY).write_text('{"machine_prefix":true,"ai_prefix":false,"extra_prefixes":["linked"]}')
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
        self.assertEqual(result.stdout.strip(), b"[work][linked] linked subject")
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
