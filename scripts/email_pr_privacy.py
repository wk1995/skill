#!/usr/bin/env python3
"""Check raw Git identities for a pull request that changes the email Skill."""

import argparse
import re
import subprocess


SKILL_PATH = "skills/email-management/"
NOREPLY = re.compile(rb"(?:[0-9]+\+)?[a-z0-9][a-z0-9-]*(?:\[bot\])?@users\.noreply\.github\.com", re.I)


def git(*args: str) -> bytes:
    # Git diagnostics can contain untrusted values. Report only a generic error.
    return subprocess.check_output(
        ["git", "--no-replace-objects", *args], stderr=subprocess.DEVNULL
    )


def resolve(ref: str) -> str:
    return git("rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").strip().decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()

    try:
        if git("rev-parse", "--is-shallow-repository").strip() != b"false":
            raise ValueError("incomplete history")
        base, head = resolve(args.base), resolve(args.head)
        span = f"{base}..{head}"
        # Include reverted Skill changes as well as changes visible in the PR diff.
        changed = git("rev-list", "--full-history", "--no-merges", "-1",
                      span, "--", SKILL_PATH)
        if not changed and not git("diff", "--name-only", f"{base}...{head}", "--", SKILL_PATH):
            print("SKIP: PR does not change the email Skill")
            return 0
        # Lowercase %ae/%ce read the committed identities without .mailmap.
        data = git("log", "--no-show-signature", "--no-notes",
                   "-z", "--format=%H%x00%ae%x00%ce", span)
        fields = data.removesuffix(b"\x00").split(b"\x00") if data else []
        if len(fields) % 3 or not data.endswith(b"\x00"):
            raise ValueError("invalid log records")
    except (OSError, ValueError, subprocess.CalledProcessError):
        print("::error::Could not validate PR commit identities. Fetch the complete base and head histories.")
        return 1

    rejected = authors = committers = 0
    for _, author, committer in zip(fields[::3], fields[1::3], fields[2::3]):
        bad_author = not NOREPLY.fullmatch(author)
        bad_committer = committer.lower() != b"noreply@github.com" and not NOREPLY.fullmatch(committer)
        rejected += bad_author or bad_committer
        authors += bad_author
        committers += bad_committer
    if rejected:
        print(f"::error::{rejected} PR commits must use GitHub noreply identities "
              f"({authors} author fields, {committers} committer fields).")
        return 1
    print(f"PASS: GitHub noreply identities verified for {len(fields) // 3} PR commits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
