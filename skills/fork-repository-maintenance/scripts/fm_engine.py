"""Plan, execute and reconcile manual fork maintenance operations."""
from __future__ import annotations

import datetime as dt
import hashlib
import os
from pathlib import Path
import re
import tempfile

from fm_core import (Failure, Provider, Store, ancestor, atomic_json, branch, canonical,
                     check_git, digest, git, keys, names_available, new_id, no_links, now,
                     oid, prepare_cache, publish_ref, read_json, require, run, safe_output,
                     select, validate_profile, new_json, publish_directory, disable_filters, workspace_roots)

COMMON = {'schema_version', 'id', 'kind', 'provider', 'source', 'destination', 'profile_id',
          'a_id', 'b_id', 'actor', 'created_at', 'expires_at', 'entries', 'profile_digest', 'protected', 'digest'}
EXTRA = {'fork': {'scope', 'requested', 'default_name', 'base', 'bootstrap', 'checkout'},
         'sync': {'scope', 'requested', 'new_branches'},
         'integrate': {'source_name', 'source_oid', 'target', 'result_branch', 'base_oid', 'picks', 'strategy', 'validation'},
         'preserve': {'snapshot_scope', 'include_tags', 'archive_root'},
         'restore': {'snapshot', 'destination_path'}}


def provider_of(value):
    return Provider(value['provider'], value['source'], value['destination'])


def context(store, identifier):
    profile = store.profile(identifier)
    provider = provider_of(profile)
    # Validate runtime root containment using the actual registered repositories.
    Store(store.root, provider)
    return profile, provider


def online(profile, provider):
    a = provider.metadata('a')
    b = provider.metadata('b')
    require(a['id'] == profile['a_id'] and b['id'] == profile['b_id'], 'repository identity changed')
    provider.verify_parent(a, b)
    require(b['default'] == profile['personal_default'], 'personal default setting changed')
    ah, bh = provider.heads('a'), provider.heads('b')
    require(profile['personal_default'] in bh, 'personal default reference missing')
    return a, b, ah, bh


def finish_plan(plan, args, store):
    plan['digest'] = digest(plan)
    validate_plan(plan)
    if args.save_plan:
        path = safe_output(args.save_plan, [*workspace_roots(), store.root])
        if plan['provider'] == 'local':
            safe_output(path, [plan['source'], plan['destination']])
        require(not path.exists(), 'plan output already exists')
        new_json(path, plan)
    return {'status': 'planned', 'plan': plan, 'approval_digest': plan['digest'],
            'remote_verified': False, 'local_prepared': bool(args.refresh)}


def validate_plan_output(args, store, provider):
    if args.save_plan:
        protected = [*workspace_roots(), store.root]
        if provider.kind == 'local': protected += [provider.source, provider.destination]
        path = safe_output(args.save_plan, protected)
        require(not path.exists(), 'plan output already exists')


def skeleton(kind, provider, profile=None):
    a = provider.metadata('a')
    b = provider.metadata('b', missing=True)
    return {'schema_version': 1, 'id': new_id(), 'kind': kind, 'provider': provider.kind,
            'source': provider.source, 'destination': provider.destination,
            'profile_id': provider.profile_id, 'a_id': a['id'], 'b_id': b['id'] if b else None,
            'actor': provider.actor(), 'created_at': now(),
            'expires_at': (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24)).isoformat(),
            'entries': [], 'protected': {}, 'profile_digest': digest(profile) if profile else None}


def validate_plan(plan):
    require(isinstance(plan, dict) and plan.get('kind') in EXTRA, 'unsupported operation kind', 2)
    keys(plan, COMMON | EXTRA[plan['kind']], COMMON | EXTRA[plan['kind']])
    require(plan['schema_version'] == 1 and re.fullmatch(r'[0-9a-f]{32}', plan['id']), 'invalid plan schema/id', 2)
    unsigned = {k: v for k, v in plan.items() if k != 'digest'}
    require(plan['digest'] == digest(unsigned), 'plan digest mismatch', 2)
    provider = provider_of(plan)
    require(provider.profile_id == plan['profile_id'], 'plan profile identity mismatch', 2)
    require(isinstance(plan['actor'], str) and plan['actor'], 'invalid plan actor', 2)
    try:
        expiration = dt.datetime.fromisoformat(plan['expires_at'])
        creation = dt.datetime.fromisoformat(plan['created_at'])
        require(expiration.tzinfo is not None and creation.tzinfo is not None and expiration > creation, 'invalid plan time', 2)
        require(expiration > dt.datetime.now(dt.timezone.utc), 'plan expired; replan', 2)
    except (ValueError, TypeError) as error:
        raise Failure('invalid plan timestamps', 2) from error
    require(isinstance(plan['protected'], dict) and isinstance(plan['entries'], list), 'invalid plan records', 2)
    for name, sha in plan['protected'].items():
        branch(name); oid(sha)
    seen = set()
    for entry in plan['entries']:
        if plan['kind'] in ('fork', 'sync'):
            keys(entry, ('name', 'before', 'after', 'action'), ('name', 'before', 'after', 'action'))
            name = branch(entry['name']); oid(entry['after'])
            require(name not in seen, 'duplicate target entry', 2); seen.add(name)
            if entry['before'] is not None:
                oid(entry['before'])
            require(entry['action'] in ('create', 'fast-forward', 'noop', 'skip'), 'invalid source action', 2)
            if entry['action'] == 'create':
                require(entry['before'] is None, 'create requires expected absence', 2)
            if entry['action'] in ('fast-forward', 'noop'):
                require(entry['before'] is not None, 'existing update has no expected old value', 2)
            if entry['action'] == 'noop':
                require(entry['before'] == entry['after'], 'invalid no-op', 2)
            if entry['action'] != 'skip':
                require(name not in plan['protected'], 'personal reference in source write set')
        elif plan['kind'] == 'preserve':
            keys(entry, ('side', 'ref', 'oid', 'bundle_ref'), ('side', 'ref', 'oid', 'bundle_ref'))
            require(entry['side'] in ('a', 'b') and entry['ref'].startswith(('refs/heads/', 'refs/tags/')), 'invalid snapshot namespace', 2)
            require(git(None, 'check-ref-format', entry['ref'], check=False).returncode == 0, 'invalid snapshot reference', 2)
            require(entry['bundle_ref'] == 'refs/fm-archive/' + entry['side'] + '/' + entry['ref'][5:], 'invalid archive reference', 2)
            require(entry['bundle_ref'] not in seen, 'duplicate snapshot reference', 2); seen.add(entry['bundle_ref'])
            oid(entry['oid'])
        else:
            require(not plan['entries'], 'unexpected operation entries', 2)
    if plan['kind'] in ('fork', 'sync'):
        require(plan['scope'] in ('single', 'selected', 'all'), 'invalid scope', 2)
        require(isinstance(plan['requested'], list) and plan['requested'] == sorted(set(plan['requested'])), 'invalid frozen selection', 2)
        require(sorted(seen) == plan['requested'], 'entries differ from frozen selection', 2)
        if plan['scope'] == 'single':
            require(len(seen) == 1, 'single scope needs one entry', 2)
    if plan['kind'] == 'fork':
        require(isinstance(plan['checkout'], str) and plan['checkout'], 'invalid checkout path', 2)
        name = branch(plan['default_name']); branch(plan['base'])
        require(name not in seen and plan['base'] in seen and seen, 'invalid personal default/base')
        keys(plan['bootstrap'], ('name', 'oid'), ('name', 'oid'))
        branch(plan['bootstrap']['name']); oid(plan['bootstrap']['oid'])
        if plan['bootstrap']['name'] in seen:
            require(plan['base'] == plan['bootstrap']['name'], 'default base must use selected upstream default')
        names_available([*seen, name])
        require(all(e['action'] != 'skip' for e in plan['entries']), 'fork cannot skip selected branches', 2)
    if plan['kind'] == 'sync':
        require(plan['new_branches'] in ('existing-only', 'include-new'), 'invalid new-branch policy', 2)
        require(plan['protected'] and plan['profile_digest'], 'sync needs registered personal roles')
        require(all(e['action'] != 'create' or plan['new_branches'] == 'include-new' for e in plan['entries']), 'existing-only cannot create branches')
    if plan['kind'] == 'integrate':
        for field in ('source_name', 'target', 'result_branch'): branch(plan[field])
        oid(plan['source_oid'])
        require(plan['strategy'] in ('merge', 'rebase', 'cherry-pick'), 'unsupported integration strategy', 2)
        require(isinstance(plan['picks'], list), 'invalid patch list', 2)
        for sha in plan['picks']: oid(sha)
        require(isinstance(plan['validation'], list), 'invalid validation commands', 2)
        for command in plan['validation']:
            require(isinstance(command, list) and command and all(isinstance(x, str) and '\x00' not in x for x in command), 'validation must be an argv array', 2)
        if plan['strategy'] == 'rebase':
            oid(plan['base_oid'])
            require(plan['result_branch'] != plan['target'], 'published rebase must use a new personal branch')
        if plan['strategy'] == 'cherry-pick':
            require(plan['picks'], 'cherry-pick requires explicit commits', 2)
    if plan['kind'] == 'preserve':
        require(isinstance(plan['archive_root'], str) and plan['archive_root'], 'invalid archive root', 2)
        require(plan['snapshot_scope'] in ('a', 'b', 'both') and type(plan['include_tags']) is bool,
                'invalid snapshot selection', 2)
        require(plan['entries'], 'snapshot selection is empty', 2)
        names_available([e['bundle_ref'] for e in plan['entries']])
    if plan['kind'] == 'restore':
        keys(plan['snapshot'], ('path', 'manifest_digest'), ('path', 'manifest_digest'))
        require(isinstance(plan['snapshot']['path'], str) and isinstance(plan['destination_path'], str), 'invalid restore paths', 2)
        require(re.fullmatch(r'[0-9a-f]{64}', plan['snapshot']['manifest_digest']), 'invalid manifest digest', 2)


def refs_for(plan):
    if plan['kind'] in ('fork', 'sync'):
        result = [('a', 'refs/heads/' + e['name'], e['after']) for e in plan['entries']]
        result += [('b', 'refs/heads/' + e['name'], e['before']) for e in plan['entries'] if e['before']]
        if plan['kind'] == 'fork':
            result += [('a', 'refs/heads/' + plan['bootstrap']['name'], plan['bootstrap']['oid'])]
    elif plan['kind'] == 'preserve':
        result = [(e['side'], e['ref'], e['oid']) for e in plan['entries']]
    else:
        result = [('b', 'refs/heads/' + plan['source_name'], plan['source_oid']),
                  ('b', 'refs/heads/' + plan['target'], plan['protected'][plan['target']])]
    return list(dict.fromkeys(result))


def prepare(plan, args, store):
    cache = prepare_cache(store, provider_of(plan), refs_for(plan), args.refresh)
    if plan['kind'] in ('fork', 'sync'):
        for entry in plan['entries']:
            if entry['before'] and entry['action'] not in ('skip',):
                ancestor(cache, entry['before'], entry['after'])
    return cache


def plan_fork(args, store):
    provider = Provider(args.provider, args.source, args.destination)
    Store(store.root, provider)
    validate_plan_output(args, store, provider)
    a = provider.metadata('a'); b = provider.metadata('b', missing=True)
    if b:
        profiles = no_links(store.root / 'profiles')
        if profiles.exists():
            for path in profiles.glob('*.json'):
                registered = read_json(path); validate_profile(registered)
                require(not (registered['provider'] == provider.kind and registered['b_id'] == b['id']),
                        'destination already registered; use its profile or an explicit migration')
    ah = provider.heads('a'); bh = provider.heads('b') if b else {}
    if b: provider.verify_parent(a, b)
    requested = select(ah, args.scope, args.branch)
    base = a['default'] if a['default'] in requested else args.default_base
    require(base in requested, 'choose --default-base from the selected source branches')
    require(not args.default_base or args.default_base == base, 'explicit base conflicts with upstream-default priority')
    name = branch(args.default_name)
    require(name not in bh and name not in requested, 'personal default name already exists or is a source')
    require(name != a['default'], 'personal name collides with native bootstrap branch')
    names_available([*bh, *requested, name])
    checkout = safe_output(args.checkout, [store.root, *workspace_roots(), *([provider.source, provider.destination] if provider.kind == 'local' else [])])
    require(not checkout.exists(), 'checkout path must not exist')
    if b:
        require(a['default'] in requested or a['default'] not in bh, 'cannot delete bootstrap branch of a reused repository')
        require(not (set(bh) - set(requested)), 'reused repository has extra branches; explicit migration required')
    require(not store.path('profiles', provider.profile_id).exists(), 'profile already registered; use sync or inspect')
    plan = skeleton('fork', provider)
    plan.update(scope=args.scope, requested=requested, default_name=name, base=base,
                bootstrap={'name': a['default'], 'oid': ah[a['default']]}, checkout=str(checkout))
    for name in requested:
        before = bh.get(name)
        plan['entries'].append({'name': name, 'before': before, 'after': ah[name],
                                'action': 'create' if before is None else ('noop' if before == ah[name] else 'fast-forward')})
    prepare(plan, args, store)
    return finish_plan(plan, args, store)


def plan_sync(args, store):
    profile, provider = context(store, args.profile)
    validate_plan_output(args, store, provider)
    _, _, ah, bh = online(profile, provider)
    requested = select(ah, args.scope, args.branch)
    require(args.new_branches in ('existing-only', 'include-new'), 'invalid new branch policy', 2)
    plan = skeleton('sync', provider, profile)
    plan.update(scope=args.scope, requested=requested, new_branches=args.new_branches)
    plan['protected'] = {name: bh[name] for name in profile['personal'] if name in bh}
    for name in requested:
        before = bh.get(name)
        if name in profile['personal']:
            require(args.scope == 'all' and args.new_branches == 'existing-only', 'personal name collides with selected source')
            action = 'skip'
        elif name in profile['sources'] and before:
            require(before == profile['sources'][name]['last_verified_remote_oid'], 'registered source changed: ' + name)
            action = 'noop' if before == ah[name] else 'fast-forward'
        elif args.new_branches == 'existing-only':
            action = 'skip'
        else:
            require(before is None, 'unregistered existing branch cannot be adopted: ' + name)
            action = 'create'
        plan['entries'].append({'name': name, 'before': before, 'after': ah[name], 'action': action})
    names_available([*bh, *(e['name'] for e in plan['entries'] if e['action'] != 'skip')])
    prepare(plan, args, store)
    return finish_plan(plan, args, store)


def plan_integrate(args, store):
    profile, provider = context(store, args.profile)
    validate_plan_output(args, store, provider)
    _, _, _, bh = online(profile, provider)
    require(args.source_name in profile['sources'], 'integration source must be a registered source branch')
    require(args.target in profile['personal'] and args.target in bh, 'integration target must be a personal branch')
    source_oid = oid(args.source_oid or bh[args.source_name])
    require(source_oid == profile['sources'][args.source_name]['last_verified_remote_oid'] == bh[args.source_name], 'sync the requested source version first')
    result_name = branch(args.result_branch or args.target)
    require(result_name not in profile['sources'], 'integration cannot write source branch')
    if result_name != args.target:
        require(result_name not in bh, 'new personal maintenance line already exists')
        names_available([*bh, result_name])
    plan = skeleton('integrate', provider, profile)
    plan.update(source_name=args.source_name, source_oid=source_oid, target=args.target,
                result_branch=result_name, base_oid=args.base_oid, picks=args.pick,
                strategy=args.strategy, validation=args.validation)
    plan['protected'] = {name: bh[name] for name in profile['personal'] if name in bh}
    # Validate operation-specific fields before object preparation can write a cache.
    preliminary = dict(plan, digest=digest(plan)); validate_plan(preliminary)
    cache = prepare(plan, args, store)
    if args.strategy == 'rebase':
        ancestor(cache, args.base_oid, bh[args.target])
        ancestor(cache, args.base_oid, source_oid)
        require(not git(cache, 'rev-list', '--merges', args.base_oid + '..' + bh[args.target]).stdout.strip(),
                'rebase of merge history needs a reviewed topology plan; use merge')
    for sha in args.pick:
        require(git(cache, 'cat-file', '-t', sha).stdout.strip() == 'commit', 'patch must be a commit')
        ancestor(cache, sha, source_oid)
    return finish_plan(plan, args, store)


def plan_preserve(args, store):
    profile, provider = context(store, args.profile)
    validate_plan_output(args, store, provider)
    online(profile, provider)
    plan = skeleton('preserve', provider, profile)
    archive = no_links(args.archive_root or store.root / 'snapshots')
    validate_archive_root(archive, store, provider)
    plan.update(snapshot_scope=args.snapshot_scope, include_tags=args.include_tags, archive_root=str(archive))
    for side in ('a', 'b') if args.snapshot_scope == 'both' else (args.snapshot_scope,):
        refs = {'refs/heads/' + n: sha for n, sha in provider.heads(side).items()}
        if args.include_tags: refs.update(provider.tags(side))
        for ref, sha in sorted(refs.items()):
            plan['entries'].append({'side': side, 'ref': ref, 'oid': sha,
                                    'bundle_ref': 'refs/fm-archive/' + side + '/' + ref[5:]})
    preliminary = dict(plan, digest=digest(plan)); validate_plan(preliminary)
    prepare(plan, args, store)
    return finish_plan(plan, args, store)


def snapshot_manifest(path):
    path = no_links(path)
    require(path.is_dir(), 'snapshot directory missing')
    manifest = read_json(path / 'manifest.json')
    fields = ('schema_version', 'snapshot_id', 'created_at', 'profile', 'entries', 'bundle_sha256', 'exclusions', 'git_complete')
    keys(manifest, fields, fields)
    require(manifest['schema_version'] == 1 and manifest['git_complete'] is True, 'unsupported or incomplete Git snapshot')
    validate_profile(manifest['profile'])
    require(isinstance(manifest['entries'], list) and manifest['entries'], 'invalid snapshot entries')
    seen = set()
    for entry in manifest['entries']:
        keys(entry, ('side', 'ref', 'oid', 'bundle_ref'), ('side', 'ref', 'oid', 'bundle_ref'))
        require(entry['side'] in ('a', 'b'), 'invalid snapshot side')
        require(entry['ref'].startswith(('refs/heads/', 'refs/tags/')) and git(None, 'check-ref-format', entry['ref'], check=False).returncode == 0, 'invalid snapshot ref')
        require(entry['bundle_ref'] == 'refs/fm-archive/' + entry['side'] + '/' + entry['ref'][5:], 'snapshot namespace mismatch')
        require(entry['bundle_ref'] not in seen, 'duplicate snapshot ref'); seen.add(entry['bundle_ref'])
        oid(entry['oid'])
    names_available([e['bundle_ref'] for e in manifest['entries']])
    bundle = no_links(path / 'history.bundle')
    require(bundle.is_file() and bundle.stat().st_nlink == 1, 'unsafe bundle file')
    require(file_digest(bundle) == manifest['bundle_sha256'], 'snapshot bundle checksum mismatch')
    with bundle.open('rb') as stream:
        require(stream.readline() in (b'# v2 git bundle\n', b'# v3 git bundle\n'), 'unsupported bundle format')
        total = 0
        while True:
            line = stream.readline(65537); total += len(line)
            require(line and total < 1024 * 1024, 'malformed bundle header')
            if line == b'\n': break
            require(not line.startswith(b'-'), 'incremental bundle cannot be restored independently')
    heads = {}
    for line in git(None, 'bundle', 'list-heads', str(bundle)).stdout.splitlines():
        sha, ref = line.split(' ', 1); heads[ref] = sha
    require(heads == {e['bundle_ref']: e['oid'] for e in manifest['entries']}, 'bundle refs disagree with manifest')
    return manifest


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def plan_restore(args, store):
    manifest = snapshot_manifest(args.snapshot)
    profile = manifest['profile']; provider = provider_of(profile)
    validate_plan_output(args, store, provider)
    target = safe_output(args.destination_path, [store.root, args.snapshot, *workspace_roots(), *([provider.source, provider.destination] if provider.kind == 'local' else [])])
    require(not target.exists(), 'restore destination must not exist; choose a new empty directory')
    required = 'refs/heads/' + profile['personal_default']
    require(any(e['side'] == 'b' and e['ref'] == required for e in manifest['entries']), 'snapshot excludes the B personal default; cannot restore B independently')
    plan = {'schema_version': 1, 'id': new_id(), 'kind': 'restore', 'provider': profile['provider'],
            'source': profile['source'], 'destination': profile['destination'], 'profile_id': profile['id'],
            'a_id': profile['a_id'], 'b_id': profile['b_id'], 'actor': 'offline', 'created_at': now(),
            'expires_at': (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24)).isoformat(),
            'entries': [], 'profile_digest': digest(profile), 'protected': {},
            'snapshot': {'path': str(Path(args.snapshot).absolute()), 'manifest_digest': digest(manifest)},
            'destination_path': str(target)}
    return finish_plan(plan, args, store)


def inspect(args, store):
    profile, provider = context(store, args.profile)
    result = {'status': 'inspected', 'profile': profile, 'remote_verified': False}
    if not args.offline:
        _, _, ah, bh = online(profile, provider)
        result['branches'] = {name: {'a': ah.get(name), 'b': bh.get(name),
                            'status': 'source-missing' if name not in ah else
                            ('origin-changed' if bh.get(name) != rec['last_verified_remote_oid'] else
                             ('current' if ah[name] == bh.get(name) else 'update-available'))}
                              for name, rec in profile['sources'].items()}
        result['remote_verified'] = True
        result['new_upstream_branches'] = sorted(set(ah) - set(profile['sources']))
    return result


def operation_load(store, plan):
    path = store.path('operations', plan['id'])
    if not path.exists(): return None
    operation = read_json(path)
    fields = ('schema_version', 'id', 'plan', 'status', 'receipts', 'intents', 'created_b_id',
              'original_profile', 'proposed_profile', 'candidate', 'stage', 'recovery_paths')
    keys(operation, fields, fields)
    require(operation['schema_version'] == 1 and operation['id'] == plan['id'] and operation['plan'] == plan, 'operation/plan mismatch')
    require(isinstance(operation['receipts'], dict) and isinstance(operation['intents'], list), 'invalid operation receipts')
    require(operation['status'] in ('running','completed','partial','uncertain','failed','aborted'), 'invalid operation status')
    require(operation['stage'] in ('validated','fork-requested','fork-created','personal-created','default-verified',
                                   'checkout-ready','integration-started','candidate-review','already-applied'), 'invalid operation stage')
    allowed = {'refs/heads/' + e['name'] for e in plan['entries'] if plan['kind'] in ('fork','sync') and e['action'] != 'skip'} if plan['kind'] in ('fork','sync') else set()
    if plan['kind'] == 'fork':
        allowed.update('refs/heads/' + plan[k] for k in ('default_name', 'base'))
        allowed.add('refs/heads/' + plan['bootstrap']['name'])
    if plan['kind'] == 'integrate': allowed.update('refs/heads/'+plan[k] for k in ('target','result_branch'))
    require(set(operation['receipts']) <= allowed and set(operation['intents']) <= allowed, 'unexpected receipt or send target')
    require(len(operation['intents']) == len(set(operation['intents'])), 'duplicate send intent')
    for sha in operation['receipts'].values(): oid(sha)
    for field in ('original_profile','proposed_profile'):
        if operation[field] is not None: validate_profile(operation[field])
    if operation['original_profile'] is not None:
        require(digest(operation['original_profile']) == plan['profile_digest'], 'original profile differs from plan')
    require(isinstance(operation['recovery_paths'], list) and all(isinstance(x,str) for x in operation['recovery_paths']), 'invalid recovery paths')
    return operation


def new_operation(plan, profile):
    return {'schema_version': 1, 'id': plan['id'], 'plan': plan, 'status': 'running', 'receipts': {},
            'intents': [], 'created_b_id': None, 'original_profile': profile, 'proposed_profile': None,
            'candidate': None, 'stage': 'validated', 'recovery_paths': []}


def save_operation(store, op):
    atomic_json(store.path('operations', op['id']), op)


def profile_for_apply(store, plan, operation):
    profile = store.profile(plan['profile_id'])
    allowed = [plan['profile_digest']]
    if operation:
        for candidate in (operation['original_profile'], operation['proposed_profile']):
            if candidate:
                validate_profile(candidate); allowed.append(digest(candidate))
    require(digest(profile) in allowed, 'profile changed since plan; replan')
    require(profile['provider'] == plan['provider'] and profile['source'] == plan['source'] and profile['destination'] == plan['destination'], 'profile transport mismatch')
    require(profile['a_id'] == plan['a_id'] and profile['b_id'] == plan['b_id'], 'plan repository identities differ from profile')
    return profile


def publish_with_receipt(store, op, cache, provider, name, desired, expected, source=True):
    require(provider.actor() == op['plan']['actor'], 'authenticated account changed before write')
    current = provider.heads('b').get(name)
    key = 'refs/heads/' + name
    if key in op['receipts']:
        require(op['receipts'][key] == desired and current == desired, 'previously verified remote reference changed')
        return
    if current == desired and key in op['intents']:
        op['receipts'][key] = desired; save_operation(store, op); return
    require(current == expected, 'destination changed before write: ' + name)
    if key not in op['intents']:
        op['intents'].append(key); save_operation(store, op)
    # Pin the old object before the only remote mutation, without modifying user refs.
    if expected:
        git(cache, 'update-ref', 'refs/fm-anchor/' + op['id'] + '/' + name, expected)
    publish_ref(cache, provider, name, desired, expected, source=source)
    op['receipts'][key] = desired; save_operation(store, op)


def preflight_source(store, plan, profile, op):
    provider = provider_of(plan)
    require(provider.actor() == plan['actor'], 'authenticated account changed')
    a = provider.metadata('a'); b = provider.metadata('b', missing=True)
    require(a['id'] == plan['a_id'], 'source identity changed')
    ah = provider.heads('a'); bh = provider.heads('b') if b else {}
    if plan['kind'] == 'fork' and store.path('profiles', plan['profile_id']).exists():
        registered = store.profile(plan['profile_id'])
        require(op and registered['fork_operation'] == plan['id'], 'registered fork cannot be reinitialized')
    if b:
        expected_id = (op or {}).get('created_b_id') or plan['b_id']
        require(b['id'] == expected_id, 'destination identity changed or creation outcome unknown', 5)
        provider.verify_parent(a, b)
    elif plan['b_id'] is not None or (op and op['created_b_id']):
        raise Failure('previous destination is no longer accessible')
    if profile:
        require(b and b['default'] == profile['personal_default'], 'personal default setting drifted')
        for name, expected in plan['protected'].items():
            require(bh.get(name) == expected, 'personal reference changed after planning: ' + name)
    for entry in plan['entries']:
        require(ah.get(entry['name']) == entry['after'], 'upstream advanced after planning; replan')
        if entry['action'] == 'skip': continue
        if profile:
            require(entry['name'] not in profile['personal'], 'source update targets personal role')
            if entry['name'] not in profile['sources']:
                require(plan['kind'] == 'sync' and plan['new_branches'] == 'include-new' and entry['action'] == 'create', 'unregistered source target')
            else:
                original = (op or {}).get('original_profile') or profile
                require(entry['before'] is None or original['sources'][entry['name']]['last_verified_remote_oid'] == entry['before'], 'source baseline differs from plan')
        current = bh.get(entry['name'])
        receipt_key = 'refs/heads/' + entry['name']
        after_write = op and (receipt_key in op['receipts'] or receipt_key in op['intents'])
        # A newly created native Fork may already contain exactly the bootstrap SHA.
        native = plan['kind'] == 'fork' and op and op['created_b_id'] and current == entry['after']
        require(current == entry['before'] or ((after_write or native) and current == entry['after']), 'destination entry differs from approved plan')
    if plan['kind'] == 'fork':
        require(provider.metadata('a')['default'] == plan['bootstrap']['name'], 'upstream default changed')
        require(ah.get(plan['bootstrap']['name']) == plan['bootstrap']['oid'], 'bootstrap source changed')
        for name, sha in bh.items():
            allowed = {e['name']: e['after'] for e in plan['entries']}
            allowed[plan['bootstrap']['name']] = plan['bootstrap']['oid']
            allowed[plan['default_name']] = next(e['after'] for e in plan['entries'] if e['name'] == plan['base'])
            require(name in allowed and (sha == allowed[name] or sha == next((e['before'] for e in plan['entries'] if e['name'] == name), None)), 'unexpected branch in initializing fork')
    return provider


def apply_sync(store, plan, profile, op, cache):
    provider = provider_of(plan)
    failures = []
    for entry in plan['entries']:
        if entry['action'] == 'skip': continue
        try:
            # Recheck protected names immediately before each independent publication.
            require(provider.metadata('b')['default'] == profile['personal_default'], 'default setting changed')
            for name, sha in plan['protected'].items():
                require(provider.heads('b').get(name) == sha, 'personal branch changed concurrently')
            publish_with_receipt(store, op, cache, provider, entry['name'], entry['after'], entry['before'])
        except Failure as error:
            failures.append({'name': entry['name'], 'error': str(error), 'code': error.code})
            # Stop after an uncertain send or global role drift. Never roll back verified items.
            break
    updated = {**profile, 'sources': {k: dict(v) for k, v in profile['sources'].items()}}
    for entry in plan['entries']:
        if op['receipts'].get('refs/heads/' + entry['name']) == entry['after']:
            updated['sources'].setdefault(entry['name'], {'initial_oid': entry['after'], 'last_verified_remote_oid': entry['after']})
            updated['sources'][entry['name']]['last_verified_remote_oid'] = entry['after']
    if updated['sources'] != profile['sources']:
        updated['revision'] += 1
    op['proposed_profile'] = updated; save_operation(store, op)
    atomic_json(store.path('profiles', profile['id']), updated)
    unconfirmed = any(ref not in op['receipts'] for ref in op['intents'])
    op['status'] = 'uncertain' if failures and (unconfirmed or any(e['code'] == 5 for e in failures)) else ('partial' if failures else 'completed')
    save_operation(store, op)
    return {'status': op['status'], 'operation_id': op['id'], 'receipts': op['receipts'],
            'failures': failures, 'remote_verified': not failures,
            'exit_code': (5 if op['status'] == 'uncertain' else 4) if failures else 0}


def apply_fork(store, plan, op, cache):
    provider = provider_of(plan)
    b = provider.metadata('b', missing=True)
    if not b:
        require(not op['created_b_id'], 'created fork is missing or inaccessible', 5)
        require(op['stage'] != 'fork-requested', 'creation outcome unknown; reconcile instead of repeating POST', 5)
        op['stage'] = 'fork-requested'; save_operation(store, op)
        b = provider.create(plan['actor'])
        op['created_b_id'] = b['id']; op['stage'] = 'fork-created'; save_operation(store, op)
        if provider.kind == 'local':
            boot = plan['bootstrap']
            publish_with_receipt(store, op, cache, provider, boot['name'], boot['oid'], None)
            provider.set_default(boot['name'])
    if op['created_b_id']:
        require(b['id'] == op['created_b_id'], 'created fork identity changed')
    else:
        require(plan['b_id'] == b['id'], 'unknown fork creation result', 5)
    provider.verify_parent(provider.metadata('a'), provider.metadata('b'))
    for entry in plan['entries']:
        current = provider.heads('b').get(entry['name'])
        if current == entry['after'] and op['created_b_id']:
            op['receipts']['refs/heads/' + entry['name']] = current; save_operation(store, op)
        else:
            publish_with_receipt(store, op, cache, provider, entry['name'], entry['after'], entry['before'])
    baseline = next(e['after'] for e in plan['entries'] if e['name'] == plan['base'])
    publish_with_receipt(store, op, cache, provider, plan['default_name'], baseline, None, source=False)
    op['stage'] = 'personal-created'; save_operation(store, op)
    current_default = provider.metadata('b')['default']
    require(current_default in (plan['bootstrap']['name'], plan['default_name']), 'concurrent default setting change')
    if current_default != plan['default_name']:
        provider.set_default(plan['default_name'])
    op['stage'] = 'default-verified'; save_operation(store, op)
    if plan['bootstrap']['name'] not in plan['requested']:
        boot = plan['bootstrap']; bh = provider.heads('b')
        if boot['name'] in bh:
            require(op['created_b_id'] and bh[boot['name']] == boot['oid'], 'bootstrap is not an unchanged owned branch')
            require(provider.metadata('b')['default'] == plan['default_name'], 'bootstrap is still default')
            git(cache, 'update-ref', 'refs/fm-anchor/' + op['id'] + '/bootstrap', boot['oid'])
            git(cache, 'push', '--porcelain', '--force-with-lease=refs/heads/' + boot['name'] + ':' + boot['oid'],
                provider.transport('b'), ':refs/heads/' + boot['name'])
    expected = {e['name']: e['after'] for e in plan['entries']}
    expected[plan['default_name']] = baseline
    require(provider.heads('b') == expected and provider.metadata('b')['default'] == plan['default_name'], 'fork final refs/default not verified', 5)
    profile = {'schema_version': 1, 'id': plan['profile_id'], 'provider': plan['provider'], 'source': plan['source'],
               'destination': plan['destination'], 'a_id': plan['a_id'], 'b_id': provider.metadata('b')['id'],
               'personal_default': plan['default_name'], 'default_base': plan['base'], 'initial_oid': baseline,
               'sources': {e['name']: {'initial_oid': e['after'], 'last_verified_remote_oid': e['after']} for e in plan['entries']},
               'personal': [plan['default_name']], 'revision': 1, 'fork_operation': plan['id']}
    validate_profile(profile)
    checkout = safe_output(plan['checkout'], [store.root, *workspace_roots(), *([provider.source, provider.destination] if provider.kind == 'local' else [])])
    if checkout.exists():
        require(read_json(checkout / '.git/fm-operation.json') == {'operation_id': op['id']}, 'checkout already exists and is not owned by this operation')
        require(git(checkout, 'remote', 'get-url', 'origin').stdout.strip() == provider.transport('b'), 'checkout origin changed')
    else:
        checkout.parent.mkdir(parents=True, exist_ok=True)
        staging = checkout.parent / ('.' + checkout.name + '-' + op['id'])
        require(not staging.exists(), 'clone staging exists; retain it and choose recovery explicitly')
        op['recovery_paths'] = [str(staging)]; save_operation(store, op)
        git(None, 'clone', '--no-local', '--no-checkout', '--origin', 'origin', '--branch', plan['default_name'], provider.transport('b'), str(staging))
        disable_filters(staging)
        git(staging, 'checkout', plan['default_name'])
        git(staging, 'remote', 'add', 'upstream', provider.transport('a'))
        atomic_json(staging / '.git/fm-operation.json', {'operation_id': op['id']})
        require(not checkout.exists(), 'checkout appeared during clone')
        publish_directory(staging, checkout)
    op['proposed_profile'] = profile; save_operation(store, op)
    atomic_json(store.path('profiles', profile['id']), profile)
    op['status'] = 'completed'; op['stage'] = 'checkout-ready'; save_operation(store, op)
    return {'status': 'completed', 'profile_id': profile['id'], 'operation_id': op['id'], 'checkout': str(checkout), 'remote_verified': True}


def validate_archive_root(archive, store, provider):
    archive = no_links(archive)
    if archive != store.root / 'snapshots':
        safe_output(archive, [store.root, *workspace_roots(), *([provider.source, provider.destination] if provider.kind == 'local' else [])])
    if archive.exists():
        require(archive.is_dir(), 'archive root is not a directory')
        marker = archive / '.fm-archive.json'
        require((not any(archive.iterdir())) or (marker.is_file() and read_json(marker) == {'kind': 'fork-maintenance-snapshots'}), 'archive directory is not owned by this tool')
    return archive


def apply_preserve(store, plan, profile, op, cache):
    archive = validate_archive_root(plan['archive_root'], store, provider_of(plan))
    target = no_links(archive / plan['id'])
    if target.exists():
        manifest = snapshot_manifest(target)
        require(manifest['snapshot_id'] == plan['id'] and manifest['entries'] == plan['entries'], 'snapshot differs from operation')
    else:
        root = target.parent; root.mkdir(parents=True, exist_ok=True, mode=0o700)
        atomic_json(root / '.fm-archive.json', {'kind': 'fork-maintenance-snapshots'})
        staging = no_links(root / ('.staging-' + plan['id']))
        require(not staging.exists(), 'snapshot staging retained from failure; inspect recovery path')
        staging.mkdir(mode=0o700)
        op['recovery_paths'] = [str(staging)]; save_operation(store, op)
        for entry in plan['entries']:
            git(cache, 'update-ref', entry['bundle_ref'], entry['oid'])
        bundle = staging / 'history.bundle'
        git(cache, 'bundle', 'create', str(bundle), *(e['bundle_ref'] for e in plan['entries']))
        exclusions = ['platform metadata/attachments', 'uncommitted worktrees', 'Git configuration and credentials', 'LFS payloads', 'submodule repositories']
        manifest = {'schema_version': 1, 'snapshot_id': plan['id'], 'created_at': now(), 'profile': profile,
                    'entries': plan['entries'], 'bundle_sha256': file_digest(bundle), 'exclusions': exclusions, 'git_complete': True}
        atomic_json(staging / 'manifest.json', manifest)
        snapshot_manifest(staging)
        with tempfile.TemporaryDirectory(prefix='fm-verify-') as temp:
            git(None, 'init', '--bare', temp)
            git(temp, 'bundle', 'verify', str(bundle))
            git(temp, 'fetch', '--no-tags', str(bundle), *(e['bundle_ref'] + ':' + e['bundle_ref'] for e in plan['entries']))
            git(temp, 'fsck', '--full', '--strict')
            for entry in plan['entries']:
                require(git(temp, 'rev-parse', entry['bundle_ref']).stdout.strip() == entry['oid'], 'independent snapshot ref mismatch')
        require(not target.exists(), 'snapshot destination appeared')
        publish_directory(staging, target)
    op['status'] = 'completed'; save_operation(store, op)
    return {'status': 'completed', 'operation_id': op['id'], 'snapshot': str(target), 'git_complete': True,
            'project_complete': False, 'exclusions': manifest['exclusions'], 'remote_verified': False}


def apply_restore(store, plan, op):
    manifest = snapshot_manifest(plan['snapshot']['path'])
    require(digest(manifest) == plan['snapshot']['manifest_digest'], 'snapshot manifest changed')
    target = safe_output(plan['destination_path'], [store.root, plan['snapshot']['path'], *workspace_roots()])
    provider = provider_of(manifest['profile'])
    if provider.kind == 'local': safe_output(target, [provider.source, provider.destination])
    if target.exists():
        require(read_json(target / '.git/fm-operation.json') == {'operation_id': op['id']}, 'restore destination not owned by operation')
        for entry in manifest['entries']:
            if entry['side'] == 'b':
                require(git(target, 'rev-parse', entry['ref']).stdout.strip() == entry['oid'], 'restored reference changed')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = no_links(target.parent / ('.' + target.name + '-' + op['id']))
        require(not staging.exists(), 'restore staging retained; inspect recovery path')
        op['recovery_paths'] = [str(staging)]; save_operation(store, op)
        git(None, 'init', str(staging))
        disable_filters(staging)
        bundle = Path(plan['snapshot']['path']) / 'history.bundle'
        mappings = [(e['bundle_ref'], e['ref'] if e['side'] == 'b' else 'refs/fm-archive/a/' + e['ref'][5:]) for e in manifest['entries']]
        git(staging, 'fetch', '--no-tags', str(bundle), *(src + ':' + dst for src, dst in mappings))
        git(staging, 'fsck', '--full', '--strict')
        for entry, (_, destination) in zip(manifest['entries'], mappings):
            require(git(staging, 'rev-parse', destination).stdout.strip() == entry['oid'], 'restored object identity mismatch')
        personal = manifest['profile']['personal_default']
        git(staging, 'symbolic-ref', 'HEAD', 'refs/heads/' + personal)
        git(staging, 'reset', '--mixed', 'HEAD')
        git(staging, 'checkout-index', '--all')
        git(staging, 'remote', 'add', 'origin', provider.transport('b'))
        git(staging, 'remote', 'add', 'upstream', provider.transport('a'))
        atomic_json(staging / '.git/fm-operation.json', {'operation_id': op['id']})
        atomic_json(staging / '.git/fm-restored-profile.json', manifest['profile'])
        require(not target.exists(), 'restore destination appeared during publication')
        publish_directory(staging, target)
    op['status'] = 'completed'; save_operation(store, op)
    return {'status': 'completed', 'operation_id': op['id'], 'destination': str(target),
            'remote_verified': False, 'remote_default_status': 'unverified', 'exclusions': manifest['exclusions']}


def apply_integrate(store, plan, profile, op, cache, *, continuing=False, abort=False):
    provider = provider_of(plan)
    bh = provider.heads('b')
    require(provider.metadata('b')['id'] == profile['b_id'], 'destination identity changed')
    require(provider.metadata('b')['default'] == profile['personal_default'], 'default setting changed')
    require(plan['target'] in profile['personal'] and plan['result_branch'] not in profile['sources'], 'integration role violation')
    if op['status'] == 'completed' and not abort:
        require(op['receipts'] and all(bh.get(ref.removeprefix('refs/heads/')) == sha for ref, sha in op['receipts'].items()), 'completed integration remote changed')
        return {'status': 'completed', 'operation_id': op['id'], 'receipts': op['receipts'], 'remote_verified': True}
    preflight_integrate(store, plan, profile, op, cache)
    require(bh.get(plan['source_name']) == plan['source_oid'] == profile['sources'][plan['source_name']]['last_verified_remote_oid'], 'integration source changed')
    remaining = list(plan['picks'])
    if plan['strategy'] == 'cherry-pick':
        remaining = []
        for sha in plan['picks']:
            if git(cache, 'merge-base', '--is-ancestor', sha, bh[plan['target']], check=False).returncode == 0:
                continue
            comparison = git(cache, 'cherry', bh[plan['target']], sha).stdout.splitlines()
            if any(line == '- ' + sha for line in comparison):
                continue
            remaining.append(sha)
        if not remaining and not abort:
            op['receipts']['refs/heads/' + plan['target']] = bh[plan['target']]
            op['status'] = 'completed'; op['stage'] = 'already-applied'; save_operation(store, op)
            return {'status': 'completed', 'reason': 'all patches already applied', 'operation_id': op['id'], 'remote_verified': True}
    candidate = no_links(store.root / 'candidates' / plan['id'])
    if op['candidate']:
        require(op['candidate'] == str(candidate) and candidate.is_dir(), 'invalid/missing integration candidate')
    else:
        require(not candidate.exists(), 'unowned candidate exists')
        candidate.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        op['candidate'] = str(candidate); op['recovery_paths'] = [str(candidate)]; save_operation(store, op)
        git(None, 'clone', '--no-local', '--no-checkout', '--branch', plan['target'], provider.transport('b'), str(candidate))
        disable_filters(candidate)
        git(candidate, 'checkout', plan['target'])
        git(candidate, 'fetch', '--no-tags', str(cache), plan['source_oid'])
        internal_branch = 'fm-candidate-' + plan['id']
        if internal_branch == plan['target']: internal_branch += '-result'
        git(candidate, 'switch', '-c', internal_branch)
        atomic_json(candidate / '.git/fm-operation.json', {'operation_id': op['id']})
    require(read_json(candidate / '.git/fm-operation.json') == {'operation_id': op['id']}, 'candidate ownership mismatch')
    active = {'merge': (candidate / '.git/MERGE_HEAD').exists(),
              'rebase': (candidate / '.git/rebase-merge').exists() or (candidate / '.git/rebase-apply').exists(),
              'cherry-pick': (candidate / '.git/CHERRY_PICK_HEAD').exists() or (candidate / '.git/sequencer').exists()}
    if abort:
        if active.get(plan['strategy']):
            git(candidate, plan['strategy'], '--abort')
        op['status'] = 'aborted'; save_operation(store, op)
        return {'status': 'aborted', 'candidate': str(candidate), 'remote_verified': False}
    require(op['status'] != 'aborted', 'operation was aborted; create a new plan')
    if op['stage'] == 'validated':
        op['stage'] = 'integration-started'; save_operation(store, op)
        if plan['strategy'] == 'merge':
            result = git(candidate, 'merge', '--no-ff', '--no-commit', plan['source_oid'], check=False)
        elif plan['strategy'] == 'rebase':
            result = git(candidate, 'rebase', '--onto', plan['source_oid'], plan['base_oid'], check=False)
        else:
            result = git(candidate, 'cherry-pick', '--no-commit', *remaining, check=False)
        op['stage'] = 'candidate-review'; save_operation(store, op)
    else:
        result = None
    dirty = git(candidate, 'status', '--porcelain').stdout
    active_now = any((candidate / '.git' / path).exists() for path in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'rebase-merge', 'rebase-apply', 'sequencer'))
    if dirty or active_now or (result is not None and result.returncode):
        return {'status': 'candidate-review', 'operation_id': op['id'], 'candidate': str(candidate),
                'next_action': 'resolve/continue the Git operation and commit using repository commit policy, then resume; abort preserves original target',
                'remote_verified': False}
    desired = git(candidate, 'rev-parse', 'HEAD').stdout.strip()
    if plan['strategy'] == 'cherry-pick':
        require(desired != plan['protected'][plan['target']], 'patch integration has no reviewed commit; retain candidate and replan')
        ancestor(candidate, plan['protected'][plan['target']], desired)
    if plan['strategy'] == 'merge':
        ancestor(candidate, plan['protected'][plan['target']], desired)
        ancestor(candidate, plan['source_oid'], desired)
    if plan['strategy'] == 'rebase':
        ancestor(candidate, plan['source_oid'], desired)
    if not plan['validation']:
        return {'status': 'unverified', 'operation_id': op['id'], 'candidate': str(candidate), 'remote_verified': False}
    for command in plan['validation']:
        validation = run(command, cwd=candidate, check=False)
        if validation.returncode:
            return {'status': 'verification-failed', 'operation_id': op['id'], 'candidate': str(candidate), 'remote_verified': False}
    require(not git(candidate, 'status', '--porcelain').stdout, 'validation changed candidate worktree')
    require(git(candidate, 'rev-parse', 'HEAD').stdout.strip() == desired, 'validation changed candidate commit')
    expected = plan['protected'][plan['target']] if plan['result_branch'] == plan['target'] else None
    require(provider.heads('b').get(plan['source_name']) == plan['source_oid']
            and provider.metadata('b')['default'] == profile['personal_default'], 'source/default changed during validation')
    # Publish only from the controlled object store, never from a checkout whose
    # configuration may have been changed by an approved validation command.
    git(cache, 'fetch', '--no-tags', '--refmap=', str(candidate), desired + ':refs/fm-candidate/' + op['id'])
    publish_with_receipt(store, op, cache, provider, plan['result_branch'], desired, expected, source=False)
    updated = dict(profile, personal=sorted(set(profile['personal'] + [plan['result_branch']])))
    if updated['personal'] != profile['personal']: updated['revision'] += 1
    op['proposed_profile'] = updated; save_operation(store, op)
    atomic_json(store.path('profiles', profile['id']), updated)
    op['status'] = 'completed'; save_operation(store, op)
    return {'status': 'completed', 'operation_id': op['id'], 'candidate': str(candidate), 'result_branch': plan['result_branch'], 'oid': desired, 'remote_verified': True}


def preflight_integrate(store, plan, profile, op, cache):
    provider = provider_of(plan)
    require(plan['a_id'] == profile['a_id'] and plan['b_id'] == profile['b_id'], 'integration identity differs from profile')
    require(plan['source_name'] in profile['sources'] and plan['target'] in profile['personal'], 'integration role violation')
    require(plan['result_branch'] not in profile['sources'], 'integration result is a source branch')
    bh = provider.heads('b')
    require(plan['target'] in plan['protected'] and set(plan['protected']) <= set(profile['personal']), 'invalid protected personal references')
    require(bh.get(plan['source_name']) == plan['source_oid'] == profile['sources'][plan['source_name']]['last_verified_remote_oid'], 'integration source changed')
    desired = None
    if op and op['candidate']:
        candidate = no_links(store.root / 'candidates' / plan['id'])
        require(op['candidate'] == str(candidate) and read_json(candidate / '.git/fm-operation.json') == {'operation_id': plan['id']}, 'invalid candidate ownership')
        desired = git(candidate, 'rev-parse', 'HEAD').stdout.strip()
    result_ref = 'refs/heads/' + plan['result_branch']
    sent = op and (result_ref in op['intents'] or result_ref in op['receipts'])
    for name, before in plan['protected'].items():
        reconciled = name == plan['result_branch'] and sent and desired and bh.get(name) == desired
        require(bh.get(name) == before or reconciled, 'personal reference changed after planning: ' + name)
    if plan['result_branch'] != plan['target']:
        require(bh.get(plan['result_branch']) is None or (sent and desired == bh.get(plan['result_branch'])), 'new personal result already exists')
        names_available([*bh, plan['result_branch']])
    if plan['strategy'] == 'rebase':
        ancestor(cache, plan['base_oid'], plan['protected'][plan['target']])
        ancestor(cache, plan['base_oid'], plan['source_oid'])
        require(not git(cache, 'rev-list', '--merges', plan['base_oid'] + '..' + plan['protected'][plan['target']]).stdout.strip(), 'rebase of merge history requires a topology plan')
    for sha in plan['picks']:
        require(git(cache, 'cat-file', '-t', sha).stdout.strip() == 'commit', 'patch must be a commit')
        ancestor(cache, sha, plan['source_oid'])


def apply(args, store, *, continuing=False, abort=False):
    if args.operation:
        saved = read_json(store.path('operations', args.operation))
        require(isinstance(saved, dict) and isinstance(saved.get('plan'), dict), 'invalid operation record')
        plan = saved['plan']
    else:
        plan = read_json(args.plan)
    validate_plan(plan)
    require(args.approve_plan == plan['digest'], 'explicit matching --approve-plan is required')
    if args.command not in ('resume', 'abort'):
        require(args.command == plan['kind'], 'plan kind does not match direct command')
    provider = provider_of(plan)
    Store(store.root, provider)
    op = operation_load(store, plan)
    profile = None
    if plan['kind'] not in ('fork', 'restore'):
        profile = profile_for_apply(store, plan, op)
    if plan['kind'] in ('sync', 'fork'):
        preflight_source(store, plan, profile, op)
        cache = prepare_cache(store, provider, refs_for(plan), False)
        for entry in plan['entries']:
            if entry['before'] and entry['action'] != 'skip': ancestor(cache, entry['before'], entry['after'])
    elif plan['kind'] == 'restore':
        manifest = snapshot_manifest(plan['snapshot']['path'])
        require(digest(manifest) == plan['snapshot']['manifest_digest'], 'snapshot changed after planning')
        require(manifest['profile']['id'] == plan['profile_id'] and digest(manifest['profile']) == plan['profile_digest'], 'restore profile differs from approved snapshot')
        require(any(e['side'] == 'b' and e['ref'] == 'refs/heads/' + manifest['profile']['personal_default'] for e in manifest['entries']), 'snapshot excludes the B personal default')
        target = safe_output(plan['destination_path'], [store.root, plan['snapshot']['path'], *workspace_roots()])
        if provider.kind == 'local': safe_output(target, [provider.source, provider.destination])
        if target.exists():
            require(op and read_json(target / '.git/fm-operation.json') == {'operation_id': plan['id']}, 'restore target already exists')
    else:
        require(provider.actor() == plan['actor'], 'authenticated account changed')
        online(profile, provider)
        cache = prepare_cache(store, provider, refs_for(plan), False)
        if plan['kind'] == 'preserve': validate_archive_root(plan['archive_root'], store, provider)
        if plan['kind'] == 'integrate': preflight_integrate(store, plan, profile, op, cache)
    if plan['kind'] == 'fork':
        target = safe_output(plan['checkout'], [store.root, *workspace_roots(), *([provider.source, provider.destination] if provider.kind == 'local' else [])])
        if target.exists():
            require(op and read_json(target / '.git/fm-operation.json') == {'operation_id': plan['id']}, 'checkout already exists')
    require(not abort or plan['kind'] == 'integrate', 'abort only cancels an isolated integration candidate; remote writes are never automatically undone')
    with store.lock(plan['profile_id']):
        # The same validation runs again after lock acquisition; wrappers cannot bypass it.
        if profile: profile = profile_for_apply(store, plan, op)
        if plan['kind'] in ('fork', 'sync'): preflight_source(store, plan, profile, op)
        op = operation_load(store, plan) or new_operation(plan, profile)
        if plan['kind'] == 'preserve': validate_archive_root(plan['archive_root'], store, provider)
        if plan['kind'] == 'integrate': preflight_integrate(store, plan, profile, op, cache)
        save_operation(store, op)
        try:
            if plan['kind'] == 'sync': return apply_sync(store, plan, profile, op, cache)
            if plan['kind'] == 'fork': return apply_fork(store, plan, op, cache)
            if plan['kind'] == 'preserve': return apply_preserve(store, plan, profile, op, cache)
            if plan['kind'] == 'restore': return apply_restore(store, plan, op)
            return apply_integrate(store, plan, profile, op, cache, continuing=continuing, abort=abort)
        except (Failure, OSError) as error:
            code = error.code if isinstance(error, Failure) else (5 if op['intents'] else 6)
            op['status'] = 'uncertain' if code == 5 else 'failed'
            try: save_operation(store, op)
            except (OSError, Failure): pass
            if isinstance(error, OSError): raise Failure('state/execution failure; reconcile operation: ' + str(error), code) from error
            raise
