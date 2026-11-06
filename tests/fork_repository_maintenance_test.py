"""Behavioral tests with real isolated repositories; never contact GitHub."""
from __future__ import annotations

import hashlib
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
SCRIPTS = Path(os.environ.get('FORK_MAINTENANCE_SCRIPTS', ROOT / 'skills/fork-repository-maintenance/scripts'))
sys.path.insert(0, str(SCRIPTS))
import fm_core as core
import fm_engine as engine
import fork_maintenance as entrypoint
CLI = SCRIPTS / 'fork_maintenance.py'
GIT = shutil.which('git')
PYTHON = sys.executable


class ForkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fork-maintenance-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = self.root / 'a.git'; self.b = self.root / 'b.git'
        self.work = self.root / 'author'; self.checkout = self.root / 'checkout'
        self.state = self.root / 'state'
        self.env = os.environ.copy()
        self.env.update(HOME=str(self.root / 'home'), GIT_CONFIG_NOSYSTEM='1',
                        GIT_CONFIG_GLOBAL=os.devnull, PYTHONDONTWRITEBYTECODE='1',
                        GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                        GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.git(None, 'init', '--bare', '--initial-branch=main', str(self.a))
        self.git(None, 'init', '--initial-branch=main', str(self.work))
        (self.work / 'version.txt').write_text('5\n')
        self.commit(self.work, 'version 5')
        self.initial = self.git(self.work, 'rev-parse', 'HEAD').strip()
        self.git(self.work, 'remote', 'add', 'origin', str(self.a))
        self.git(self.work, 'push', 'origin', 'main')
        self.git(self.work, 'branch', 'release/5')
        self.git(self.work, 'branch', 'develop')
        self.git(self.work, 'push', 'origin', 'release/5', 'develop')

    def git(self, repo, *args, check=True):
        cmd = [GIT] + (['-C', str(repo)] if repo else []) + list(args)
        result = subprocess.run(cmd, env=self.env, text=True, capture_output=True)
        if check and result.returncode:
            raise AssertionError(result.stderr)
        return result.stdout if check else result

    def commit(self, repo, message):
        self.git(repo, 'add', '--all'); self.git(repo, 'commit', '-m', message)
        return self.git(repo, 'rev-parse', 'HEAD').strip()

    def cli(self, *args, ok=True, env=None, cwd=None):
        result = subprocess.run([PYTHON, str(CLI), '--state-dir', str(self.state), *map(str, args)],
                                cwd=cwd or ROOT, env=env or self.env, text=True, capture_output=True)
        output = result.stdout if result.returncode == 0 else result.stderr
        try: data = json.loads(output)
        except ValueError: raise AssertionError(result.stdout + '\n' + result.stderr)
        if ok and result.returncode:
            raise AssertionError(data)
        if not ok:
            self.assertNotEqual(result.returncode, 0, data)
        return data

    def plan_fork(self, scope='single', branches=('main',), base=None, name='personal-main'):
        args = ['fork', '--provider', 'local', '--source', self.a, '--destination', self.b,
                '--scope', scope, '--default-name', name, '--checkout', self.checkout,
                '--dry-run', '--refresh']
        for item in branches: args += ['--branch', item]
        if base: args += ['--default-base', base]
        return self.cli(*args)['plan']

    def apply(self, plan, ok=True):
        path = self.root / ('plan-' + plan['id'] + '.json')
        path.write_text(json.dumps(plan))
        return self.cli(plan['kind'], '--plan', path, '--approve-plan', plan['digest'], ok=ok)

    def initialize(self, scope='single', branches=('main',), base=None):
        plan = self.plan_fork(scope, branches, base)
        result = self.apply(plan)
        self.profile_id = result['profile_id']
        return plan, result

    def heads(self, repo=None):
        output = self.git(repo or self.b, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads')
        return dict(line.split(' ', 1) for line in output.splitlines())

    def advance(self, branch='main', content='6\n', filename='version.txt'):
        self.git(self.work, 'switch', branch)
        (self.work / filename).write_text(content)
        sha = self.commit(self.work, 'advance ' + branch)
        self.git(self.work, 'push', 'origin', branch)
        return sha

    def sync_plan(self, scope='single', branches=('main',), mode='existing-only'):
        args = ['plan-sync', '--profile', self.profile_id, '--scope', scope,
                '--new-branches', mode, '--refresh']
        for name in branches: args += ['--branch', name]
        return self.cli(*args)['plan']

    def profile_path(self):
        return self.state / 'profiles' / (self.profile_id + '.json')

    def state_digest(self):
        return {str(p.relative_to(self.state)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.state.rglob('*') if p.is_file() and 'cache' not in p.relative_to(self.state).parts} if self.state.exists() else {}

    def test_default_only_creates_independent_default_and_idempotent_resume(self):
        plan, result = self.initialize()
        self.assertEqual(set(self.heads()), {'refs/heads/main', 'refs/heads/personal-main'})
        self.assertEqual(self.git(self.b, 'symbolic-ref', 'HEAD').strip(), 'refs/heads/personal-main')
        self.assertEqual(self.heads()['refs/heads/main'], self.initial)
        self.assertEqual(self.git(self.checkout, 'branch', '--show-current').strip(), 'personal-main')
        again = self.cli('resume', '--operation', plan['id'], '--approve-plan', plan['digest'])
        self.assertEqual(again['status'], 'completed')
        self.assertEqual(self.heads()['refs/heads/personal-main'], self.initial)

    def test_selected_nondefault_removes_only_owned_bootstrap(self):
        self.initialize('selected', ('release/5', 'develop'), 'release/5')
        self.assertEqual(set(self.heads()), {'refs/heads/release/5', 'refs/heads/develop', 'refs/heads/personal-main'})
        self.assertEqual(self.heads()['refs/heads/personal-main'], self.initial)

    def test_all_branch_fork_has_same_names_plus_personal_default(self):
        self.initialize('all', ())
        self.assertEqual(set(self.heads()), {'refs/heads/main', 'refs/heads/release/5', 'refs/heads/develop', 'refs/heads/personal-main'})

    def test_missing_base_rejected_without_state_or_destination(self):
        self.cli('fork', '--provider', 'local', '--source', self.a, '--destination', self.b,
                 '--scope', 'single', '--branch', 'release/5', '--default-name', 'personal-main',
                 '--checkout', self.checkout, '--dry-run', '--refresh', ok=False)
        self.assertFalse(self.b.exists()); self.assertFalse(self.state.exists())

    def test_default_priority_cannot_be_overridden(self):
        self.cli('fork', '--provider', 'local', '--source', self.a, '--destination', self.b,
                 '--scope', 'selected', '--branch', 'main', '--branch', 'release/5',
                 '--default-name', 'personal-main', '--default-base', 'release/5',
                 '--checkout', self.checkout, '--dry-run', '--refresh', ok=False)
        self.assertFalse(self.state.exists())

    def test_no_background_sync_and_source_sync_preserves_personal_function(self):
        self.initialize()
        (self.checkout / 'feature.txt').write_text('my feature\n')
        personal = self.commit(self.checkout, 'my feature')
        self.git(self.checkout, 'push', 'origin', 'personal-main')
        updated = self.advance()
        self.assertEqual(self.heads()['refs/heads/main'], self.initial)
        plan = self.sync_plan()
        self.assertEqual(self.heads()['refs/heads/main'], self.initial)
        self.apply(plan)
        self.assertEqual(self.heads()['refs/heads/main'], updated)
        self.assertEqual(self.heads()['refs/heads/personal-main'], personal)
        self.assertEqual((self.checkout / 'version.txt').read_text(), '5\n')

    def test_existing_only_all_skips_new_upstream_branches(self):
        self.initialize(); updated = self.advance()
        result = self.apply(self.sync_plan('all', ()))
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(set(self.heads()), {'refs/heads/main', 'refs/heads/personal-main'})
        self.assertEqual(self.heads()['refs/heads/main'], updated)

    def test_include_new_all_creates_corresponding_sources_only(self):
        self.initialize(); self.advance()
        self.apply(self.sync_plan('all', (), 'include-new'))
        self.assertEqual(set(self.heads()), {'refs/heads/main', 'refs/heads/release/5', 'refs/heads/develop', 'refs/heads/personal-main'})
        self.assertEqual(self.heads()['refs/heads/personal-main'], self.initial)

    def test_selected_sync_does_not_advance_other_existing_source(self):
        self.initialize('all', ()); self.advance('main'); updated = self.advance('release/5', '5.1\n')
        self.apply(self.sync_plan('selected', ('release/5',)))
        self.assertEqual(self.heads()['refs/heads/main'], self.initial)
        self.assertEqual(self.heads()['refs/heads/release/5'], updated)

    def test_new_source_with_personal_name_blocks_even_when_sha_equal(self):
        self.initialize()
        self.git(self.work, 'branch', 'personal-main', self.initial)
        self.git(self.work, 'push', 'origin', 'personal-main')
        before = self.state_digest()
        self.cli('plan-sync', '--profile', self.profile_id, '--scope', 'all', '--new-branches', 'include-new', '--refresh', ok=False)
        self.assertEqual(before, self.state_digest())
        self.assertEqual(self.heads()['refs/heads/personal-main'], self.initial)

    def test_unregistered_existing_name_is_not_adopted(self):
        self.initialize()
        self.git(self.a, 'push', str(self.b), 'refs/heads/develop:refs/heads/develop')
        self.cli('plan-sync', '--profile', self.profile_id, '--scope', 'single', '--branch', 'develop',
                 '--new-branches', 'include-new', '--refresh', ok=False)

    def test_source_personal_commits_block_without_overwrite(self):
        self.initialize()
        self.git(self.checkout, 'switch', '-c', 'source-edit', 'origin/main')
        (self.checkout / 'private.txt').write_text('keep me')
        personal = self.commit(self.checkout, 'source accidentally edited')
        self.git(self.checkout, 'push', 'origin', 'HEAD:main')
        before = self.state_digest()
        self.cli('plan-sync', '--profile', self.profile_id, '--scope', 'single', '--branch', 'main', '--refresh', ok=False)
        self.assertEqual(before, self.state_digest()); self.assertEqual(self.heads()['refs/heads/main'], personal)

    def test_upstream_rewrite_is_rejected(self):
        self.initialize(); self.advance(); self.apply(self.sync_plan())
        self.git(self.work, 'switch', '--orphan', 'rewrite')
        self.git(self.work, 'rm', '-rf', '.', check=False)
        (self.work / 'other.txt').write_text('other history')
        self.commit(self.work, 'replacement history')
        self.git(self.work, 'push', '--force', 'origin', 'HEAD:main')
        old = self.heads(); state = self.state_digest()
        self.cli('plan-sync', '--profile', self.profile_id, '--scope', 'single', '--branch', 'main', '--refresh', ok=False)
        self.assertEqual(old, self.heads()); self.assertEqual(state, self.state_digest())

    def test_source_deleted_is_retained_and_reported(self):
        self.initialize('all', ())
        self.git(self.a, 'update-ref', '-d', 'refs/heads/develop')
        result = self.cli('inspect', '--profile', self.profile_id)
        self.assertEqual(result['branches']['develop']['status'], 'source-missing')
        self.assertIn('refs/heads/develop', self.heads())

    def test_plan_frozen_against_upstream_advances(self):
        self.initialize(); self.advance(); plan = self.sync_plan()
        self.advance(content='7\n')
        before = self.state_digest(); heads = self.heads()
        self.apply(plan, ok=False)
        self.assertEqual(before, self.state_digest()); self.assertEqual(heads, self.heads())

    def test_plan_frozen_against_remote_target_advances(self):
        self.initialize(); self.advance(); plan = self.sync_plan()
        self.git(self.a, 'push', str(self.b), 'refs/heads/main:refs/heads/main')
        before = self.state_digest()
        self.apply(plan, ok=False)
        self.assertEqual(before, self.state_digest())

    def test_scope_authorization_and_digest_rejected(self):
        self.initialize(); self.advance(); plan = self.sync_plan()
        path = self.root / 'plan.json'; path.write_text(json.dumps(plan))
        before = self.state_digest()
        self.cli('sync', '--plan', path, '--approve-plan', 'wrong', ok=False)
        plan['entries'][0]['name'] = 'personal-main'; path.write_text(json.dumps(plan))
        self.cli('sync', '--plan', path, '--approve-plan', plan['digest'], ok=False)
        self.assertEqual(before, self.state_digest())

    def test_direct_invocation_revalidates_later_personal_entry(self):
        self.initialize('all', ()); self.advance(); plan = self.sync_plan('all', ())
        plan['entries'][-1] = {'name': 'personal-main', 'before': self.initial, 'after': self.initial, 'action': 'noop'}
        plan['requested'] = sorted(e['name'] for e in plan['entries'])
        plan['digest'] = core.digest({k:v for k,v in plan.items() if k!='digest'})
        before = self.state_digest(); heads = self.heads()
        self.apply(plan, ok=False)
        self.assertEqual(before, self.state_digest()); self.assertEqual(heads, self.heads())

    def test_direct_forged_existing_only_create_rejected(self):
        self.initialize(); plan = self.sync_plan('all', ())
        for entry in plan['entries']:
            if entry['before'] is None: entry['action']='create'
        plan['digest']=core.digest({k:v for k,v in plan.items() if k!='digest'})
        self.apply(plan, ok=False)
        self.assertNotIn('refs/heads/develop', self.heads())

    def test_recreated_destination_cannot_be_adopted_by_editing_plan_id(self):
        self.initialize(); self.advance(); plan=self.sync_plan()
        replacement=self.root/'replacement.git'
        self.git(None,'clone','--bare',str(self.b),str(replacement))
        shutil.rmtree(self.b); replacement.rename(self.b)
        provider=core.Provider('local',str(self.a),str(self.b))
        with patch.dict(os.environ,self.env,clear=True): plan['b_id']=provider.metadata('b')['id']
        plan['digest']=core.digest({k:v for k,v in plan.items() if k!='digest'})
        before=self.state_digest(); heads=self.heads(); self.apply(plan,ok=False)
        self.assertEqual(before,self.state_digest()); self.assertEqual(heads,self.heads())

    def test_completed_sync_resume_is_idempotent(self):
        self.initialize(); sha = self.advance(); plan = self.sync_plan()
        self.apply(plan); profile = self.profile_path().read_bytes()
        self.cli('resume', '--operation', plan['id'], '--approve-plan', plan['digest'])
        self.assertEqual(self.profile_path().read_bytes(), profile)
        self.assertEqual(self.heads()['refs/heads/main'], sha)

    def test_state_and_output_symlinks_rejected_before_mutation(self):
        alias = self.root / 'state-alias'; alias.symlink_to(self.root / 'uncreated')
        result = subprocess.run([PYTHON, str(CLI), '--state-dir', str(alias), 'inspect', '--profile', 'a'*32, '--offline'], env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode,0); self.assertFalse((self.root/'uncreated').exists())
        self.cli('fork','--provider','local','--source',self.a,'--destination',self.a,
                 '--scope','single','--branch','main','--default-name','mine','--checkout',self.checkout,'--dry-run','--refresh',ok=False)
        self.assertFalse(self.state.exists())

    def test_state_overlap_with_source_rejected(self):
        self.state=self.a/'state'
        self.cli('fork','--provider','local','--source',self.a,'--destination',self.b,
                 '--scope','single','--branch','main','--default-name','mine','--checkout',self.checkout,'--dry-run','--refresh',ok=False)
        self.assertFalse(self.state.exists())

    def test_projectless_parent_directory_allows_external_state_and_checkout(self):
        result=self.cli('fork','--provider','local','--source',self.a,'--destination',self.b,
                        '--scope','single','--branch','main','--default-name','mine','--checkout',self.checkout,
                        '--dry-run','--refresh',cwd=self.root)
        self.assertEqual(result['status'],'planned'); self.assertFalse(self.b.exists())

    def test_case_and_nested_name_collisions(self):
        for names in [('Main','main'),('Foo/bar','foo'),('foo','foo/bar')]:
            with self.subTest(names=names), self.assertRaises(core.Failure): core.names_available(names)

    def test_path_identity_containment_and_existing_checkout_states(self):
        for output in (self.a, self.a/'nested', self.a.parent, self.root/'A.GIT'):
            with self.subTest(output=output), self.assertRaises(core.Failure): core.safe_output(output,[self.a])
        empty=self.root/'empty'; empty.mkdir()
        populated=self.root/'populated'; populated.mkdir(); (populated/'keep').write_text('keep')
        file=self.root/'file'; file.write_text('keep')
        alias=self.root/'alias'; alias.symlink_to(populated)
        for checkout in (empty,populated,file,alias,self.a/'nested',self.a.parent):
            self.cli('fork','--provider','local','--source',self.a,'--destination',self.b,
                     '--scope','single','--branch','main','--default-name','mine','--checkout',checkout,
                     '--dry-run','--refresh',ok=False)
            self.assertFalse(self.state.exists()); self.assertFalse(self.b.exists())
        self.assertEqual(file.read_text(),'keep'); self.assertEqual((populated/'keep').read_text(),'keep')

    def test_duplicate_json_is_not_accepted(self):
        path=self.root/'duplicate.json'; path.write_text('{"kind":"sync","kind":"fork"}')
        self.cli('sync','--plan',path,'--approve-plan','anything',ok=False)
        self.assertFalse(self.state.exists())

    def preserve(self):
        plan=self.cli('preserve','--profile',self.profile_id,'--dry-run','--refresh')['plan']
        result=self.apply(plan)
        return plan,Path(result['snapshot'])

    def test_snapshot_restores_offline_after_original_repositories_removed(self):
        self.initialize()
        (self.checkout/'personal.txt').write_text('important function')
        personal=self.commit(self.checkout,'personal code'); self.git(self.checkout,'push','origin','personal-main')
        plan,snapshot=self.preserve()
        shutil.rmtree(self.a); shutil.rmtree(self.b)
        target=self.root/'restored'
        restore=self.cli('restore','--snapshot',snapshot,'--destination-path',target,'--dry-run')['plan']
        result=self.apply(restore)
        self.assertFalse(result['remote_verified'])
        self.assertEqual(self.git(target,'rev-parse','HEAD').strip(),personal)
        self.assertEqual((target/'personal.txt').read_text(),'important function')
        self.assertEqual(self.git(target,'branch','--show-current').strip(),'personal-main')
        self.cli('resume','--operation',restore['id'],'--approve-plan',restore['digest'])

    def test_snapshot_tamper_and_later_manifest_entry_rejected(self):
        self.initialize(); _,snapshot=self.preserve()
        manifest_path=snapshot/'manifest.json'; original=manifest_path.read_text()
        manifest=json.loads(original); manifest['entries'][-1]['ref']='../../escape'
        manifest_path.write_text(json.dumps(manifest))
        target=self.root/'bad-restore'
        self.cli('restore','--snapshot',snapshot,'--destination-path',target,'--dry-run',ok=False)
        self.assertFalse(target.exists())
        manifest_path.write_text(original)
        with (snapshot/'history.bundle').open('ab') as stream: stream.write(b'corrupt')
        self.cli('restore','--snapshot',snapshot,'--destination-path',target,'--dry-run',ok=False)
        self.assertFalse(target.exists())

    def test_restore_existing_destination_and_nested_snapshot_rejected(self):
        self.initialize(); _,snapshot=self.preserve()
        target=self.root/'existing'; target.mkdir(); (target/'keep').write_text('keep')
        for destination in (target,snapshot/'nested',snapshot.parent):
            self.cli('restore','--snapshot',snapshot,'--destination-path',destination,'--dry-run',ok=False)
        self.assertEqual((target/'keep').read_text(),'keep')

    def integration_plan(self,strategy='merge',validation=None,**extra):
        args=['integrate','--profile',self.profile_id,'--source-name','main','--target','personal-main',
              '--strategy',strategy,'--dry-run','--refresh']
        for command in validation or []: args+=['--validation',json.dumps(command)]
        for key,value in extra.items(): args+=['--'+key.replace('_','-'),value]
        return self.cli(*args)['plan']

    def test_merge_review_and_resume_keeps_sources_and_requires_validation(self):
        self.initialize()
        (self.checkout/'feature.txt').write_text('X')
        personal=self.commit(self.checkout,'X'); self.git(self.checkout,'push','origin','personal-main')
        source=self.advance(); self.apply(self.sync_plan())
        validation=[[PYTHON,'-c',"from pathlib import Path; assert Path('feature.txt').read_text()=='X'; assert Path('version.txt').read_text()=='6\\n'"]]
        plan=self.integration_plan(validation=validation)
        result=self.apply(plan)
        self.assertEqual(result['status'],'candidate-review')
        self.assertEqual(self.heads()['refs/heads/personal-main'],personal)
        candidate=Path(result['candidate']); self.git(candidate,'commit','-m','adapt X to version 6')
        result=self.cli('resume','--operation',plan['id'],'--approve-plan',plan['digest'])
        self.assertEqual(result['status'],'completed')
        self.assertEqual(self.heads()['refs/heads/main'],source)
        self.cli('resume','--operation',plan['id'],'--approve-plan',plan['digest'])

    def test_conflict_abort_leaves_personal_and_source_untouched(self):
        self.initialize()
        (self.checkout/'version.txt').write_text('personal behavior')
        old=self.commit(self.checkout,'personal behavior'); self.git(self.checkout,'push','origin','personal-main')
        source=self.advance(); self.apply(self.sync_plan())
        plan=self.integration_plan(validation=[[PYTHON,'-c','pass']])
        result=self.apply(plan)
        self.assertEqual(result['status'],'candidate-review')
        self.cli('abort','--operation',plan['id'],'--approve-plan',plan['digest'])
        self.assertEqual(self.heads()['refs/heads/personal-main'],old)
        self.assertEqual(self.heads()['refs/heads/main'],source)

    def test_rebase_creates_new_personal_line_and_never_rewrites_default(self):
        self.initialize()
        (self.checkout/'feature.txt').write_text('X')
        old=self.commit(self.checkout,'X'); self.git(self.checkout,'push','origin','personal-main')
        source=self.advance(); self.apply(self.sync_plan())
        plan=self.integration_plan('rebase',[[PYTHON,'-c',"from pathlib import Path; assert Path('feature.txt').read_text()=='X'"]],base_oid=self.initial,result_branch='personal/v6')
        result=self.apply(plan)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(self.heads()['refs/heads/personal-main'],old)
        self.assertEqual(self.git(self.b,'symbolic-ref','HEAD').strip(),'refs/heads/personal-main')
        self.assertEqual(self.git(self.b,'merge-base','--is-ancestor',source,self.heads()['refs/heads/personal/v6']), '')

    def test_validation_failure_never_updates_personal_target(self):
        self.initialize(); self.advance(); self.apply(self.sync_plan())
        plan=self.integration_plan(validation=[[PYTHON,'-c','raise SystemExit(1)']])
        result=self.apply(plan); self.git(result['candidate'],'commit','-m','integration candidate')
        result=self.cli('resume','--operation',plan['id'],'--approve-plan',plan['digest'])
        self.assertEqual(result['status'],'verification-failed')
        self.assertEqual(self.heads()['refs/heads/personal-main'],self.initial)

    def test_conflict_resolution_and_repeat_resume_publish_only_personal_result(self):
        self.initialize()
        (self.checkout/'version.txt').write_text('personal version 5\n')
        self.commit(self.checkout,'personal version'); self.git(self.checkout,'push','origin','personal-main')
        source=self.advance(); self.apply(self.sync_plan())
        plan=self.integration_plan(validation=[[PYTHON,'-c',"from pathlib import Path; assert Path('version.txt').read_text()=='personal version 6\\n'"]])
        result=self.apply(plan); candidate=Path(result['candidate'])
        (candidate/'version.txt').write_text('personal version 6\n')
        self.commit(candidate,'resolve personal version 6')
        result=self.cli('resume','--operation',plan['id'],'--approve-plan',plan['digest'])
        self.assertEqual(result['status'],'completed')
        heads=self.heads(); self.assertEqual(heads['refs/heads/main'],source)
        self.cli('resume','--operation',plan['id'],'--approve-plan',plan['digest'])
        self.assertEqual(heads,self.heads())

    def test_cherry_pick_review_and_already_applied_idempotency(self):
        self.initialize(); picked=self.advance(filename='upstream-feature.txt',content='upstream feature')
        self.apply(self.sync_plan())
        plan=self.integration_plan('cherry-pick',[[PYTHON,'-c',"from pathlib import Path; assert Path('upstream-feature.txt').exists()"]],pick=picked)
        result=self.apply(plan); self.commit(Path(result['candidate']),'apply upstream feature')
        result=self.cli('resume','--operation',plan['id'],'--approve-plan',plan['digest'])
        self.assertEqual(result['status'],'completed')
        heads=self.heads()
        again=self.integration_plan('cherry-pick',[[PYTHON,'-c','pass']],pick=picked)
        self.assertEqual(self.apply(again)['reason'],'all patches already applied')
        self.assertEqual(heads,self.heads())

    def test_integration_lost_receipt_reconciles_without_republish(self):
        self.initialize(); self.advance(); self.apply(self.sync_plan())
        plan=self.integration_plan(validation=[[PYTHON,'-c','pass']])
        result=self.apply(plan); self.commit(Path(result['candidate']),'reviewed integration')
        args=self.direct_args(plan); original=engine.publish_ref
        def lose_receipt(*positional,**kwargs):
            original(*positional,**kwargs)
            raise core.Failure('injected timeout after personal publication',5)
        with patch.dict(os.environ,self.env,clear=True),patch.object(engine,'publish_ref',side_effect=lose_receipt):
            with self.assertRaises(core.Failure): engine.apply(args,core.Store(self.state),continuing=True)
        published=self.heads()
        with patch.dict(os.environ,self.env,clear=True),patch.object(engine,'publish_ref',side_effect=AssertionError('must reconcile')):
            result=engine.apply(args,core.Store(self.state),continuing=True)
        self.assertEqual(result['status'],'completed'); self.assertEqual(published,self.heads())

    def test_resume_before_git_integration_starts_and_aborted_patch_cannot_complete(self):
        self.initialize(); picked=self.advance(); self.apply(self.sync_plan())
        plan=self.integration_plan('cherry-pick',[[PYTHON,'-c','pass']],pick=picked)
        store=core.Store(self.state)
        with patch.dict(os.environ,self.env,clear=True):
            op=engine.new_operation(plan,store.profile(self.profile_id)); engine.save_operation(store,op)
        result=self.cli('resume','--operation',plan['id'],'--approve-plan',plan['digest'])
        self.assertEqual(result['status'],'candidate-review')
        candidate=Path(result['candidate'])
        self.git(candidate,'reset','--hard','HEAD')  # isolated fixture simulates abandoning staged patches
        heads=self.heads()
        self.cli('resume','--operation',plan['id'],'--approve-plan',plan['digest'],ok=False)
        self.assertEqual(heads,self.heads())

    def test_personal_default_name_does_not_collide_with_internal_candidate(self):
        fork=self.plan_fork(name='fm-candidate')
        self.profile_id=self.apply(fork)['profile_id']
        self.advance(); self.apply(self.sync_plan())
        plan=self.cli('integrate','--profile',self.profile_id,'--source-name','main','--target','fm-candidate',
                      '--dry-run','--refresh','--validation',json.dumps([PYTHON,'-c','pass']))['plan']
        result=self.apply(plan); self.assertEqual(result['status'],'candidate-review')
        self.commit(Path(result['candidate']),'review candidate with custom default')
        self.assertEqual(self.cli('resume','--operation',plan['id'],'--approve-plan',plan['digest'])['status'],'completed')

    def test_direct_invalid_integration_role_and_patch_rejected_before_journal(self):
        self.initialize(); picked=self.advance(); self.apply(self.sync_plan())
        plan=self.integration_plan('cherry-pick',[[PYTHON,'-c','pass']],pick=picked)
        for changed in ({'source_name':'personal-main'}, {'picks':['f'*40]}, {'protected':{}}):
            malformed=dict(plan,**changed)
            malformed['digest']=core.digest({k:v for k,v in malformed.items() if k!='digest'})
            before=self.state_digest(); heads=self.heads(); self.apply(malformed,ok=False)
            self.assertEqual(before,self.state_digest()); self.assertEqual(heads,self.heads())

    def test_direct_invalid_archive_root_rejected_before_journal(self):
        self.initialize()
        plan=self.cli('preserve','--profile',self.profile_id,'--dry-run','--refresh')['plan']
        plan['archive_root']=str(self.a/'overlap')
        plan['digest']=core.digest({k:v for k,v in plan.items() if k!='digest'})
        before=self.state_digest(); self.apply(plan,ok=False); self.assertEqual(before,self.state_digest())

    def test_missing_git_and_gh_stop_explicitly(self):
        env=dict(self.env,PATH=str(self.root/'no-tools'))
        result=subprocess.run([PYTHON,str(CLI),'--state-dir',str(self.state),'inspect','--profile','a'*32,'--offline'],env=env,cwd=ROOT,text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0); self.assertIn('missing dependency',result.stderr)
        self.assertFalse(self.state.exists())

    def direct_args(self,plan,command=None):
        filename=self.root/('direct-'+plan['id']+'.json'); filename.write_text(json.dumps(plan))
        return entrypoint.parser().parse_args(['--state-dir',str(self.state),command or plan['kind'],
                                               '--plan',str(filename),'--approve-plan',plan['digest']])

    def test_unknown_send_reconciles_without_republishing_verified_remote(self):
        self.initialize('all', ()); self.advance('main'); self.advance('release/5','5.1\n')
        plan=self.sync_plan('all',()); args=self.direct_args(plan)
        original=engine.publish_ref
        def lost_receipt(cache,provider,name,desired,expected,**kwargs):
            original(cache,provider,name,desired,expected,**kwargs)
            if name=='release/5': raise core.Failure('injected transport timeout after server update',5)
        with patch.dict(os.environ,self.env,clear=True),patch.object(engine,'publish_ref',side_effect=lost_receipt):
            result=engine.apply(args,core.Store(self.state))
        self.assertEqual(result['status'],'uncertain')
        for e in plan['entries']: self.assertEqual(self.heads()['refs/heads/'+e['name']],e['after'])
        with patch.dict(os.environ,self.env,clear=True),patch.object(engine,'publish_ref',side_effect=AssertionError('must reconcile without resending')):
            result=engine.apply(args,core.Store(self.state))
        self.assertEqual(result['status'],'completed')
        stored=json.loads(self.profile_path().read_text())
        for e in plan['entries']: self.assertEqual(stored['sources'][e['name']]['last_verified_remote_oid'],e['after'])

    def test_remote_success_with_profile_persistence_failure_can_resume(self):
        self.initialize(); self.advance(); plan=self.sync_plan(); args=self.direct_args(plan)
        original=engine.atomic_json
        def fail_profile(path,value):
            if Path(path)==self.profile_path().resolve(): raise OSError('injected profile fsync failure')
            return original(path,value)
        with patch.dict(os.environ,self.env,clear=True),patch.object(engine,'atomic_json',side_effect=fail_profile):
            with self.assertRaises(core.Failure) as raised: engine.apply(args,core.Store(self.state))
            self.assertEqual(raised.exception.code,5)
        self.assertEqual(self.heads()['refs/heads/main'],plan['entries'][0]['after'])
        with patch.dict(os.environ,self.env,clear=True),patch.object(engine,'publish_ref',side_effect=AssertionError('already sent')):
            result=engine.apply(args,core.Store(self.state))
        self.assertEqual(result['status'],'completed')

    def test_exclusive_directory_publication_rejects_racing_destination(self):
        staging=self.root/'staging'; target=self.root/'appeared'
        staging.mkdir(); (staging/'new').write_text('new')
        target.mkdir(); (target/'keep').write_text('old')
        with self.assertRaises(core.Failure): core.publish_directory(staging,target)
        self.assertEqual((target/'keep').read_text(),'old')
        self.assertEqual((staging/'new').read_text(),'new')

    def test_exclusive_plan_save_does_not_overwrite_racing_file(self):
        path=self.root/'plan.json'; path.write_text('user data')
        with self.assertRaises(FileExistsError): core.new_json(path,{'plan':'new'})
        self.assertEqual(path.read_text(),'user data')

    def test_invalid_plan_output_rejected_before_refresh(self):
        self.cli('fork','--provider','local','--source',self.a,'--destination',self.b,
                 '--scope','single','--branch','main','--default-name','mine','--checkout',self.checkout,
                 '--dry-run','--refresh','--save-plan',self.a/'bad-plan.json',ok=False)
        self.assertFalse(self.state.exists()); self.assertFalse((self.a/'bad-plan.json').exists())

    def test_apply_cannot_mix_new_parameters_with_saved_plan(self):
        self.initialize(); self.advance(); plan=self.sync_plan(); filename=self.root/'saved.json'
        filename.write_text(json.dumps(plan)); before=self.state_digest()
        self.cli('sync','--plan',filename,'--approve-plan',plan['digest'],'--profile','a'*32,ok=False)
        self.assertEqual(before,self.state_digest())

    def test_expired_plan_and_unknown_later_profile_record_stop_before_write(self):
        self.initialize(); self.advance(); plan=self.sync_plan()
        plan['created_at']='2020-01-01T00:00:00+00:00'; plan['expires_at']='2020-01-02T00:00:00+00:00'
        plan['digest']=core.digest({k:v for k,v in plan.items() if k!='digest'})
        before=self.state_digest(); self.apply(plan,ok=False); self.assertEqual(before,self.state_digest())
        profile=json.loads(self.profile_path().read_text())
        profile['sources']['later']={'initial_oid':self.initial,'last_verified_remote_oid':self.initial,'unexpected':True}
        self.profile_path().write_text(json.dumps(profile)); before=self.state_digest()
        self.cli('inspect','--profile',self.profile_id,'--offline',ok=False)
        self.assertEqual(before,self.state_digest())

    def test_custom_archive_and_snapshot_idempotency(self):
        self.initialize(); archive=self.root/'archive'
        plan=self.cli('preserve','--profile',self.profile_id,'--archive-root',archive,'--dry-run','--refresh')['plan']
        result=self.apply(plan); snapshot=Path(result['snapshot']); self.assertEqual(snapshot.parent,archive.resolve())
        before=(snapshot/'history.bundle').read_bytes()
        self.cli('resume','--operation',plan['id'],'--approve-plan',plan['digest'])
        self.assertEqual(before,(snapshot/'history.bundle').read_bytes())

    def test_annotated_tags_preserve_objects_and_restore_original_names(self):
        self.initialize()
        self.git(self.work,'tag','-a','v5','-m','version five',self.initial)
        self.git(self.work,'push','origin','refs/tags/v5')
        self.git(self.a,'push',str(self.b),'refs/tags/v5:refs/tags/v5')
        plan=self.cli('preserve','--profile',self.profile_id,'--include-tags','--dry-run','--refresh')['plan']
        snapshot=Path(self.apply(plan)['snapshot'])
        restore=self.cli('restore','--snapshot',snapshot,'--destination-path',self.root/'tags-restored','--dry-run')['plan']
        result=self.apply(restore)
        self.assertEqual(self.git(result['destination'],'rev-parse','refs/tags/v5^{}').strip(),self.initial)
        self.assertEqual(self.git(result['destination'],'cat-file','-t','refs/tags/v5').strip(),'tag')

    def test_snapshot_failure_retains_staging_and_recovery_path(self):
        self.initialize(); plan=self.cli('preserve','--profile',self.profile_id,'--dry-run','--refresh')['plan']
        args=self.direct_args(plan)
        with patch.dict(os.environ,self.env,clear=True),patch.object(engine,'publish_directory',side_effect=core.Failure('injected publication failure',6)):
            with self.assertRaises(core.Failure): engine.apply(args,core.Store(self.state))
        record=json.loads((self.state/'operations'/(plan['id']+'.json')).read_text())
        self.assertTrue(record['recovery_paths'])
        self.assertTrue(Path(record['recovery_paths'][0]).is_dir())
        self.assertEqual(self.heads()['refs/heads/personal-main'],self.initial)

    def test_wrong_direct_plan_kind_never_writes(self):
        self.initialize(); self.advance(); plan=self.sync_plan(); filename=self.root/'wrong-kind.json'
        filename.write_text(json.dumps(plan)); before=self.state_digest()
        self.cli('fork','--plan',filename,'--approve-plan',plan['digest'],ok=False)
        self.assertEqual(before,self.state_digest())

    def test_global_smudge_filter_is_not_executed_during_clone_or_restore(self):
        self.git(self.work,'switch','main')
        (self.work/'.gitattributes').write_text('*.txt filter=canary\n')
        self.commit(self.work,'attributes'); self.git(self.work,'push','origin','main')
        sentinel=self.root/'filter-ran'; config=self.root/'gitconfig'
        config.write_text('[filter "canary"]\n smudge = "touch '+str(sentinel)+'; cat"\n required = true\n')
        self.env['GIT_CONFIG_GLOBAL']=str(config)
        self.initialize(); self.assertFalse(sentinel.exists())
        _,snapshot=self.preserve(); target=self.root/'filter-safe-restore'
        plan=self.cli('restore','--snapshot',snapshot,'--destination-path',target,'--dry-run')['plan']
        self.apply(plan); self.assertFalse(sentinel.exists())

    def test_missing_gh_blocks_github_request_without_mutation(self):
        tools=self.root/'only-git'; tools.mkdir(); (tools/'git').symlink_to(GIT)
        env=dict(self.env,PATH=str(tools))
        self.cli('fork','--source','acme/source','--destination','user/fork','--scope','single','--branch','main',
                 '--default-name','mine','--checkout',self.checkout,'--dry-run',ok=False,env=env)
        self.assertFalse(self.state.exists())

    def test_github_adapter_checks_actor_scope_and_default_api_without_network(self):
        provider=core.Provider('github','acme/source','user/fork')
        calls=[]
        def api(path,method='GET',body=None,missing=False):
            calls.append((path,method,body))
            if path=='user': return {'login':'user'}
            if method=='POST': return {'id':42,'default_branch':'main'}
            if method=='PATCH': return {}
            return {'id':42,'default_branch':'personal-main','parent':{'id':7}}
        with patch.object(provider,'api',side_effect=api),patch.object(provider,'actor',return_value='user'):
            created=provider.create('user'); provider.set_default('personal-main')
            self.assertEqual(created['id'],'42')
        post=next(c for c in calls if c[1]=='POST')
        self.assertEqual(post[2],{'name':'fork','default_branch_only':True})
        self.assertTrue(any(c[1]=='PATCH' and c[2]=={'default_branch':'personal-main'} for c in calls))


if __name__=='__main__': unittest.main(verbosity=2)
