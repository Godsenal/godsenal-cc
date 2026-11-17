"""branch-pr's ship-prep against real throwaway git repos and a fake `gh` — no network."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "plugins/base/skills/branch-pr/scripts/ship-prep"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}

BODY = """제목 한 줄

## Why
한 문장.

## Review focus
> [!NOTE]
> **사람이 판단할 곳 없음.** 검사가 덮는다.

**위험도** low (문서) · two-way · squash 커밋 되돌리기

## Change outline
### 1. 문서
- 한 줄.

## Evidence
- [x] `make test` → pass
"""
NOTE = "> [!NOTE]\n> **사람이 판단할 곳 없음.** 검사가 덮는다."  # BODY's Review focus, and the `(확인)` item that replaces it
CONFIRM = "> [!IMPORTANT]\n> **사람이 볼 곳 1건**\n> 1. **실기기에서 확인** (확인)\n>    시뮬레이터 없음"


class Repo(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.origin = self.tmp / "origin.git"
        self.repo = self.tmp / "repo"
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.env = {**os.environ, **GIT_ENV, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}"}
        self.env.pop("GIT_INDEX_FILE", None)
        self.env.pop("AGENT_EVIDENCE_FILE", None)  # a run that sets it would hand its own evidence to every draft here
        self.git("init", "-q", "--bare", "-b", "main", str(self.origin), cwd=self.tmp)
        self.git("clone", "-q", str(self.origin), str(self.repo), cwd=self.tmp)
        self.write("README.md", "# app\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        self.git("push", "-q", "-u", "origin", "main")
        self.git("remote", "set-head", "origin", "main")
        self.fake_gh("exit 1")  # no PR, no network, unless a test says otherwise

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=self.env, capture_output=True, text=True, check=True).stdout.strip()

    def write(self, path, text):
        p = self.repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def fake_gh(self, script):
        gh = self.bin / "gh"
        gh.write_text(f"#!/bin/sh\necho \"$@\" >> \"{self.tmp}/gh.log\"\n{script}\n")
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)

    def gh_log(self):
        log = self.tmp / "gh.log"
        return log.read_text() if log.exists() else ""

    def run_prep(self, *args):
        p = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.repo, env=self.env, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def branch(self, name="feat/x"):
        self.git("checkout", "-q", "-b", name)

    def draft(self, text=BODY):
        return str(self.write("../draft.md", text))


class Start(Repo):
    def test_clean_tree_with_nothing_ahead_is_nothing_to_ship(self):
        code, out = self.run_prep("start")
        self.assertEqual(code, 3)
        self.assertIn("nothing to ship", out)
        self.assertEqual(self.git("for-each-ref", "refs/gbase/backup"), "")

    def test_backup_holds_tracked_and_untracked_changes_and_leaves_the_tree_alone(self):
        self.branch()
        self.write("README.md", "# app\nmore\n")
        self.write("src/new.ts", "export const a = 1\n")
        self.git("add", "README.md")
        before = self.git("status", "--porcelain")
        code, out = self.run_prep("start")
        self.assertEqual(code, 0, out)
        ref = next(l.split()[1] for l in out.splitlines() if l.startswith("backup: "))
        self.assertEqual(self.git("show", f"{ref}:src/new.ts"), "export const a = 1")
        self.assertEqual(self.git("show", f"{ref}:README.md"), "# app\nmore")
        self.assertEqual(self.git("status", "--porcelain"), before)
        self.assertIn("2 files changed", out)
        self.assertIn("next: group the files into commits", out)

    def test_missing_gh_is_not_a_crash(self):
        (self.bin / "gh").unlink()
        self.env["PATH"] = f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin"
        self.branch()
        self.write("a.py", "x = 1\n")
        code, out = self.run_prep("start")
        self.assertEqual(code, 0, out)
        self.assertIn("branch plan: commit on this branch", out)

    def test_default_branch_needs_a_new_branch(self):
        self.write("a.py", "x = 1\n")
        _, out = self.run_prep("start")
        self.assertIn("branch plan: on the default branch — create one", out)

    def test_fresh_feature_branch_is_used_as_is(self):
        self.branch("gbase/task")
        self.write("a.py", "x = 1\n")
        code, out = self.run_prep("start")
        self.assertEqual(code, 0)
        self.assertIn("branch plan: commit on this branch", out)

    def test_branch_with_its_own_history_and_no_pr_is_a_question(self):
        self.branch()
        self.write("a.py", "x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: a")
        self.write("b.py", "y = 1\n")
        code, out = self.run_prep("start")
        self.assertEqual(code, 2)
        self.assertIn("ask: feat/x already has 1 commits of its own and no open PR", out)
        code, out = self.run_prep("start", "--local")  # the caller owns the branch in local mode
        self.assertEqual(code, 0, out)

    def test_remote_branch_of_the_same_name_with_other_commits_is_a_question(self):
        self.branch()
        self.write("theirs.py", "z = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: theirs")
        self.git("push", "-q", "origin", "feat/x")
        self.git("checkout", "-q", "main")
        self.git("branch", "-q", "-D", "feat/x")
        self.branch()
        self.write("a.py", "x = 1\n")
        code, out = self.run_prep("start")
        self.assertEqual(code, 2)
        self.assertIn("ask: origin/feat/x already exists with commits this branch doesn't have", out)

    def test_branch_with_an_open_pr_pushes_to_it(self):
        self.branch()
        self.write("a.py", "x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: a")
        self.write("b.py", "y = 1\n")
        self.fake_gh('echo \'{"number":5,"url":"https://github.com/o/r/pull/5","state":"OPEN"}\'')
        code, out = self.run_prep("start")
        self.assertEqual(code, 0, out)
        self.assertIn("pushing updates the open PR https://github.com/o/r/pull/5", out)

    def test_clean_tree_with_commits_ahead_skips_the_commit_step(self):
        self.branch()
        self.write("a.py", "x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: a")
        code, out = self.run_prep("start")
        self.assertEqual(code, 0, out)
        self.assertIn("tree clean — 1 commits ahead already hold the change", out)
        self.assertIn("next: write the PR draft", out)
        self.assertNotIn("backup:", out)

    def pause(self, subject="wip: half", body="Intent: finish the form\n\nNext: wire submit"):
        self.write("form.ts", "export {}\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject, "-m", body)

    def test_unpushed_pause_commits_are_unwrapped_and_their_notes_printed(self):
        self.branch()
        self.pause()
        code, out = self.run_prep("start")
        self.assertEqual(code, 0, out)
        self.assertIn("Intent: finish the form", out)
        self.assertEqual(self.git("log", "-1", "--format=%s"), "init")
        self.assertIn("form.ts", self.git("status", "--porcelain"))

    def test_a_pushed_pause_commit_is_never_reset(self):
        self.branch()
        self.pause()
        self.git("push", "-q", "-u", "origin", "feat/x")
        self.write("more.ts", "export {}\n")
        self.run_prep("start", "--local")
        self.assertEqual(self.git("log", "-1", "--format=%s"), "wip: half")

    def test_a_hand_written_wip_commit_without_intent_stays(self):
        self.branch()
        self.pause(body="just saving")
        self.write("more.ts", "export {}\n")
        self.run_prep("start", "--local")
        self.assertEqual(self.git("log", "-1", "--format=%s"), "wip: half")

    def test_secret_file_and_token_are_questions_and_the_value_is_not_printed(self):
        self.branch()
        self.write(".env", "DB=postgres://x\n")
        self.write("src/cfg.ts", 'const k = "ghp_' + "a1B2" * 9 + '"\n')
        self.write(".env.example", "DB=\n")
        code, out = self.run_prep("start")
        self.assertEqual(code, 2)
        self.assertIn("ask: secret? .env — secret-looking file", out)
        self.assertIn("ask: secret? src/cfg.ts:1 — GitHub token", out)
        self.assertNotIn(".env.example —", out)
        self.assertNotIn("ghp_", out)

    def test_a_secret_in_an_unpushed_commit_is_caught_on_a_clean_tree(self):
        self.branch()
        self.write("src/cfg.ts", 'const k = "ghp_' + "a1B2" * 9 + '"\n')
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: cfg")
        code, out = self.run_prep("start")
        self.assertEqual(code, 2)
        self.assertIn("ask: secret? src/cfg.ts — GitHub token", out)

    def test_secret_shapes(self):
        import importlib.machinery, importlib.util
        loader = importlib.machinery.SourceFileLoader("ship_prep", str(SCRIPT))
        sp = importlib.util.module_from_spec(importlib.util.spec_from_loader("ship_prep", loader))
        loader.exec_module(sp)
        v = "a1B2c3D4e5F6g7H8i9J0k1L2"
        secrets = [f'STRIPE_SECRET_KEY = "sk_live_{v}"', f'DB_PASSWORD="{v}"', f'client_secret: "{v}"', f"API_KEY={v}", f"access_token: '{v}'",
                   "Authorization: Bearer " + ".".join(["eyJ" + "hbGciOiJIUzI1NiJ9", "eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0", v]), f'"privateKey": "{v}"']
        fine = ["token = getTokenFromEnvironment()", "password: string", 'const secretLabel = "비밀번호"', "api_key = os.environ['API_KEY']",
                "tokenizer = build_tokenizer_for_language_model", 'placeholder="Enter your password"']
        for line in secrets:
            self.assertTrue(sp.secret_hits([], [("f:1", line)]), line)
        for line in fine:
            self.assertEqual(sp.secret_hits([], [("f:1", line)]), [], line)

    def test_start_from_a_subdirectory_sees_the_whole_repo(self):
        self.write(".github/pull_request_template.md", "## What\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "docs")
        self.branch()
        self.write("newsecret.ts", "const k = 'AKIA" + "ABCDEFGHIJKLMNOP" + "'\n")
        sub = self.repo / "pkg" / "app"
        sub.mkdir(parents=True)
        p = subprocess.run([sys.executable, str(SCRIPT), "start", "--local"], cwd=sub, env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn("ask: secret? newsecret.ts:1 — AWS access key", p.stdout)
        self.assertIn(".github/pull_request_template.md", p.stdout)

    def test_conventions_files_are_listed(self):
        self.write(".github/pull_request_template.md", "## What\n")
        self.write("CONTRIBUTING.md", "rules\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "docs")
        self.git("config", "gbase.conventions", "/x/conv.md")
        self.branch()
        self.write("a.py", "x = 1\n")
        _, out = self.run_prep("start", "--local")
        self.assertIn("conventions — read before naming the branch, commits, or PR: /x/conv.md, .github/pull_request_template.md, CONTRIBUTING.md", out)

    def compat(self, files):
        self.branch()
        for f in files:
            self.write(f, "x\n")
        return self.run_prep("start", "--local")[1]

    def test_docs_tests_and_images_skip_compat_check(self):
        out = self.compat(["docs/guide.md", "src/__tests__/a.test.ts", "tests/fixtures/b.md", "assets/logo.png"])
        self.assertIn("compat: skip — only asset/doc/test files changed", out)
        self.assertIn("risk hint: low", out)

    def test_any_code_or_config_file_runs_compat_check(self):
        for i, f in enumerate(("src/a.ts", "package.json", ".claude-plugin/plugin.json", "config/app.yaml")):
            with self.subTest(f):
                self.git("checkout", "-q", "main")
                self.git("clean", "-qfd")
                self.git("checkout", "-q", "-b", f"b{i}")
                self.write("docs/x.md", "x\n")
                self.write(f, "x\n")
                self.assertIn("compat: run — gbase:compat-check on origin/main...HEAD", self.run_prep("start", "--local")[1])

    def test_code_that_only_looks_like_docs_runs_compat_check(self):
        for i, f in enumerate(("requirements.txt", "CMakeLists.txt", "docs/openapi.yaml", "src/app/docs/page.tsx", "tests/fixtures/seed.sql")):
            with self.subTest(f):
                self.git("checkout", "-q", "main")
                self.git("clean", "-qfd")
                self.git("checkout", "-q", "-b", f"d{i}")
                self.write(f, "x\n")
                out = self.run_prep("start", "--local")[1]
                self.assertIn("compat: run", out)
                self.assertNotIn("risk hint: low", out)

    def test_committed_files_count_toward_compat_and_risk(self):
        self.branch()
        self.write("db/migrations/0001_add.sql", "alter table t add c int;\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: migration")
        self.write("README.md", "# app\nnote\n")
        out = self.run_prep("start", "--local")[1]
        self.assertIn("compat: run", out)
        self.assertIn("risk hint: high — db/migrations/0001_add.sql", out)

    def test_high_risk_paths(self):
        out = self.compat([".github/workflows/ci.yml", "src/auth/session.ts", "app.json", "src/billing/charge.ts"])
        hint = next(l for l in out.splitlines() if l.startswith("risk hint"))
        self.assertTrue(hint.startswith("risk hint: high — .github/workflows/ci.yml, app.json, src/auth/session.ts"), hint)


class Check(Repo):
    def problems(self, text, *flags):
        code, out = self.run_prep("check", self.draft(text), *flags)
        return code, out

    def test_good_draft_passes(self):
        self.assertEqual(self.problems(BODY), (0, "draft: ok\n"))

    def test_draft_rules(self):
        cases = [
            (BODY.replace("제목 한 줄\n\n", "제목 한 줄\n## Why 바로\n", 1), "line 2 must be empty"),
            (BODY.replace("## Review focus", "## Focus"), "missing `## Review focus`"),
            (BODY.replace("## Evidence", "## Proof"), "missing `## Evidence`"),
            (BODY.replace("> [!NOTE]\n", ""), "Review focus needs its"),
            (BODY + "\n> [!WARNING]\n> 조심\n", "2 alert boxes"),
            (BODY.replace("> [!NOTE]\n", "") + "\n> [!NOTE]\n> 다른 곳\n", "Review focus needs its"),
            (BODY + "\n![after](/Users/me/shots/after.png)\n", "is a local path a reviewer can't open"),
            (BODY + "\n![after](~/shots/after.png)\n", "is a local path a reviewer can't open"),
            (BODY.replace("한 문장.", "<exactly one sentence: the problem>"), "template placeholder"),
            (BODY.replace("> **사람이 판단할 곳 없음.** 검사가 덮는다.", "\n".join(f"> {n}. **항목** (확인)" for n in range(1, 7))), "6 Review focus items"),
        ]
        for text, want in cases:
            code, out = self.problems(text)
            self.assertEqual(code, 1, want)
            self.assertIn(want, out)

    def test_an_unverified_evidence_line_needs_a_confirm_item(self):
        skip = BODY + "- [ ] behavior: skip — 로그인: 시뮬레이터 없음\n"
        differs = BODY + "- [x] behavior: 업로드 → pass (input: 1024px 사본; differs: 실기기는 5712px 원본)\n"
        for text in (skip, differs):
            code, out = self.problems(text)
            self.assertEqual(code, 1, text)
            self.assertIn("Review focus has no `(확인)` item", out)
            self.assertEqual(self.problems(text.replace(NOTE, CONFIRM))[0], 0, text)
            # an item of another kind doesn't answer it, and local mode checks the same
            self.assertEqual(self.problems(text.replace(NOTE, CONFIRM.replace("(확인)", "(결정)")))[0], 1)
            self.assertEqual(self.problems(text, "--local")[0], 1)
        self.assertEqual(self.problems(skip.replace(NOTE, CONFIRM.replace("(확인)", "(verify)")))[0], 0)  # a body written in English
        self.assertEqual(self.problems(BODY.replace("한 문장.", "behavior: skip 을 다루는 변경."))[0], 0)  # outside Evidence it is prose

    def test_a_skipped_behavior_check_is_not_a_checked_box(self):
        text = BODY.replace(NOTE, CONFIRM) + "- [x] behavior: skip — 시뮬레이터 없음\n"
        code, out = self.problems(text)
        self.assertEqual(code, 1)
        self.assertIn("not a checked box", out)

    def test_the_evidence_file_counts_even_when_the_draft_dropped_the_line(self):
        path = self.tmp / "evidence.jsonl"
        self.env["AGENT_EVIDENCE_FILE"] = str(path)
        cases = [({"step": "behavior", "result": "open", "command": "/verify login", "detail": "no simulator"}, 1),
                 ({"step": "checks", "result": "pass", "command": "pytest", "detail": "ok", "input": "fixture a; differs: real files are larger"}, 1),
                 ({"step": "behavior", "result": "skip", "command": "-", "detail": "low risk"}, 0),  # not required is not unverified
                 ({"step": "behavior", "result": "pass", "command": "/verify login", "detail": "ok", "input": "simulator"}, 0)]
        for record, want in cases:
            path.write_text("not json\n[1]\n{\"step\": \"checks\", \"command\": [\"a\"]}\n" + json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            self.assertEqual(self.problems(BODY)[0], want, record)
        still_open, closed = cases[0][0], {**cases[0][0], "result": "pass", "detail": "ok on a device"}
        path.write_text(json.dumps(still_open) + "\n" + json.dumps(closed) + "\n", encoding="utf-8")
        self.assertEqual(self.problems(BODY)[0], 0)  # a later pass for the same check closes the open line
        self.env["AGENT_EVIDENCE_FILE"] = str(self.tmp / "missing.jsonl")
        self.assertEqual(self.problems(BODY)[0], 0)

    def test_local_draft_may_embed_local_screenshots(self):
        self.assertEqual(self.problems(BODY + "\n![after](/Users/me/shots/after.png)\n", "--local")[0], 0)

    def test_uploaded_image_is_fine(self):
        self.assertEqual(self.problems(BODY + "\n![after](https://github.com/o/r/raw/gbase-assets/b/after.png)\n")[0], 0)

    def test_long_lead_is_a_warning_not_an_error(self):
        code, out = self.problems(BODY.replace("한 문장.", "한 문장.\n" + "- 줄\n" * 50))
        self.assertEqual(code, 0)
        self.assertIn("warn: ", out)


class Open(Repo):
    def commit_change(self):
        self.branch()
        self.write("a.py", "x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: a")

    def test_pushes_opens_and_prints_the_pr_line(self):
        self.commit_change()
        self.fake_gh('case "$1 $2" in "pr view") exit 1;; "pr create") echo "https://github.com/o/r/pull/9";; esac')
        code, out = self.run_prep("open", self.draft(), "--draft")
        self.assertEqual(code, 0, out)
        self.assertIn("\npr: https://github.com/o/r/pull/9\n", out)
        self.assertEqual(self.git("rev-parse", "origin/feat/x"), self.git("rev-parse", "HEAD"))
        self.assertRegex(self.gh_log(), r"pr create --title 제목 한 줄 --body-file - --draft")

    def test_bad_draft_stops_before_the_push(self):
        self.commit_change()
        code, out = self.run_prep("open", self.draft(BODY.replace("## Evidence", "## Proof")))
        self.assertEqual(code, 1)
        self.assertNotIn("feat/x", self.git("branch", "-r"))

    def test_uncommitted_change_to_a_tracked_file_stops_before_the_push(self):
        self.commit_change()
        self.write("a.py", "x = 2\n")
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 1)
        self.assertIn("uncommitted changes to tracked files", out)
        self.assertNotIn("feat/x", self.git("branch", "-r"))

    def test_partial_ships_without_the_files_left_out_on_purpose(self):
        self.commit_change()
        self.write("a.py", "x = 2\n")
        self.fake_gh('case "$1 $2" in "pr view") exit 1;; "pr create") echo "https://github.com/o/r/pull/9";; esac')
        code, out = self.run_prep("open", self.draft(), "--partial")
        self.assertEqual(code, 0, out)
        self.assertIn("note: left out on purpose (--partial) — say so in the report: a.py", out)
        self.assertEqual(self.git("show", "origin/feat/x:a.py"), "x = 1")

    def test_remote_can_be_named(self):
        self.commit_change()
        self.git("remote", "rename", "origin", "upstream")
        self.fake_gh('case "$1 $2" in "pr view") exit 1;; "pr create") echo "https://github.com/o/r/pull/9";; esac')
        self.assertEqual(self.run_prep("open", self.draft())[0], 1)
        code, out = self.run_prep("open", self.draft(), "--remote", "upstream")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.git("rev-parse", "upstream/feat/x"), self.git("rev-parse", "HEAD"))

    def test_untracked_leftovers_are_noted_not_blocking_and_not_deleted(self):
        self.commit_change()
        cache = self.write("__pycache__/a.pyc", "x")
        self.fake_gh('case "$1 $2" in "pr view") exit 1;; "pr create") echo "https://github.com/o/r/pull/9";; esac')
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertIn("note: untracked files stay out of the PR", out)
        self.assertTrue(cache.exists())

    def test_default_branch_is_refused(self):
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 1)
        self.assertIn("a PR needs its own branch", out)

    def test_existing_open_pr_gets_the_push_and_keeps_its_body(self):
        self.commit_change()
        self.fake_gh('case "$1 $2" in "pr view") echo \'{"url":"https://github.com/o/r/pull/5","state":"OPEN"}\';; esac')
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertIn("pr: https://github.com/o/r/pull/5", out)
        self.assertNotIn("pr create", self.gh_log())

    def test_rejected_push_is_reported_not_forced(self):
        self.commit_change()
        self.git("push", "-q", "-u", "origin", "feat/x")
        self.git("commit", "-q", "--amend", "-m", "feat: a (rewritten)")
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 1)
        self.assertIn("push failed — not retried, nothing forced", out)
        self.assertNotIn("pr create", self.gh_log())


if __name__ == "__main__":
    unittest.main()
