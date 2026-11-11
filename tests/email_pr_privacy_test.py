"""Exercise the PR privacy check against disposable repositories."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECK = Path(__file__).resolve().parents[1] / "scripts/email_pr_privacy.py"
MAIL_SKILL = "skills/email-management/SKILL.md"
PRIVATE = "synthetic-private@example.invalid"
NOREPLY = "123+example-user@users.noreply.github.com"
LEGACY = "example-user@users.noreply.github.com"
BOT = "123+example[bot]@users.noreply.github.com"


class EmailPRPrivacyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="email-pr-privacy-")
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "commit.gpgsign", "false")
        # Existing base history is outside the PR and deliberately uses the fixture address.
        self.base = self.commit("README.md", author=PRIVATE, committer=PRIVATE)

    def git(self, *args, env=None):
        return subprocess.run(["git", *args], cwd=self.repo, env=env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def identity(self, author=NOREPLY, committer=NOREPLY):
        return dict(os.environ, GIT_AUTHOR_NAME="Fixture Author", GIT_AUTHOR_EMAIL=author,
                    GIT_COMMITTER_NAME="Fixture Committer", GIT_COMMITTER_EMAIL=committer)

    def commit(self, path, *, author=NOREPLY, committer=NOREPLY, text="Synthetic fixture\n"):
        file = self.repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
        self.git("add", "--", path)
        self.git("commit", "-qm", "fixture", env=self.identity(author, committer))
        return self.git("rev-parse", "HEAD")

    def check(self, expected, *, head="HEAD", base=None, repo=None):
        result = subprocess.run([sys.executable, "-B", str(CHECK), "--base", base or self.base,
                                 "--head", head], cwd=repo or self.repo, capture_output=True, text=True)
        output = result.stdout + result.stderr
        self.assertNotIn(PRIVATE, output)
        self.assertEqual(result.returncode, expected, output)
        return output

    def test_unrelated_pr_keeps_existing_commit_identity_policy(self):
        self.commit("unrelated.md", author=PRIVATE, committer=PRIVATE)
        self.assertIn("SKIP", self.check(0))

    def test_exact_range_accepts_current_legacy_bot_and_web_flow_noreply(self):
        self.commit(MAIL_SKILL, author=LEGACY, committer="noreply@github.com")
        head = self.commit("notes.md", author=BOT)
        self.commit("later.md", author=PRIVATE, committer=PRIVATE)
        self.assertIn("2 PR commits", self.check(0, head=head))

    def test_author_and_committer_are_checked_independently_across_the_pr(self):
        self.commit(MAIL_SKILL, author=PRIVATE)
        self.commit("notes.md", committer=PRIVATE)
        self.commit("last.md")
        self.assertIn("2 PR commits must use GitHub noreply identities (1 author fields, 1 committer fields)",
                      self.check(1))

    def test_mailmap_cannot_hide_raw_identity(self):
        self.commit(MAIL_SKILL, author=PRIVATE, committer=PRIVATE)
        self.commit(".mailmap", text=f"<{NOREPLY}> <{PRIVATE}>\n")
        self.assertIn("1 author fields, 1 committer fields", self.check(1))

    def test_reverted_skill_change_remains_in_scope(self):
        self.commit(MAIL_SKILL, author=PRIVATE)
        self.git("revert", "--no-edit", "HEAD", env=self.identity())
        self.assertEqual(self.git("diff", "--name-only", f"{self.base}...HEAD"), "")
        self.assertIn("1 PR commits", self.check(1))

    def test_merge_commit_identity_is_included(self):
        self.git("switch", "-qc", "side")
        self.commit(MAIL_SKILL)
        self.git("switch", "-q", "main")
        self.commit("notes.md")
        self.git("merge", "--no-ff", "--no-edit", "side", env=self.identity(committer=PRIVATE))
        self.assertIn("0 author fields, 1 committer fields", self.check(1))

    def test_missing_revision_fails_without_echoing_the_invalid_input(self):
        self.assertIn("Fetch the complete base and head", self.check(1, base=PRIVATE))

    def test_shallow_checkout_is_rejected_even_if_both_refs_resolve(self):
        self.commit(MAIL_SKILL)
        with tempfile.TemporaryDirectory(prefix="email-privacy-shallow-") as temp:
            clone = Path(temp) / "clone"
            self.git("clone", "--depth=1", self.repo.resolve().as_uri(), str(clone))
            self.assertIn("Fetch the complete base and head", self.check(1, base="HEAD", repo=clone))


if __name__ == "__main__":
    unittest.main()
