#!/usr/bin/env python3
"""Manual same-name source synchronization, personal integration and preservation."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from fm_core import Failure, Store, check_git, read_json, redact, require
import fm_engine as engine


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state-dir', default=str(Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'fork-repository-maintenance'))
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('fork', 'plan-sync', 'sync', 'integrate', 'preserve', 'restore', 'resume', 'abort', 'inspect'):
        q = sub.add_parser(name)
        q.add_argument('--json', action='store_true', help='output is always machine-readable JSON')
        q.add_argument('--profile')
        q.add_argument('--plan')
        q.add_argument('--approve-plan')
        q.add_argument('--operation')
        q.add_argument('--dry-run', action='store_true')
        q.add_argument('--refresh', action='store_true', help='explicitly prepare owned local Git objects; never updates B')
        q.add_argument('--save-plan')
        if name == 'fork':
            q.add_argument('--provider', choices=('github', 'local'), default='github')
            q.add_argument('--source'); q.add_argument('--destination'); q.add_argument('--checkout')
            q.add_argument('--default-name'); q.add_argument('--default-base')
        if name in ('fork', 'plan-sync'):
            q.add_argument('--scope', choices=('single', 'selected', 'all'))
            q.add_argument('--branch', action='append', default=[])
        if name == 'plan-sync':
            q.add_argument('--new-branches', choices=('existing-only', 'include-new'), default='existing-only')
        if name == 'integrate':
            q.add_argument('--source-name'); q.add_argument('--source-oid'); q.add_argument('--target')
            q.add_argument('--result-branch'); q.add_argument('--base-oid')
            q.add_argument('--strategy', choices=('merge', 'rebase', 'cherry-pick'), default='merge')
            q.add_argument('--pick', action='append', default=[])
            q.add_argument('--validation', action='append', default=[], metavar='JSON_ARGV')
        if name == 'preserve':
            q.add_argument('--snapshot-scope', choices=('a', 'b', 'both'), default='both')
            q.add_argument('--include-tags', action='store_true')
            q.add_argument('--archive-root', help='owned external archive directory; defaults to the state snapshots directory')
        if name == 'restore':
            q.add_argument('--snapshot'); q.add_argument('--destination-path')
        if name == 'inspect':
            q.add_argument('--offline', action='store_true')
    return p


def main(argv=None):
    raw = list(argv) if argv is not None else sys.argv[1:]
    args = parser().parse_args(raw)
    try:
        require(sys.version_info >= (3, 11), 'Python 3.11+ is required')
        require(os.name == 'posix', 'this implementation currently supports macOS/Linux only')
        check_git()
        store = Store(args.state_dir)
        if args.command in ('resume', 'abort'):
            require({x.split('=',1)[0] for x in raw if x.startswith('--')} <= {'--state-dir','--operation','--approve-plan','--json'}, 'resume/abort cannot override planned inputs', 2)
            require(args.operation and args.approve_plan, '--operation and --approve-plan are required', 2)
            require(not args.plan and not args.refresh and not args.dry_run and not args.save_plan,
                    'resume/abort cannot change plan inputs', 2)
            result = engine.apply(args, store, continuing=True, abort=args.command == 'abort')
        elif args.plan:
            require({x.split('=',1)[0] for x in raw if x.startswith('--')} <= {'--state-dir','--plan','--approve-plan','--json'}, 'apply cannot override planned inputs', 2)
            require(args.command in ('fork', 'sync', 'integrate', 'preserve', 'restore'), 'command cannot apply a plan', 2)
            require(not args.dry_run and not args.refresh and not args.save_plan and not args.operation,
                    'apply cannot combine planning or operation inputs', 2)
            result = engine.apply(args, store)
        elif args.command == 'inspect':
            require(args.profile and not args.operation and not args.approve_plan and not args.save_plan and not args.refresh,
                    'inspect requires a profile and is read-only', 2)
            result = engine.inspect(args, store)
        else:
            require(args.command != 'sync', 'sync requires --plan and --approve-plan; use plan-sync first', 2)
            require(not args.operation and not args.approve_plan, 'planning does not accept apply/resume flags', 2)
            require(args.command == 'plan-sync' or args.dry_run, 'direct inputs only generate a --dry-run plan', 2)
            # --refresh is an explicit local preparation stage. It may be used with
            # --dry-run to prepare a plan, but never grants remote write authority.
            if args.command == 'fork':
                require(args.source and args.destination and args.scope and args.default_name and args.checkout,
                        'fork requires source/destination/scope/default-name/checkout', 2)
                result = engine.plan_fork(args, store)
            elif args.command == 'plan-sync':
                require(args.profile and args.scope, 'plan-sync requires profile and scope', 2)
                result = engine.plan_sync(args, store)
            elif args.command == 'integrate':
                require(args.profile and args.source_name and args.target, 'integrate requires profile/source-name/target', 2)
                args.validation = [json.loads(value) for value in args.validation]
                result = engine.plan_integrate(args, store)
            elif args.command == 'preserve':
                require(args.profile, 'preserve requires profile', 2)
                result = engine.plan_preserve(args, store)
            else:
                require(args.snapshot and args.destination_path, 'restore requires snapshot and destination-path', 2)
                result = engine.plan_restore(args, store)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return result.get('exit_code', 0)
    except (Failure, ValueError, TypeError, KeyError, OSError) as error:
        code = error.code if isinstance(error, Failure) else 2
        failure = {'status': 'uncertain' if code == 5 else 'blocked', 'error': redact(error), 'exit_code': code}
        try:
            identifier = args.operation or (read_json(args.plan)['id'] if args.plan else None)
            if identifier and 'store' in locals():
                record = read_json(store.path('operations', identifier))
                failure.update(operation_id=identifier, recovery_paths=[redact(x) for x in record.get('recovery_paths', []) if isinstance(x,str)])
        except (Failure, ValueError, KeyError, TypeError, OSError):
            pass
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
