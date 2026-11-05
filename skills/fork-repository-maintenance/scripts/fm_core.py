"""Portable filesystem, Git and hosting boundaries; Python standard library only."""
from __future__ import annotations

import contextlib
import ctypes
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid


class Failure(Exception):
    def __init__(self, message, code=3):
        super().__init__(redact(str(message)))
        self.code = code


def require(value, message, code=3):
    if not value:
        raise Failure(message, code)


def redact(value):
    value = re.sub(r'(https?://)[^/\s@]+@', r'\1[redacted]@', str(value))
    value = re.sub(r'(?i)([?&](?:token|password|access_token|key|auth)[^=\s]*=)[^&\s]+', r'\1[redacted]', value)
    value = re.sub(r'\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b', '[redacted]', value)
    return re.sub(r'(?i)(bearer\s+)\S+', r'\1[redacted]', value)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key, 2)
        result[key] = value
    return result


def no_links(path):
    path = Path(os.path.abspath(path))
    # macOS exposes /tmp and /var as root-owned aliases. Canonicalize only these
    # fixed system prefixes; arbitrary/user-created aliases remain rejected.
    if os.name == 'posix' and os.uname().sysname == 'Darwin' and len(path.parts) > 1 and path.parts[1] in ('tmp', 'var'):
        prefix = Path('/') / path.parts[1]
        expected = Path('/private') / path.parts[1]
        if prefix.is_symlink() and prefix.lstat().st_uid == 0 and prefix.resolve() == expected:
            path = expected.joinpath(*path.parts[2:])
    for item in (path, *path.parents):
        require(not item.is_symlink(), 'symbolic-link path is not allowed: ' + str(item))
    return path


def read_json(path):
    path = no_links(path)
    require(path.is_file() and path.stat().st_nlink == 1, 'expected an unaliased regular JSON file: ' + str(path))
    try:
        return json.loads(path.read_text(), object_pairs_hook=unique,
                          parse_constant=lambda x: (_ for _ in ()).throw(Failure('invalid JSON number', 2)))
    except (ValueError, UnicodeError) as error:
        raise Failure('invalid JSON: ' + str(error), 2) from error


def keys(value, allowed, required=()):
    require(isinstance(value, dict), 'expected JSON object', 2)
    require(set(value) <= set(allowed), 'unknown fields: ' + ','.join(sorted(set(value) - set(allowed))), 2)
    require(set(required) <= set(value), 'missing fields: ' + ','.join(sorted(set(required) - set(value))), 2)


def related(a, b):
    a, b = Path(a).resolve(), Path(b).resolve()
    folded_a, folded_b = Path(str(a).casefold()), Path(str(b).casefold())
    if folded_a == folded_b or folded_a.is_relative_to(folded_b) or folded_b.is_relative_to(folded_a):
        return True
    return ((b.exists() and any(x.exists() and os.path.samefile(x, b) for x in (a, *a.parents)))
            or (a.exists() and any(x.exists() and os.path.samefile(x, a) for x in (b, *b.parents))))


def safe_output(path, protected):
    path = no_links(path)
    require(path != Path(path.anchor), 'filesystem root is not an output')
    for other in protected:
        require(not related(path, other), 'output overlaps protected path: ' + str(other))
    return path


def atomic_json(path, value):
    path = no_links(path)
    if path.exists():
        require(path.is_file() and path.stat().st_nlink == 1, 'unsafe state file')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(canonical(value) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        no_links(path)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def new_json(path, value):
    path = no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.plan-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(canonical(value) + b'\n'); stream.flush(); os.fsync(stream.fileno())
        no_links(path)
        os.link(temporary, path)  # Fails atomically if any file/symlink appeared.
    finally:
        Path(temporary).unlink(missing_ok=True)


def publish_directory(staging, target):
    staging, target = no_links(staging), no_links(target)
    library = ctypes.CDLL(None, use_errno=True)
    if os.uname().sysname == 'Darwin' and hasattr(library, 'renamex_np'):
        operation = library.renamex_np
        operation.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        operation.restype = ctypes.c_int
        result = operation(os.fsencode(staging), os.fsencode(target), 4)  # RENAME_EXCL
    elif hasattr(library, 'renameat2'):
        operation = library.renameat2
        operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        operation.restype = ctypes.c_int
        result = operation(-100, os.fsencode(staging), -100, os.fsencode(target), 1)  # RENAME_NOREPLACE
    else:
        raise Failure('exclusive directory publication unavailable; staging retained', 6)
    if result:
        number = ctypes.get_errno()
        raise Failure('exclusive publication failed: ' + os.strerror(number) + '; staging retained', 6)


def disable_filters(repo):
    result = git(repo, 'config', '--get-regexp', r'^filter\..*\.(smudge|clean|process|required)$', check=False)
    for line in result.stdout.splitlines():
        key = line.split(' ', 1)[0]
        suffix = key.rsplit('.', 1)[-1]
        git(repo, 'config', '--replace-all', key, 'false' if suffix == 'required' else ('' if suffix == 'process' else 'cat'))


def run(argv, *, env=None, check=True, cwd=None):
    require(shutil.which(str(argv[0])) is not None, 'missing dependency: ' + str(argv[0]))
    try:
        result = subprocess.run([str(x) for x in argv], cwd=cwd, env=env,
                                text=True, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired as error:
        raise Failure('command timed out; reconcile before retrying a remote write', 5) from error
    except OSError as error:
        raise Failure(str(error), 6) from error
    if check and result.returncode:
        raise Failure(result.stderr.strip() or 'command failed', 6)
    return result


def git(repo, *args, check=True):
    env = os.environ.copy()
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_TEMPLATE_DIR',
                'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS'):
        env.pop(key, None)
    env.update(GIT_NO_REPLACE_OBJECTS='1', GIT_GRAFT_FILE=os.devnull, GIT_TERMINAL_PROMPT='0')
    # Never inherit hooks from a fetched/cloned project. Hosting protections still apply.
    command = ['git', '-c', 'core.hooksPath=' + os.devnull, '-c', 'init.templateDir=', '-c', 'gc.auto=0',
               '-c', 'fetch.writeCommitGraph=false']
    if args and args[0] in ('clone', 'fetch', 'push', 'ls-remote', 'init'):
        # Do not allow inherited URL rewrites/templates/push defaults to redirect
        # a verified transport. GitHub credentials come from the verified gh actor.
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        if any(str(arg).startswith('https://github.com/') for arg in args):
            command += ['-c', 'credential.helper=', '-c', 'credential.https://github.com.helper=!gh auth git-credential']
        if repo is not None:
            redirect = git(repo, 'config', '--local', '--get-regexp',
                           r'^(url\..*\.(insteadof|pushinsteadof)|include\..*|includeif\..*|core\.sshcommand|remote\..*\.pushurl)$', check=False)
            require(redirect.returncode == 1, 'unexpected transport redirection or include configuration')
    if repo is not None:
        command += ['-C', str(repo)]
    return run(command + list(args), env=env, check=check)


def check_git():
    version = git(None, '--version').stdout
    match = re.search(r'(\d+)\.(\d+)', version)
    require(match and tuple(map(int, match.groups())) >= (2, 45), 'Git 2.45+ is required')


def workspace_roots():
    # A projectless shell may be in HOME or a parent of many repositories.
    # Protect actual worktrees and this installed Skill, not every child of cwd.
    roots = [Path(__file__).resolve().parents[1]]
    result = git(None, 'rev-parse', '--show-toplevel', check=False)
    if result.returncode == 0:
        roots.append(Path(result.stdout.strip()).resolve())
    return roots


def branch(name):
    require(isinstance(name, str) and name and not name.startswith('-'), 'invalid branch name', 2)
    require(not any(c in name for c in '\r\n\x00'), 'invalid branch characters', 2)
    require(git(None, 'check-ref-format', 'refs/heads/' + name, check=False).returncode == 0,
            'invalid branch name: ' + name, 2)
    return name


def oid(value):
    require(isinstance(value, str) and re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', value), 'invalid object ID', 2)
    return value


def names_available(names):
    for name in names:
        branch(name)
    ordered = sorted(set(names))
    for i, left in enumerate(ordered):
        for right in ordered[i + 1:]:
            require(left.casefold() != right.casefold(), 'case-only branch alias: ' + left)
            require(not right.casefold().startswith(left.casefold() + '/')
                    and not left.casefold().startswith(right.casefold() + '/'), 'branch namespace collision: ' + left)


def select(heads, scope, requested):
    require(scope in ('single', 'selected', 'all'), 'invalid scope', 2)
    require(isinstance(requested, list) and all(isinstance(x, str) for x in requested), 'invalid branch list', 2)
    require((scope == 'all' and not requested) or (scope == 'single' and len(requested) == 1)
            or (scope == 'selected' and requested), 'scope and branch arguments disagree', 2)
    for name in requested:
        branch(name)
        require(name in heads, 'unknown upstream branch: ' + name)
    result = sorted(heads if scope == 'all' else set(requested))
    require(result, 'empty upstream branch selection', 2)
    return result


class Provider:
    """GitHub production adapter, or explicit local bare-repository adapter."""
    def __init__(self, kind, source, destination):
        require(kind in ('github', 'local'), 'unsupported provider', 2)
        self.kind = kind
        self.source = self.normalize(source)
        self.destination = self.normalize(destination)
        require(self.source != self.destination, 'source and destination are the same repository')
        if kind == 'local':
            require(not related(self.source, self.destination), 'local source/destination paths overlap or alias')
        self.profile_id = digest([kind, self.destination])[:32]

    def normalize(self, value):
        require(isinstance(value, str) and value, 'missing repository', 2)
        require(redact(value) == value, 'credential-bearing repository URL rejected')
        if self.kind == 'local':
            return str(no_links(value).resolve())
        value = re.sub(r'^https://github.com/', '', value)
        require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value), 'use GitHub owner/repository (github.com)', 2)
        return value.removesuffix('.git').lower()

    def transport(self, side):
        value = self.source if side == 'a' else self.destination
        return value if self.kind == 'local' else 'https://github.com/' + value + '.git'

    def api(self, path, method='GET', body=None, missing=False):
        command = ['gh', 'api', '--hostname', 'github.com', '--method', method,
                   '-H', 'X-GitHub-Api-Version: 2026-03-10', path]
        for key, value in (body or {}).items():
            command += ['-F' if isinstance(value, bool) else '-f', key + '=' + (str(value).lower() if isinstance(value, bool) else value)]
        result = run(command, check=False)
        if missing and result.returncode and re.search(r'HTTP 404\b', result.stderr):
            return None
        require(result.returncode == 0, result.stderr or 'GitHub API failed', 6)
        try:
            return json.loads(result.stdout, object_pairs_hook=unique) if result.stdout.strip() else {}
        except ValueError as error:
            raise Failure('invalid GitHub response', 6) from error

    def actor(self):
        if self.kind == 'local':
            return 'local:' + str(os.getuid())
        run(['gh', 'auth', 'status'])
        return self.api('user')['login']

    def metadata(self, side, missing=False):
        value = self.source if side == 'a' else self.destination
        if self.kind == 'local':
            path = Path(value)
            if not path.exists() and missing:
                return None
            require(path.is_dir() and git(path, 'rev-parse', '--is-bare-repository').stdout.strip() == 'true',
                    'local adapter requires bare repositories')
            default = git(path, 'symbolic-ref', 'HEAD').stdout.strip().removeprefix('refs/heads/')
            return {'id': digest(['local', str(path), path.stat().st_dev, path.stat().st_ino]), 'default': default}
        data = self.api('repos/' + value, missing=missing)
        if data is None:
            return None
        require(isinstance(data.get('id'), int) and isinstance(data.get('default_branch'), str), 'incomplete repository metadata')
        return {'id': str(data['id']), 'default': data['default_branch'], 'parent': str(data.get('parent', {}).get('id', ''))}

    def heads(self, side):
        output = git(None, 'ls-remote', '--heads', self.transport(side)).stdout
        result = {}
        for line in output.splitlines():
            sha, ref = line.split('\t', 1)
            require(ref.startswith('refs/heads/'), 'unexpected remote ref')
            result[branch(ref[11:])] = oid(sha)
        return result

    def tags(self, side):
        output = git(None, 'ls-remote', '--tags', '--refs', self.transport(side)).stdout
        return {ref: oid(sha) for sha, ref in (line.split('\t', 1) for line in output.splitlines())}

    def create(self, expected_actor):
        require(self.actor() == expected_actor, 'authenticated account changed')
        if self.kind == 'local':
            require(not Path(self.destination).exists(), 'destination already exists')
            git(None, 'init', '--bare', self.destination)
        else:
            owner, name = self.destination.split('/')
            body = {'name': name, 'default_branch_only': True}
            if owner.lower() != expected_actor.lower():
                body['organization'] = owner
            data = self.api('repos/' + self.source + '/forks', 'POST', body)
            require(isinstance(data.get('id'), int), 'fork response has no repository identity', 5)
            return {'id': str(data['id']), 'default': data.get('default_branch', '')}
        return self.metadata('b')

    def set_default(self, name):
        if self.kind == 'local':
            git(self.destination, 'symbolic-ref', 'HEAD', 'refs/heads/' + branch(name))
        else:
            self.api('repos/' + self.destination, 'PATCH', {'default_branch': branch(name)})
        require(self.metadata('b')['default'] == name, 'default branch setting was not verified', 5)

    def verify_parent(self, a, b):
        if self.kind == 'github':
            require(b.get('parent') == a['id'], 'destination is not a direct fork of the selected source')


class Store:
    def __init__(self, root, provider=None):
        self.root = no_links(root)
        if self.root.exists():
            require(self.root.is_dir() and self.root.stat().st_uid == os.getuid()
                    and not self.root.stat().st_mode & 0o022, 'state root must be owned and not group/world writable')
        self.provider = provider
        protected = workspace_roots()
        if provider and provider.kind == 'local':
            protected += [provider.source, provider.destination]
        safe_output(self.root, protected)

    def path(self, section, identifier):
        require(re.fullmatch(r'[a-f0-9]{32}', identifier or ''), 'invalid state identifier', 2)
        return no_links(self.root / section / (identifier + '.json'))

    def profile(self, identifier):
        result = read_json(self.path('profiles', identifier))
        validate_profile(result)
        require(result['id'] == identifier, 'profile identity mismatch')
        return result

    def cache(self, identifier):
        require(re.fullmatch(r'[a-f0-9]{32}', identifier or ''), 'invalid cache identifier', 2)
        return no_links(self.root / 'cache' / identifier)

    @contextlib.contextmanager
    def lock(self, identifier):
        require(os.name == 'posix', 'mutations currently require macOS or Linux')
        import fcntl
        path = self.path('locks', identifier)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(path, flags, 0o600)
        try:
            require(os.fstat(fd).st_nlink == 1, 'aliased lock file')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise Failure('another local operation owns this repository lock') from error
            yield
        finally:
            os.close(fd)


def validate_profile(value):
    fields = ('schema_version', 'id', 'provider', 'source', 'destination', 'a_id', 'b_id',
              'personal_default', 'default_base', 'initial_oid', 'sources', 'personal', 'revision', 'fork_operation')
    keys(value, fields, fields)
    require(value['schema_version'] == 1, 'unsupported profile schema', 2)
    require(all(isinstance(value[k], str) and value[k] for k in ('a_id', 'b_id')), 'invalid repository IDs', 2)
    require(isinstance(value['fork_operation'], str) and re.fullmatch(r'[a-f0-9]{32}', value['fork_operation']), 'invalid fork operation', 2)
    provider = Provider(value['provider'], value['source'], value['destination'])
    require(provider.profile_id == value['id'], 'invalid profile key')
    branch(value['personal_default']); branch(value['default_base']); oid(value['initial_oid'])
    require(type(value['revision']) is int and value['revision'] >= 1, 'invalid profile revision', 2)
    require(isinstance(value['sources'], dict) and isinstance(value['personal'], list), 'invalid branch roles', 2)
    for name, record in value['sources'].items():
        branch(name)
        keys(record, ('initial_oid', 'last_verified_remote_oid'), ('initial_oid', 'last_verified_remote_oid'))
        oid(record['initial_oid']); oid(record['last_verified_remote_oid'])
    for name in value['personal']:
        branch(name)
    require(value['personal_default'] in value['personal'], 'default must have personal role')
    require(value['default_base'] in value['sources'] and len(value['personal']) == len(set(value['personal'])), 'invalid initial base or duplicate personal roles')
    require(not set(value['sources']) & set(value['personal']), 'source/personal role collision')
    names_available([*value['sources'], *value['personal']])


def prepare_cache(store, provider, refs, refresh):
    cache = store.cache(provider.profile_id)
    marker = {'provider': provider.kind, 'source': provider.source, 'destination': provider.destination}
    if cache.exists():
        require(cache.is_dir() and read_json(cache / 'owner.json') == marker, 'unowned object cache')
        require(not (cache / 'objects/info/alternates').exists(), 'object cache has external alternates')
        for item in cache.rglob('*'):
            require(not item.is_symlink(), 'symlink in object cache')
    if refresh:
        if not cache.exists():
            cache.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            git(None, 'init', '--bare', str(cache))
            atomic_json(cache / 'owner.json', marker)
        batch = uuid.uuid4().hex
        for side, reference, expected in refs:
            require(reference.startswith(('refs/heads/', 'refs/tags/')), 'invalid fetch namespace')
            oid(expected)
            destination = 'refs/fm-input/' + batch + '/' + side + '/' + reference[5:]
            git(cache, 'fetch', '--no-tags', '--refmap=', provider.transport(side), reference + ':' + destination)
            observed = git(cache, 'rev-parse', '--verify', destination).stdout.strip()
            require(observed == expected, 'source changed during preparation; replan')
    require(cache.is_dir(), 'objects not prepared; plan with --refresh before applying')
    for _, _, expected in refs:
        require(git(cache, 'cat-file', '-e', expected, check=False).returncode == 0,
                'required object unavailable; plan with --refresh')
    require(git(cache, 'rev-parse', '--is-shallow-repository').stdout.strip() == 'false', 'full Git history is required; unshallow the source explicitly')
    return cache


def ancestor(cache, old, new):
    result = git(cache, 'merge-base', '--is-ancestor', oid(old), oid(new), check=False)
    require(result.returncode == 0, 'source diverged or ancestry cannot be verified')


def publish_ref(cache, provider, name, desired, expected, *, source=True):
    branch(name)
    if expected is not None:
        oid(expected)
        ancestor(cache, expected, desired)
    oid(desired)
    actual = provider.heads('b').get(name)
    require(actual == expected, 'destination changed before publication: ' + name)
    lease = '--force-with-lease=refs/heads/' + name + ':' + (expected or '')
    git(cache, 'push', '--porcelain', lease, provider.transport('b'), desired + ':refs/heads/' + name)
    require(provider.heads('b').get(name) == desired, 'remote result not verified', 5)


def new_id():
    return uuid.uuid4().hex
