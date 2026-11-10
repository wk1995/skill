#!/usr/bin/env python3
"""Private, local-only email account references. Never executes a mail backend."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

MAX_BYTES = 1024 * 1024
SCHEMA = 1
SKILL_ROOT = Path(__file__).resolve().parents[1]
BACKENDS = {
    "qq": {"qq-email-mcp", "himalaya"},
    "netease": {"himalaya"},
    "gmail": {"gws", "himalaya"},
    "feishu": {"lark-cli"},
    "imap-smtp": {"himalaya"},
}
FIELDS = {"id", "address", "provider", "backend", "instance", "config_path"}
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,62}\Z")
ADDRESS = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}\Z")


class AccountError(Exception):
    """An actionable failure, without echoing account data or credentials."""


def require(condition, message):
    if not condition:
        raise AccountError(message)


def contained(path, parent):
    return path == parent or parent in path.parents


def local_path(value):
    """Validate before mkdir, lock, read, or a caller's other filesystem effects."""
    require(isinstance(value, str) and value and "\x00" not in value,
            "A nonempty absolute local path is required")
    raw = Path(value)
    require(raw.is_absolute(), "Relative private paths are not allowed")
    try:
        path = raw.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise AccountError("Cannot resolve the selected private path") from exc
    require(not contained(path, SKILL_ROOT) and not contained(SKILL_ROOT, path),
            "Private data cannot overlap a Skill source or installation")
    for ancestor in (path, *path.parents):
        require(not os.path.lexists(ancestor / ".git"),
                "Private data cannot be inside a Git worktree")
        require(not (os.path.lexists(ancestor / "HEAD") and
                     (ancestor / "objects").is_dir() and (ancestor / "refs").is_dir()),
                "Private data cannot be inside a bare Git repository")
        require(not os.path.lexists(ancestor / "SKILL.md"),
                "Private data cannot be inside a Skill directory")
    return path


def private_info(info, directory=False):
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
            "A private directory or regular file was expected")
    require(info.st_uid == os.getuid() and not info.st_mode & 0o077,
            "Private storage must be owned by the current user with no group/other access")
    if not directory:
        require(info.st_nlink == 1, "Hard-linked private files are not accepted")


def posix_storage():
    require(os.name == "posix" and hasattr(os, "O_NOFOLLOW"),
            "This helper requires POSIX private storage; no verified Windows ACL adapter is provided")


def separate_locations(locations):
    items = list(locations.values())
    for index, left in enumerate(items):
        for right in items[index + 1:]:
            aliases = left.exists() and right.exists() and os.path.samefile(left, right)
            require(not aliases and not contained(left, right) and not contained(right, left),
                    "Private config, state, cache and data directories must be separate")


def roots(override=None):
    posix_storage()
    if override is not None:
        base = local_path(override)
        values = {name: base / name for name in ("config", "state", "cache", "data")}
    else:
        home = Path.home()
        defaults = {"config": ("XDG_CONFIG_HOME", home / ".config"),
                    "state": ("XDG_STATE_HOME", home / ".local/state"),
                    "cache": ("XDG_CACHE_HOME", home / ".cache"),
                    "data": ("XDG_DATA_HOME", home / ".local/share")}
        values = {}
        for name, (key, default) in defaults.items():
            value = os.environ.get(key)
            parent = local_path(value if value is not None else str(default))
            values[name] = parent / "email-management"
    result = {name: local_path(str(path)) for name, path in values.items()}
    separate_locations(result)
    for path in result.values():
        if os.path.lexists(path):
            private_info(path.lstat(), directory=True)
    return result


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON keys are not accepted")
        result[key] = value
    return result


def decode(data):
    require(len(data) <= MAX_BYTES, "Private JSON exceeds the size limit")
    try:
        return json.loads(data, object_pairs_hook=pairs)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AccountError("Invalid private JSON; the existing file has not been replaced") from exc


def profile(value):
    require(isinstance(value, dict) and set(value) <= FIELDS,
            "Unknown profile fields are rejected; credentials are never accepted")
    require(set(value) >= FIELDS - {"config_path"}, "Missing required account reference fields")
    require(all(isinstance(v, str) and 0 < len(v) <= 4096 and not any(ord(c) < 32 for c in v)
                for v in value.values()), "Account reference fields must be nonempty text without controls")
    require(ID.fullmatch(value["id"]) and ID.fullmatch(value["instance"]),
            "Account and instance IDs must use lowercase letters, digits and hyphens")
    require(ADDRESS.fullmatch(value["address"]), "A supported ASCII email address is required")
    user, domain = value["address"].rsplit("@", 1)
    require(len(value["address"]) <= 254 and len(user) <= 64 and
            not user.startswith(".") and not user.endswith(".") and ".." not in user and
            all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                for label in domain.split(".")), "A supported ASCII email address is required")
    require(value["provider"] in BACKENDS and
            value["backend"] in BACKENDS[value["provider"]],
            "Unsupported provider/backend combination; later-stage providers are not registered here")
    require(value["backend"] not in {"himalaya", "qq-email-mcp"} or "config_path" in value,
            "This backend requires an explicit private native configuration reference")
    clean = dict(value)
    if "config_path" in clean:
        path = local_path(clean["config_path"])
        require(not Path(clean["config_path"]).is_symlink(),
                "Native configuration references must not be symbolic links")
        # Validate identity/permissions only; never open a backend's credential data.
        if path.exists():
            private_info(path.lstat(), directory=path.is_dir())
        clean["config_path"] = str(path)
    return clean


def document(value):
    require(isinstance(value, dict) and set(value) == {"schema_version", "accounts"}
            and type(value["schema_version"]) is int and value["schema_version"] == SCHEMA
            and isinstance(value["accounts"], dict), "Unsupported or damaged private account index")
    seen = set()
    qq_instances, qq_configs = set(), set()
    for key, entry in value["accounts"].items():
        item = profile(entry)
        require(key == item["id"], "Account index identity mismatch")
        require(item["address"].casefold() not in seen, "Duplicate account address in private index")
        seen.add(item["address"].casefold())
        require(item == entry, "Noncanonical native configuration reference; explicitly repair the local index")
        if item["backend"] == "qq-email-mcp":
            require(item["instance"] not in qq_instances and item["config_path"] not in qq_configs,
                    "QQ single-account instances and native configuration must be isolated")
            qq_instances.add(item["instance"])
            qq_configs.add(item["config_path"])
    return value


def read_private(path):
    posix_storage()
    local_path(str(path))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        private_info(os.fstat(fd))
        require(os.fstat(fd).st_size <= MAX_BYTES, "Private JSON exceeds the size limit")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return stream.read(MAX_BYTES + 1)
    finally:
        os.close(fd)


class Store:
    def __init__(self, root=None):
        self.locations = roots(root)
        self.directory = self.locations["config"]

    def validate_files(self):
        # Check every owned path before even an already-current return or mkdir.
        posix_storage()
        roots_now = {name: local_path(str(path)) for name, path in self.locations.items()}
        require(roots_now == self.locations, "Private storage path identity changed")
        separate_locations(roots_now)
        for path in roots_now.values():
            if os.path.lexists(path):
                private_info(path.lstat(), directory=True)
        for name in ("accounts.json", "accounts.json.bak", ".accounts.lock"):
            path = self.directory / name
            if os.path.lexists(path):
                private_info(path.lstat())

    def read(self):
        self.validate_files()
        path = self.directory / "accounts.json"
        if not os.path.lexists(path):
            return {"schema_version": SCHEMA, "accounts": {}}
        return document(decode(read_private(path)))

    def create_directory(self):
        missing = []
        current = self.directory
        while not current.exists():
            missing.append(current)
            current = current.parent
        for path in reversed(missing):
            local_path(str(path))
            try:
                path.mkdir(mode=0o700)
            except FileExistsError:
                pass
            require(not path.is_symlink(), "Private directory changed during creation")
            private_info(path.lstat(), directory=True)
        self.validate_files()

    @contextmanager
    def locked(self):
        self.create_directory()
        directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        lock_fd = None
        try:
            private_info(os.fstat(directory_fd), directory=True)
            require(os.path.samestat(os.fstat(directory_fd), self.directory.stat()),
                    "Private directory identity changed")
            try:
                lock_fd = os.open(".accounts.lock", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                  0o600, dir_fd=directory_fd)
            except FileExistsError as exc:
                raise AccountError("Account index is locked; inspect the local lock before an explicit retry") from exc
            yield directory_fd
        finally:
            if lock_fd is not None:
                # Never remove a different actor's replacement lock.
                try:
                    info = os.stat(".accounts.lock", dir_fd=directory_fd, follow_symlinks=False)
                    if os.path.samestat(info, os.fstat(lock_fd)):
                        os.unlink(".accounts.lock", dir_fd=directory_fd)
                finally:
                    os.close(lock_fd)
            os.close(directory_fd)

    def atomic(self, directory_fd, name, payload):
        require(name in {"accounts.json", "accounts.json.bak"},
                "Only owned account-index filenames can be replaced")
        self.validate_files()
        require(os.path.samestat(os.fstat(directory_fd), self.directory.stat()),
                "Private directory identity changed")
        temporary = ".accounts-" + uuid.uuid4().hex + ".tmp"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory_fd)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(fd)
            self.validate_files()
            require(os.path.samestat(os.fstat(directory_fd), self.directory.stat()),
                    "Private directory identity changed")
            os.replace(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
            os.fsync(directory_fd)
        finally:
            os.close(fd)
            try:
                os.unlink(temporary, dir_fd=directory_fd)
            except FileNotFoundError:
                pass

    def mutate(self, operation):
        old = self.read()
        proposal = operation(json.loads(json.dumps(old)))
        document(proposal)
        payload = (json.dumps(proposal, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        require(len(payload) <= MAX_BYTES, "Account index would exceed the size limit")
        if proposal == old:
            return False
        with self.locked() as fd:
            current = self.read()
            require(current == old, "Account index changed; read it again before an explicit retry")
            previous = self.directory / "accounts.json"
            if previous.exists():
                self.atomic(fd, "accounts.json.bak", read_private(previous))
            self.atomic(fd, "accounts.json", payload)
        return True

    def put(self, incoming, replace=False):
        entry = profile(incoming)
        def apply(value):
            accounts = value["accounts"]
            existing = accounts.get(entry["id"])
            require(existing is None or existing == entry or replace,
                    "Account ID already exists; explicitly select replace for an intentional update")
            for key, other in accounts.items():
                require(key == entry["id"] or other["address"].casefold() != entry["address"].casefold(),
                        "Address already belongs to another local account ID")
                if entry["backend"] == "qq-email-mcp" and other["backend"] == "qq-email-mcp" and key != entry["id"]:
                    require(other["instance"] != entry["instance"] and
                            other.get("config_path") != entry.get("config_path"),
                            "QQ single-account instances and native configuration must be isolated")
            accounts[entry["id"]] = entry
            return value
        return self.mutate(apply)

    def remove(self, account):
        require(ID.fullmatch(account), "Invalid account ID")
        def apply(value):
            value["accounts"].pop(account, None)
            return value
        return self.mutate(apply)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", help="absolute external test/private base; contains config/state/cache/data")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("paths", help="validate and show local directories without creating them")
    check = sub.add_parser("check-path", help="check a proposed external path; never writes it")
    check.add_argument("--path", required=True)
    sub.add_parser("list", help="show IDs, providers, backends and instances; omit addresses and paths")
    show = sub.add_parser("show", help="show one private reference only for an authorized account task")
    show.add_argument("--account", required=True)
    put = sub.add_parser("put", help="read one non-secret JSON profile from stdin; never contacts a backend")
    put.add_argument("--replace", action="store_true")
    remove = sub.add_parser("remove", help="remove only one local reference, not credentials or mail")
    remove.add_argument("--account", required=True)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        store = Store(args.root)
        if args.command == "paths":
            store.validate_files()
            result = {k: str(v) for k, v in store.locations.items()}
        elif args.command == "check-path":
            store.validate_files()
            result = {"path": str(local_path(args.path)), "checked": True}
        elif args.command == "put":
            incoming = decode(sys.stdin.buffer.read(MAX_BYTES + 1))
            result = {"changed": store.put(incoming, replace=args.replace), "connected": False}
        elif args.command == "remove":
            result = {"changed": store.remove(args.account), "credentials_deleted": False}
        else:
            accounts = store.read()["accounts"]
            if args.command == "show":
                require(args.account in accounts, "Selected account was not found; no default account was chosen")
                result = accounts[args.account]
            else:
                result = [{k: item[k] for k in ("id", "provider", "backend", "instance")}
                          for _, item in sorted(accounts.items())]
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (AccountError, OSError) as exc:
        # OS exception strings may include private filenames; never echo them.
        message = str(exc) if isinstance(exc, AccountError) else "Local filesystem operation failed; existing data was not intentionally removed"
        print(json.dumps({"error": message}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
