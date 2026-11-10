"""Disposable synthetic-only storage tests; never read a user's mail or configuration."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(os.environ.get("EMAIL_ACCOUNTS_SCRIPT", Path(__file__).resolve().parents[1] / "scripts/email_accounts.py"))
spec = importlib.util.spec_from_file_location("email_accounts_under_test", SCRIPT)
accounts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accounts)


@unittest.skipUnless(os.name == "posix", "POSIX helper; Windows mutations must fail closed")
class AccountStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="email-management-synthetic-")
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "private"
        self.store = accounts.Store(str(self.root))
        self.alpha = {"id": "alpha", "address": "a@example.invalid", "provider": "gmail",
                      "backend": "gws", "instance": "alpha"}
        self.beta = dict(self.alpha, id="beta", address="b@example.invalid", instance="beta")

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, *arguments, data=None, path=None):
        env = os.environ.copy()
        if path is not None:
            env["PATH"] = path
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(self.root), *arguments],
                              input=None if data is None else json.dumps(data), text=True,
                              capture_output=True, cwd=self.base, env=env)

    def test_read_commands_do_not_create_directories(self):
        for command in [("list",), ("paths",), ("show", "--account", "absent"),
                        ("check-path", "--path", str(self.base / "download"))]:
            with self.subTest(command=command):
                self.cli(*command)
                self.assertFalse(self.root.exists())

    def test_put_reload_remove_sequence_and_private_modes(self):
        self.assertTrue(self.store.put(self.alpha))
        self.assertTrue(self.store.put(self.beta))
        saved = accounts.Store(str(self.root)).read()
        self.assertEqual(saved["accounts"]["alpha"], self.alpha)
        self.assertEqual(stat.S_IMODE(self.store.directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.store.directory / "accounts.json").stat().st_mode), 0o600)
        self.assertTrue(self.store.remove("alpha"))
        self.assertEqual(self.store.read()["accounts"], {"beta": self.beta})
        self.assertFalse(self.store.remove("alpha"))

    def test_same_profile_is_noop_without_rewriting_index_or_backup(self):
        self.store.put(self.alpha)
        target = self.store.directory / "accounts.json"
        before = (target.read_bytes(), target.stat().st_mtime_ns)
        self.assertFalse(self.store.put(self.alpha))
        self.assertEqual(before, (target.read_bytes(), target.stat().st_mtime_ns))
        self.assertFalse((self.store.directory / "accounts.json.bak").exists())

    def test_conflicting_id_requires_explicit_replace(self):
        self.store.put(self.alpha)
        other = dict(self.alpha, address="different@example.invalid")
        before = self.store.read()
        with self.assertRaises(accounts.AccountError):
            self.store.put(other)
        self.assertEqual(self.store.read(), before)
        self.assertTrue(self.store.put(other, replace=True))
        backup = json.loads((self.store.directory / "accounts.json.bak").read_text())
        self.assertEqual(backup, before)

    def test_duplicate_address_rejected_before_first_write(self):
        self.store.put(self.alpha)
        before = sorted(p.name for p in self.store.directory.iterdir())
        with self.assertRaises(accounts.AccountError):
            self.store.put(dict(self.beta, address=self.alpha["address"].upper()))
        self.assertEqual(before, sorted(p.name for p in self.store.directory.iterdir()))

    def test_unknown_and_credential_fields_never_create_storage_or_echo_values(self):
        for field in ("password", "token", "authorization_code", "credential_ref", "capabilities"):
            with self.subTest(field=field):
                result = self.cli("put", data=dict(self.alpha, **{field: "SYNTHETIC_SECRET_CANARY"}))
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("SYNTHETIC_SECRET_CANARY", result.stdout + result.stderr)
                self.assertFalse(self.root.exists())

    def test_provider_and_fields_validation(self):
        for changes in ({"provider": "icloud"}, {"backend": "lark-cli"}, {"id": "../bad"},
                        {"address": "bad\n@example.invalid"}, {"instance": ""}, {"address": 12},
                        {"address": "a@example..invalid"}, {"address": ".a@example.invalid"},
                        {"address": "a@example-.invalid"}):
            with self.subTest(changes=changes):
                with self.assertRaises(accounts.AccountError):
                    self.store.put(dict(self.alpha, **changes))
                self.assertFalse(self.root.exists())

    def test_invalid_profiles_do_not_raise_raw_key_or_type_errors(self):
        for value in (None, [], {}, {"password": "SYNTHETIC"}, dict(self.alpha, instance=None)):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(accounts.AccountError):
                    self.store.put(value)

    def test_native_profile_underscores_are_preserved_without_relaxing_account_ids(self):
        entry = dict(self.alpha, provider="feishu", backend="lark-cli", instance="cli_example")
        result = self.cli("put", data=entry)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.store.read()["accounts"]["alpha"]["instance"], "cli_example")
        self.assertFalse(self.store.put(entry))
        original = (self.store.directory / "accounts.json").read_bytes()
        for changes in ({"id": "local_id"}, {"instance": "../native"}, {"instance": "has space"},
                        {"instance": "Upper"}, {"instance": "x" * 64}):
            with self.subTest(changes=changes):
                with self.assertRaises(accounts.AccountError):
                    self.store.put(dict(entry, **changes), replace=True)
                self.assertEqual((self.store.directory / "accounts.json").read_bytes(), original)

    def test_relative_root_and_xdg_paths_rejected(self):
        with self.assertRaises(accounts.AccountError):
            accounts.Store("relative")
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "relative"}):
            with self.assertRaises(accounts.AccountError):
                accounts.Store()
        self.assertFalse(self.root.exists())

    def test_xdg_roots_cannot_overlap_config_and_cleanable_cache(self):
        for cache in (self.base / "settings", self.base / "settings/email-management/child"):
            env = {"XDG_CONFIG_HOME": str(self.base / "settings"),
                   "XDG_STATE_HOME": str(self.base / "state"),
                   "XDG_CACHE_HOME": str(cache), "XDG_DATA_HOME": str(self.base / "data")}
            with self.subTest(cache=cache.name), mock.patch.dict(os.environ, env):
                with self.assertRaises(accounts.AccountError):
                    accounts.Store()
        self.assertFalse((self.base / "settings").exists())

    def test_git_worktree_bare_repository_and_skill_paths_rejected(self):
        variants = [self.base / name for name in ("repo", "worktree", "bare", "skill")]
        for directory in variants:
            directory.mkdir()
        (variants[0] / ".git").mkdir()
        (variants[1] / ".git").write_text("gitdir: /synthetic-only")
        (variants[2] / "HEAD").write_text("ref: refs/heads/synthetic")
        (variants[2] / "objects").mkdir()
        (variants[2] / "refs").mkdir()
        (variants[3] / "SKILL.md").write_text("Synthetic fixture only")
        for directory in variants:
            with self.subTest(kind=directory.name):
                with self.assertRaises(accounts.AccountError):
                    accounts.Store(str(directory / "missing" / "private"))
                self.assertFalse((directory / "missing").exists())

    def test_native_case_alias_of_git_worktree(self):
        directory = self.base / "CaseRepo"
        directory.mkdir()
        (directory / ".git").mkdir()
        alias = self.base / "cASErEPO"
        if not alias.exists() or not os.path.samefile(alias, directory):
            self.skipTest("Native filesystem is case sensitive; symlink identity matrix remains covered")
        with self.assertRaises(accounts.AccountError):
            accounts.Store(str(alias / "absent"))
        self.assertFalse((directory / "absent").exists())

    def test_symlink_and_missing_descendant_cannot_enter_protected_tree(self):
        protected = self.base / "repo"
        protected.mkdir()
        (protected / ".git").mkdir()
        alias = self.base / "alias"
        alias.symlink_to(protected, target_is_directory=True)
        with self.assertRaises(accounts.AccountError):
            accounts.Store(str(alias / "not-created"))
        self.assertFalse((protected / "not-created").exists())

    def test_own_skill_source_and_ancestor_rejected(self):
        for path in (accounts.SKILL_ROOT, accounts.SKILL_ROOT / "doc/local", accounts.SKILL_ROOT.parent):
            with self.subTest(path=path.name):
                with self.assertRaises(accounts.AccountError):
                    accounts.local_path(str(path))

    def test_all_direct_commands_validate_root_before_effects(self):
        self.root.mkdir()
        (self.root / ".git").mkdir()
        commands = [("put",), ("remove", "--account", "alpha"), ("list",),
                    ("show", "--account", "alpha"), ("paths",),
                    ("check-path", "--path", str(self.base / "file"))]
        for command in commands:
            with self.subTest(command=command):
                result = self.cli(*command, data=self.alpha if command == ("put",) else None)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(sorted(p.name for p in self.root.iterdir()), [".git"])

    def test_directory_file_and_permissive_storage_are_not_repaired(self):
        self.root.mkdir(mode=0o700)
        target = self.root / "config"
        target.write_text("foreign content")
        with self.assertRaises(accounts.AccountError):
            accounts.Store(str(self.root))
        self.assertEqual(target.read_text(), "foreign content")
        target.unlink()
        target.mkdir(mode=0o755)
        target.chmod(0o755)
        with self.assertRaises(accounts.AccountError):
            accounts.Store(str(self.root))
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o755)

    def test_corrupt_duplicate_keys_and_unsupported_schema_preserved(self):
        self.store.put(self.alpha)
        target = self.store.directory / "accounts.json"
        samples = [b"not JSON", b'{"schema_version":1,"schema_version":1,"accounts":{}}',
                   b'{"schema_version":true,"accounts":{}}', b'{"schema_version":2,"accounts":{}}']
        for sample in samples:
            with self.subTest(sample=sample[:15]):
                target.write_bytes(sample)
                with self.assertRaises(accounts.AccountError):
                    self.store.put(self.beta)
                self.assertEqual(target.read_bytes(), sample)
                self.assertFalse((self.store.directory / ".accounts.lock").exists())

    def test_index_id_and_duplicate_address_damage_rejected(self):
        self.store.put(self.alpha)
        target = self.store.directory / "accounts.json"
        samples = [{"wrong": self.alpha}, {"alpha": self.alpha, "beta": dict(self.beta, address=self.alpha["address"])}]
        for entries in samples:
            target.write_text(json.dumps({"schema_version": 1, "accounts": entries}))
            with self.assertRaises(accounts.AccountError):
                self.store.read()

    def test_symlink_and_hardlink_owned_files_rejected_before_lock(self):
        for name in ("accounts.json", "accounts.json.bak", ".accounts.lock"):
            with self.subTest(name=name):
                self.store.create_directory()
                outside = self.base / (name.replace(".", "_") + "-outside")
                outside.write_text("synthetic sentinel")
                outside.chmod(0o600)
                pointer = self.store.directory / name
                pointer.symlink_to(outside)
                with self.assertRaises(accounts.AccountError):
                    self.store.put(self.alpha)
                self.assertEqual(outside.read_text(), "synthetic sentinel")
                pointer.unlink()
                os.link(outside, pointer)
                with self.assertRaises(accounts.AccountError):
                    self.store.put(self.alpha)
                pointer.unlink()

    def test_stale_lock_refuses_mutation_and_is_not_deleted(self):
        self.store.put(self.alpha)
        lock = self.store.directory / ".accounts.lock"
        lock.write_text("synthetic lock owner")
        lock.chmod(0o600)
        old = (self.store.directory / "accounts.json").read_bytes()
        with self.assertRaises(accounts.AccountError):
            self.store.put(self.beta)
        self.assertEqual(lock.read_text(), "synthetic lock owner")
        self.assertEqual((self.store.directory / "accounts.json").read_bytes(), old)

    def test_failed_index_replacement_keeps_old_and_backup(self):
        self.store.put(self.alpha)
        original = self.store.atomic
        def inject(fd, name, payload):
            if name == "accounts.json":
                raise OSError("Synthetic failure, no private data")
            return original(fd, name, payload)
        with mock.patch.object(self.store, "atomic", side_effect=inject):
            with self.assertRaises(OSError):
                self.store.put(self.beta)
        self.assertEqual(self.store.read()["accounts"], {"alpha": self.alpha})
        self.assertEqual(json.loads((self.store.directory / "accounts.json.bak").read_text())["accounts"], {"alpha": self.alpha})
        self.assertFalse((self.store.directory / ".accounts.lock").exists())
        self.assertFalse(list(self.store.directory.glob(".accounts-*.tmp")))
        self.assertTrue(self.store.put(self.beta))
        self.assertFalse(self.store.put(self.beta))

    def test_changed_index_during_lock_acquisition_is_preserved(self):
        self.store.put(self.alpha)
        original = self.store.locked
        @contextlib.contextmanager
        def interleave():
            accounts.Store(str(self.root)).put(self.beta)
            with original() as fd:
                yield fd
        with mock.patch.object(self.store, "locked", side_effect=interleave):
            with self.assertRaises(accounts.AccountError):
                self.store.remove("alpha")
        self.assertEqual(self.store.read()["accounts"], {"alpha": self.alpha, "beta": self.beta})
        self.assertFalse((self.store.directory / ".accounts.lock").exists())

    def test_atomic_replace_os_failure_removes_only_own_temp(self):
        self.store.put(self.alpha)
        sentinel = self.store.directory / "unrelated"
        sentinel.write_text("preserve")
        with mock.patch.object(accounts.os, "replace", side_effect=OSError("synthetic")):
            with self.assertRaises(OSError):
                self.store.put(self.beta)
        self.assertEqual(self.store.read()["accounts"], {"alpha": self.alpha})
        self.assertEqual(sentinel.read_text(), "preserve")
        self.assertFalse(list(self.store.directory.glob(".accounts-*.tmp")))

    def test_atomic_writer_refuses_unowned_names_and_wrong_directory(self):
        self.store.create_directory()
        outside = self.base / "unrelated"
        outside.mkdir(mode=0o700)
        with self.store.locked() as fd:
            for name in ("../outside", "other.json", "/absolute"):
                with self.subTest(name=name):
                    with self.assertRaises(accounts.AccountError):
                        self.store.atomic(fd, name, b"synthetic")
            other_fd = os.open(outside, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(accounts.AccountError):
                    self.store.atomic(other_fd, "accounts.json", b"synthetic")
            finally:
                os.close(other_fd)
        self.assertFalse(list(outside.iterdir()))
        self.assertFalse(list(self.store.directory.glob(".accounts-*.tmp")))

    def test_sensitive_references_rejected_even_on_noop(self):
        native = self.base / "native.json"
        native.write_text("synthetic config, never read")
        native.chmod(0o600)
        entry = dict(self.alpha, config_path=str(native))
        self.store.put(entry)
        native.chmod(0o644)
        before = (self.store.directory / "accounts.json").read_bytes()
        with self.assertRaises(accounts.AccountError):
            self.store.put(entry)
        self.assertEqual((self.store.directory / "accounts.json").read_bytes(), before)

    def test_native_config_is_reference_only_and_never_deleted(self):
        native = self.base / "native.toml"
        native.write_text("SYNTHETIC_SECRET_CANARY")
        native.chmod(0o600)
        entry = dict(self.alpha, provider="qq", backend="qq-email-mcp", config_path=str(native))
        with mock.patch.object(Path, "read_text", side_effect=AssertionError("Must not read backend secrets")):
            self.store.put(entry)
            self.store.remove("alpha")
        self.assertEqual(native.read_text(), "SYNTHETIC_SECRET_CANARY")

    def test_dangling_native_config_symlink_and_oversized_json_reject(self):
        link = self.base / "native-link"
        link.symlink_to(self.base / "not-created")
        with self.assertRaises(accounts.AccountError):
            self.store.put(dict(self.alpha, config_path=str(link)))
        with self.assertRaises(accounts.AccountError):
            accounts.decode(b" " * (accounts.MAX_BYTES + 1))
        self.assertFalse(self.root.exists())

    def test_qq_instances_and_native_config_are_not_shared(self):
        native = self.base / "qq.toml"
        native.write_text("synthetic")
        native.chmod(0o600)
        first = dict(self.alpha, provider="qq", backend="qq-email-mcp", config_path=str(native))
        self.store.put(first)
        second = dict(self.beta, provider="qq", backend="qq-email-mcp", config_path=str(native))
        with self.assertRaises(accounts.AccountError):
            self.store.put(second)
        with self.assertRaises(accounts.AccountError):
            self.store.put(dict(second, config_path=str(self.base / "other.toml"), instance="alpha"))

    def test_existing_qq_isolation_damage_rejected_on_read_and_remove(self):
        first = dict(self.alpha, provider="qq", backend="qq-email-mcp",
                     config_path=str(self.base / "first.toml"))
        self.store.put(first)
        target = self.store.directory / "accounts.json"
        for config, instance in (("first.toml", "beta"), ("other.toml", "alpha")):
            second = dict(self.beta, provider="qq", backend="qq-email-mcp",
                          config_path=str(self.base / config), instance=instance)
            payload = json.dumps({"schema_version": 1, "accounts": {"alpha": first, "beta": second}})
            target.write_text(payload)
            with self.assertRaises(accounts.AccountError):
                self.store.read()
            with self.assertRaises(accounts.AccountError):
                self.store.remove("beta")
            self.assertEqual(target.read_text(), payload)
            self.assertFalse((self.store.directory / ".accounts.lock").exists())

    def test_cli_real_entry_points_and_controlled_empty_path(self):
        result = self.cli("put", data=self.alpha, path="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["connected"])
        listing = self.cli("list", path="")
        self.assertEqual(listing.returncode, 0)
        self.assertNotIn(self.alpha["address"], listing.stdout)
        self.assertNotIn(str(self.root), listing.stdout)
        shown = self.cli("show", "--account", "alpha", path="")
        self.assertEqual(json.loads(shown.stdout), self.alpha)
        removed = self.cli("remove", "--account", "alpha", path="")
        self.assertEqual(removed.returncode, 0)
        self.assertFalse(json.loads(removed.stdout)["credentials_deleted"])

    def test_unsupported_platform_mutations_fail_closed(self):
        root = str(self.root)
        with mock.patch.object(accounts.os, "name", "nt"):
            with self.assertRaises(accounts.AccountError):
                accounts.Store(root)
            with self.assertRaises(accounts.AccountError):
                self.store.put(self.alpha)
            with self.assertRaises(accounts.AccountError):
                self.store.remove("alpha")
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
