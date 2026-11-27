"""branch-pr's ship-prep against real throwaway git repos and a fake `gh` — no network."""
import json
import os
import re
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
        self.env["GBASE_HOME"] = str(self.tmp / "gbase-home")
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

    def commit_change(self, text="x = 1\n", message="feat: a"):
        if self.git("branch", "--show-current") == "main":
            self.branch()
        self.write("a.py", text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def draft(self, text=BODY):
        return str(self.write("../draft.md", text).resolve())


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
        self.assertIn("with no rule, `feat/` `fix/` `refactor/` `docs/` `chore/` + slug", out)

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

    def test_environment_file_adds_the_ticket_line_and_no_file_adds_none(self):
        self.branch()
        self.write("a.py", "x = 1\n")
        _, out = self.run_prep("start", "--local")
        self.assertNotIn("environment:", out)
        self.git("config", "gbase.conventions", "/x/env.md")
        _, out = self.run_prep("start", "--local")
        line = next(l for l in out.splitlines() if l.startswith("environment: "))
        self.assertIn("/x/env.md — when this change came from a ticket", line)
        doc = Path(re.search(r'in (\S+environment\.md)', line).group(1))
        self.assertTrue(doc.is_file(), doc)
        self.assertIn("## Shipping it", doc.read_text(encoding="utf-8"))

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
    def test_pushes_opens_and_prints_the_pr_line(self):
        self.commit_change()
        self.fake_gh('case "$1 $2" in "pr view") exit 1;; "pr create") echo "https://github.com/o/r/pull/9";; esac')
        code, out = self.run_prep("open", self.draft(), "--draft")
        self.assertEqual(code, 0, out)
        self.assertIn("\npr: https://github.com/o/r/pull/9\n", out)
        self.assertEqual(self.git("rev-parse", "origin/feat/x"), self.git("rev-parse", "HEAD"))
        self.assertRegex(self.gh_log(), r"pr create --title 제목 한 줄 --body-file - --draft")

    def test_open_pr_names_the_write_back_rule_only_with_an_environment_file(self):
        self.commit_change()
        self.fake_gh('case "$1 $2" in "pr view") exit 1;; "pr create") echo "https://github.com/o/r/pull/9";; esac')
        env = self.tmp / "env.md"
        env.write_text("# Environment\n\n## Write-back\n- link the PR on the ticket: on\n", encoding="utf-8")
        self.git("config", "gbase.conventions", str(env))
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertIn(f"\npr: https://github.com/o/r/pull/9\nenvironment: the PR is open — write back to the ticket only what {env} marks `on`", out)
        self.assertNotIn("already open", out)
        self.fake_gh('case "$1 $2" in "pr view") echo \'{"url":"https://github.com/o/r/pull/9","state":"OPEN"}\';; esac')
        code, out = self.run_prep("open", self.draft())
        self.assertIn("\npr: https://github.com/o/r/pull/9\nenvironment: the PR is open", out)
        self.assertIn("it was already open, so read the ticket first and skip a write it already shows", out)
        self.git("config", "--unset", "gbase.conventions")
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertNotIn("environment:", out)

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


class ReviewPolicy(Repo):
    GH = 'case "$1 $2" in "pr view") exit 1;; "pr create") echo "https://github.com/o/r/pull/9";; esac'

    def policy(self, lines):
        env = self.tmp / "env.md"
        env.write_text("# Environment: acme\n\n## Conventions\n- Branch: `feat/<slug>`\n" + lines, encoding="utf-8")
        self.git("config", "gbase.conventions", str(env))
        return env

    def test_no_policy_line_prints_nothing_and_asks_gh_for_nothing_more(self):
        for i, text in enumerate((None, "- Commit: conventional\n", "- Reviewers: none\n- Labels: -\n- PR size: 0 lines\n- Commit sign-off: off\n")):
            with self.subTest(text=text):
                if text:
                    self.policy(text)
                self.git("checkout", "-q", "main")
                self.branch(f"feat/p{i}")
                self.commit_change(message=f"feat: {text!r}")
                _, out = self.run_prep("start", "--local")
                for word in ("review policy", "reviewers:", "labels:", "size:", "sign", "review-policy.md"):
                    self.assertNotIn(word, out)
                self.fake_gh(self.GH)
                code, out = self.run_prep("open", self.draft())
                self.assertEqual(code, 0, out)
                self.assertRegex(self.gh_log().splitlines()[-1], r"^pr create --title 제목 한 줄 --body-file -$")
                self.assertNotIn("requested:", out)
                (self.tmp / "gh.log").unlink()

    def test_reviewers_and_labels_go_to_pr_create(self):
        self.policy("- Reviewers: @alice, acme/backend (CODEOWNERS 외)\n- Labels: `needs-review`, area: api\n")
        self.commit_change()
        _, out = self.run_prep("start")
        self.assertIn("review policy: reviewers alice, acme/backend · labels needs-review, area: api — from ", out)
        self.assertIn("review-policy.md before the first commit", out)
        self.assertNotIn("\nreviewers:", out)
        self.fake_gh(self.GH)
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertIn("--reviewer alice --reviewer acme/backend --label needs-review --label area: api", self.gh_log())
        self.assertIn("requested: reviewers alice, acme/backend · labels needs-review, area: api", out)

    def test_local_mode_reports_them_for_the_caller(self):
        self.policy("- Reviewers: @alice\n- Labels: needs-review\n")
        self.commit_change()
        _, out = self.run_prep("start", "--local")
        self.assertIn("\nreviewers: alice\nlabels: needs-review\n", out)

    def test_prose_on_the_reviewers_line_requests_nobody(self):
        self.policy("- Reviewers: CODEOWNERS가 배정한다\n- Labels: bug\n")
        self.commit_change()
        _, out = self.run_prep("start")
        self.assertIn("is not a list of logins or org/teams (CODEOWNERS가, 배정한다) — no reviewer is requested", out)
        self.assertIn("review policy: labels bug —", out)
        self.fake_gh(self.GH)
        self.run_prep("open", self.draft())
        self.assertNotIn("--reviewer", self.gh_log())

    def test_a_refused_reviewer_still_opens_the_pr_and_says_so(self):
        self.policy("- Reviewers: @gone\n")
        self.commit_change()
        self.fake_gh('case "$1 $2" in "pr view") exit 1;; "pr create") case "$*" in *--reviewer*) echo "could not resolve user gone" >&2; exit 1;; '
                     '*) echo "https://github.com/o/r/pull/9";; esac;; esac')
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertIn("note: GitHub refused the reviewers or labels of", out)
        self.assertIn("could not resolve user gone", out)
        self.assertIn("\npr: https://github.com/o/r/pull/9\n", out)

    def test_a_reviewer_refused_after_the_pr_was_made_keeps_that_pr(self):
        self.policy("- Reviewers: @me-the-author\n- Labels: bug\n")
        self.commit_change()
        made = self.tmp / "made"
        self.fake_gh(f'case "$1 $2" in "pr view") [ -f "{made}" ] && echo \'{{"url":"https://github.com/o/r/pull/9","state":"OPEN"}}\' || exit 1;; '
                     f'"pr create") touch "{made}"; echo "https://github.com/o/r/pull/9"; echo "pull request update failed: author" >&2; exit 1;; esac')
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertIn("pull request update failed", out)
        self.assertIn("\npr: https://github.com/o/r/pull/9\n", out)
        self.assertEqual(self.gh_log().count("pr create"), 1)

    def test_a_refused_reviewer_keeps_the_labels(self):
        self.policy("- Reviewers: @gone\n- Labels: bug\n")
        self.commit_change()
        self.fake_gh('case "$1 $2" in "pr view") exit 1;; "pr create") case "$*" in *--reviewer*) echo "no user gone" >&2; exit 1;; '
                     '*) echo "https://github.com/o/r/pull/9";; esac;; esac')
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertRegex(self.gh_log().splitlines()[-1], r"pr create .* --label bug$")

    def test_an_english_sentence_on_the_reviewers_line_is_prose(self):
        self.policy("- Reviewers: CODEOWNERS assigns them\n")
        self.commit_change()
        _, out = self.run_prep("start")
        self.assertIn("is not a list of logins or org/teams", out)
        self.assertNotIn("review policy:", out)

    def test_a_size_in_korean_reads_and_an_unreadable_one_is_a_note(self):
        self.branch()
        self.write("a.py", "x = 1\ny = 2\n")
        self.policy("## Shipping\n- PR size: 1줄 — ask\n")
        code, out = self.run_prep("start")
        self.assertEqual(code, 2, out)
        self.assertIn("ask: the change is 2 lines, over the 1", out)
        self.policy("## Shipping\n- PR size: about four hundred\n")
        _, out = self.run_prep("start")
        self.assertIn("the `PR size:` line of", out)
        self.assertIn("no size is checked", out)

    def test_a_local_check_refuses_a_commit_without_its_sign_off(self):
        self.policy("- Commit sign-off: on\n")
        self.commit_change()
        code, out = self.run_prep("check", self.draft(), "--local")
        self.assertEqual(code, 1, out)
        self.assertIn("have no `Signed-off-by:` trailer", out)
        self.git("commit", "-q", "--amend", "--no-edit", "-s")
        code, out = self.run_prep("check", self.draft(), "--local")
        self.assertEqual(code, 0, out)

    def test_a_merge_in_the_range_is_not_rebased_and_needs_no_trailer(self):
        self.policy("- Commit sign-off: on\n")
        self.branch()
        self.write("a.py", "x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: a")
        self.git("checkout", "-q", "main")
        self.write("b.py", "y = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "main: b")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "feat/x")
        self.git("merge", "-q", "--no-edit", "main")
        code, out = self.run_prep("check", self.draft(), "--local")
        self.assertEqual(code, 1, out)
        self.assertIn("1 commit(s) have no", out)
        self.assertIn("a merge commit", out)
        self.assertNotIn("git rebase --signoff", out)

    def test_a_trailer_of_someone_else_is_not_the_authors_sign_off(self):
        self.policy("- Commit sign-off: on\n")
        self.commit_change(message="feat: a\n\nSigned-off-by: other <o@example.invalid>")
        code, out = self.run_prep("check", self.draft(), "--local")
        self.assertEqual(code, 1, out)

    def test_a_refused_label_keeps_the_reviewers(self):
        self.policy("- Reviewers: @alice\n- Labels: not-made-yet\n")
        self.commit_change()
        self.fake_gh('case "$1 $2" in "pr view") exit 1;; "pr create") case "$*" in *--label*) echo "label not found" >&2; exit 1;; '
                     '*) echo "https://github.com/o/r/pull/9";; esac;; esac')
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertRegex(self.gh_log().splitlines()[-1], r"pr create .* --reviewer alice$")

    def test_a_sentence_on_the_labels_line_adds_no_label(self):
        self.policy("- Labels: set by the triage bot\n")
        self.commit_change()
        _, out = self.run_prep("start")
        self.assertIn("reads as a sentence (set by the triage bot)", out)
        self.fake_gh(self.GH)
        self.run_prep("open", self.draft())
        self.assertNotIn("--label", self.gh_log())

    def test_an_unsigned_merge_commit_under_gpgsign_is_refused(self):
        self.git("config", "commit.gpgsign", "true")
        self.git("config", "gpg.program", "false")
        self.branch()
        self.write("a.py", "x = 1\n")
        self.git("add", "-A")
        self.git("-c", "commit.gpgsign=false", "commit", "-q", "-m", "feat: a")
        self.git("push", "-q", "-u", "origin", "feat/x")  # the branch's own commit is already pushed
        self.git("checkout", "-q", "main")
        self.write("b.py", "y = 1\n")
        self.git("add", "-A")
        self.git("-c", "commit.gpgsign=false", "commit", "-q", "-m", "main: b")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "feat/x")
        self.git("-c", "commit.gpgsign=false", "merge", "-q", "--no-edit", "main")
        code, out = self.run_prep("check", self.draft(), "--local")
        self.assertEqual(code, 1, out)
        self.assertIn("1 commit(s) carry no signature", out)
        self.assertIn("a merge commit", out)

    def test_someone_elses_commit_is_theirs_to_sign_off(self):
        self.policy("- Commit sign-off: on\n")
        self.branch()
        self.write("a.py", "x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: a", "--author", "o <o@example.invalid>")
        code, out = self.run_prep("check", self.draft(), "--local")
        self.assertEqual(code, 1, out)
        self.assertIn("needs its author's own sign-off", out)

    def test_sign_off_is_required_on_unpushed_commits_only(self):
        self.policy("- Commit sign-off: on\n")
        self.branch()
        self.write("a.py", "x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: pushed earlier")
        self.git("push", "-q", "-u", "origin", "feat/x")
        _, out = self.run_prep("start")
        self.assertIn("sign-off on", out)
        self.write("a.py", "x = 2\n")
        self.git("commit", "-q", "-am", "feat: b")
        self.fake_gh(self.GH)
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 1, out)
        self.assertIn("1 commit(s) have no `Signed-off-by:` trailer", out)
        self.assertIn("git rebase --signoff", out)
        self.assertIn("nothing was pushed", out)
        self.assertNotIn("pr create", self.gh_log())
        self.git("commit", "-q", "--amend", "--no-edit", "-s")
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertIn("Signed-off-by: t <t@example.invalid>", self.git("log", "-1", "--format=%B"))

    def test_an_unsigned_commit_under_gpgsign_stops_and_is_never_bypassed(self):
        self.git("config", "commit.gpgsign", "true")
        self.git("config", "gpg.program", "false")
        self.branch()
        self.write("a.py", "x = 1\n")
        self.git("add", "-A")
        sign = subprocess.run(["git", "commit", "-q", "-m", "feat: a"], cwd=self.repo, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(sign.returncode, 0)
        self.git("-c", "commit.gpgsign=false", "commit", "-q", "-m", "feat: a")
        _, out = self.run_prep("start")
        self.assertIn("signing: commit.gpgsign is on — a commit that fails to sign stops the run; never `--no-gpg-sign`", out)
        self.fake_gh(self.GH)
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 1, out)
        self.assertIn("error: commit.gpgsign is on and 1 commit(s) carry no signature", out)
        self.assertIn("Never `--no-gpg-sign`", out)
        self.assertNotIn("pr create", self.gh_log())

    def test_over_pr_size_needs_the_split_as_item_one(self):
        self.policy("## Shipping\n- PR size: 50 lines\n")
        self.branch()
        self.write("a.py", "".join(f"x{i} = {i}\n" for i in range(120)))
        _, out = self.run_prep("start")
        self.assertIn("review policy: PR size 50 lines —", out)
        self.assertIn("size: 120 lines, over the 50 of PR size", out)
        self.assertNotIn("ask:", out)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: big")
        self.fake_gh(self.GH)
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 1, out)
        self.assertIn("the change is 120 lines, over the 50 of PR size — Review focus item 1", out)
        split = "> [!IMPORTANT]\n> **사람이 볼 곳 1건**\n> 1. **나눌 수 있다** 상수와 사용처를 두 PR로 (크기)\n>    120줄"
        code, out = self.run_prep("open", self.draft(BODY.replace(NOTE, split)))
        self.assertEqual(code, 0, out)

    def test_under_pr_size_needs_nothing_and_ask_asks_only_when_over(self):
        self.policy("## Shipping\n- PR size: 500 lines, ask\n")
        self.branch()
        self.write("a.py", "x = 1\n")
        code, out = self.run_prep("start")
        self.assertNotIn("size:", out.replace("PR size", ""))
        self.assertEqual(code, 0, out)
        self.policy("## Shipping\n- **PR size**: `1` line, ask\n")
        self.write("a.py", "x = 1\ny = 2\n")
        code, out = self.run_prep("start")
        self.assertEqual(code, 2, out)
        self.assertIn("ask: the change is 2 lines, over the 1 the environment file sets — split it, or open it as one PR?", out)


class Preview(Repo):
    """The stop before the PR: the environment file's `before the PR: preview` line, or a preview recorded on request."""
    CREATED = 'case "$1 $2" in "pr view") exit 1;; "pr create") echo "https://github.com/o/r/pull/9";; esac'

    def setting(self, text="# Environment: acme\n\n## Shipping\n- before the PR: preview\n"):
        env = self.tmp / "env.md"
        env.write_text(text, encoding="utf-8")
        self.git("config", "gbase.conventions", str(env))
        return env

    def line(self, out):
        return next((l for l in out.splitlines() if l.startswith("preview: ")), None)

    def pushed(self):
        return "feat/x" in self.git("ls-remote", "--heads", "origin")

    def test_no_setting_and_no_flag_says_nothing_about_a_preview(self):
        self.branch()
        self.write("a.py", "x = 1\n")
        for env_text in (None, "# Environment\n\n## Shipping\n- before the PR: open\n", "# Environment\n\n## Conventions\n- Branch: `feat/<slug>`\n"):
            if env_text:
                self.setting(env_text)
            code, out = self.run_prep("start")
            self.assertEqual(code, 0, out)
            self.assertNotIn("preview:", out)

    def test_the_environment_line_turns_it_on_and_names_the_reference(self):
        self.branch()
        self.write("a.py", "x = 1\n")
        env = self.setting()
        for text in ("## Shipping\n- before the PR: preview\n", "## Shipping\n* **Before the PR**: `preview` (신규 입사 기간)\n",
                     "## Shipping\nbefore the pr : Preview\n"):
            env.write_text(text, encoding="utf-8")
            _, out = self.run_prep("start")
            line = self.line(out)
            self.assertIn(f'preview: on — {env} says "before the PR: preview": push nothing and open no PR', line, text)
            doc = Path(re.search(r"read (\S+preview\.md)", line).group(1))
            self.assertTrue(doc.is_file(), doc)
            self.assertIn("next: group the files into commits, then write the PR draft, then `ship-prep preview <draft>` instead of `open`", out)
        self.assertNotIn("preview:", self.run_prep("start", "--local")[1])

    def test_an_open_pr_is_not_held_back(self):
        self.setting()
        self.commit_change()
        self.write("a.py", "x = 2\n")
        self.fake_gh('case "$1 $2" in "pr view") echo \'{"number":5,"url":"https://github.com/o/r/pull/5","state":"OPEN"}\';; esac')
        _, out = self.run_prep("start")
        self.assertIn("pushing updates the open PR", out)
        self.assertNotIn("preview:", out)
        self.git("commit", "-q", "-am", "fix: b")
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 0, out)
        self.assertTrue(self.pushed())

    def test_open_is_refused_until_a_preview_is_recorded_for_head(self):
        self.setting()
        self.commit_change()
        code, out = self.run_prep("open", self.draft())
        self.assertEqual(code, 1)
        self.assertIn('says "before the PR: preview" and no preview was recorded', out)
        self.assertIn("nothing pushed", out)
        self.assertFalse(self.pushed())
        self.assertNotIn("pr create", self.gh_log())

    def test_the_request_can_waive_the_setting(self):
        self.setting()
        self.commit_change()
        self.fake_gh(self.CREATED)
        code, out = self.run_prep("open", self.draft(), "--no-preview")
        self.assertEqual(code, 0, out)
        self.assertIn("pr: https://github.com/o/r/pull/9", out)
        self.assertTrue(self.pushed())

    def record(self, draft, *flags, text="# PR 미리보기: 제목\n\n## 이대로 열릴 PR\n| 브랜치 |\n"):
        """`ship-prep preview <draft> --write` with the preview text on stdin: the call that records the commit as shown."""
        p = subprocess.run([sys.executable, str(SCRIPT), "preview", draft, "--write", *flags], cwd=self.repo, env=self.env,
                           input=text, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def states(self):
        return [json.loads(f.read_text(encoding="utf-8")) for f in (self.repo / ".git" / "gbase").glob("preview-*.json")]

    def test_the_first_call_prints_what_would_open_and_records_nothing(self):
        self.setting()
        self.commit_change()
        self.write("b.py", "y = 1\ny = 2\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: b")
        draft = self.draft(BODY + "\n![after](/Users/me/shots/after.png)\n")  # not uploaded before the PR: a local path is fine here
        code, out = self.run_prep("preview", draft)
        self.assertEqual(code, 0, out)
        head = self.git("rev-parse", "HEAD")
        self.assertIn(f"ship: local feat/x @{head[:7]} — 2 commits, not pushed\nPR 본문 초안: {draft}\npreview: ", out)
        self.assertIn("title: 제목 한 줄", out)
        self.assertRegex(out, r"commits \(origin/main\.\.HEAD\):\n  \w{7} feat: a\n  \w{7} feat: b\n")
        self.assertIn("  +1 -0  a.py\n  +2 -0  b.py\n", out)
        self.assertIn("next: nothing is recorded yet", out)
        self.assertEqual(self.states(), [])
        self.assertEqual(self.git("status", "--porcelain"), "")
        # nobody has read anything yet, so the PR stays closed
        self.fake_gh(self.CREATED)
        self.assertEqual(self.run_prep("open", draft)[0], 1)
        self.assertFalse(self.pushed())
        self.assertNotIn("pr create", self.gh_log())

    def test_write_saves_the_text_and_records_the_commit_as_shown(self):
        self.commit_change()
        self.write("scratch.log", "x\n")
        draft = self.draft()
        text = "# PR 미리보기: 제목\n\n## 이대로 열릴 PR\n| 브랜치 |\n"
        code, out = self.record(draft, text=text)
        self.assertEqual(code, 0, out)
        head = self.git("rev-parse", "HEAD")
        file = Path(self.line(out)[len("preview: "):])
        self.assertEqual(file.parent, self.tmp / "gbase-home" / "previews")  # outside the repo and its git dir
        self.assertRegex(file.name, r"^repo-feat-x-[0-9a-f]{6}\.md$")
        self.assertEqual(file.read_text(encoding="utf-8"), text)
        self.assertIn(f"saved: 4 lines, and @{head[:7]} recorded as the commit that was shown", out)
        state = json.loads((self.repo / ".git" / "gbase" / f"preview-{head}.json").read_text(encoding="utf-8"))  # the name go's Step 1 reads
        self.assertEqual((state["reviewed"], state["branch"], state["head"], state["draft"], state["preview"], state["untracked"], state["left_out"]),
                         (False, "feat/x", head, draft, str(file), ["scratch.log"], []))
        code, out = self.run_prep("preview", draft, "--reviewed")  # dropped without a word, the next go would review again
        self.assertEqual(code, 1)
        self.assertIn("--reviewed goes with --write", out)
        self.assertEqual(self.record(draft, "--reviewed")[0], 0)
        self.assertEqual([s["reviewed"] for s in self.states()], [True])  # one record per branch
        code, out = self.record(draft, text=" \n")
        self.assertEqual(code, 1)
        self.assertIn("stdin was empty", out)
        self.assertEqual(file.read_text(encoding="utf-8"), text)  # the saved preview is not blanked

    def test_two_repos_of_the_same_folder_name_keep_separate_preview_files(self):
        self.commit_change()
        first = self.line(self.record(self.draft())[1])
        other = self.tmp / "other" / "repo"
        other.parent.mkdir()
        self.git("clone", "-q", str(self.origin), str(other), cwd=self.tmp)
        self.git("checkout", "-q", "-b", "feat/x", cwd=other)
        (other / "a.py").write_text("x = 1\n")
        self.git("add", "-A", cwd=other)
        self.git("commit", "-q", "-m", "feat: a", cwd=other)
        p = subprocess.run([sys.executable, str(SCRIPT), "preview", self.draft()], cwd=other, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(self.line(p.stdout), first)

    def test_preview_needs_a_branch_commits_a_good_draft_a_committed_tree_and_a_base(self):
        code, out = self.run_prep("preview", self.draft())
        self.assertEqual(code, 1)
        self.assertIn("needs its own branch", out)
        self.branch()
        self.assertEqual(self.run_prep("preview", self.draft())[0], 3)
        self.commit_change()
        code, out = self.run_prep("preview", self.draft(BODY.replace("## Evidence", "## Proof")))
        self.assertEqual(code, 1)
        self.assertIn("missing `## Evidence`", out)
        self.write("a.py", "x = 2\n")
        code, out = self.record(self.draft())
        self.assertEqual(code, 1)
        self.assertIn("the preview would describe a PR without them: a.py", out)
        self.assertEqual(self.states(), [])
        self.git("checkout", "-q", "a.py")
        # no default branch to be found: say so, instead of "nothing to ship" while `open` waits for a preview
        self.git("remote", "remove", "origin")
        self.git("branch", "-q", "-D", "main")
        code, out = self.record(self.draft())
        self.assertEqual(code, 1)
        self.assertIn("can't tell which branch the PR goes to", out)

    def test_open_continues_from_the_prepared_commits_and_draft(self):
        self.setting()
        self.commit_change()
        draft = self.draft(BODY + "\n![after](/Users/me/shots/after.png)\n")
        self.assertEqual(self.record(draft)[0], 0)
        head = self.git("rev-parse", "HEAD")
        # the one edit between the preview and the PR: the screenshot is uploaded and the line `assets` printed, its own label included, is pasted in
        Path(draft).write_text(Path(draft).read_text(encoding="utf-8").replace("![after](/Users/me/shots/after.png)", "![after-1](https://github.com/o/r/raw/gbase-assets/feat/x/after-1.png)"),
                               encoding="utf-8")
        self.fake_gh(self.CREATED)
        code, out = self.run_prep("open", draft, "--draft")
        self.assertEqual(code, 0, out)
        self.assertIn("pr: https://github.com/o/r/pull/9", out)
        self.assertEqual(self.git("rev-parse", "origin/feat/x"), head)  # the commits made before the preview, unchanged
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertRegex(self.gh_log(), r"pr create --title 제목 한 줄 --body-file - --draft")
        self.assertEqual(self.states(), [])  # used up: the next change is previewed anew

    def test_a_later_session_finds_the_prepared_preview_and_is_told_to_ask_again(self):
        self.setting()
        self.commit_change()
        self.write("scratch.log", "x\n")  # there when the preview was made: not a change
        draft = self.draft()
        self.record(draft)
        code, out = self.run_prep("start")
        self.assertEqual(code, 0, out)  # no question about "commits of its own and no open PR"
        line = self.line(out)
        self.assertIn(f"preview: prepared — feat/x @{self.git('rev-parse', '--short=7', 'HEAD')} is what", line)
        self.assertIn(f"(draft {draft}) and nothing changed since: run no review or check again", line)
        self.assertIn("next: show the preview again and ask", out)
        self.assertNotIn("preview: on", out)
        # also when the stop was asked for once and no setting is written anywhere
        self.git("config", "--unset", "gbase.conventions")
        self.assertIn("preview: prepared — ", self.run_prep("start")[1])

    def test_a_change_after_the_preview_is_named_and_blocks_open_until_previewed_again(self):
        self.setting()
        self.commit_change()
        draft = self.draft()
        self.record(draft)
        shown = self.git("rev-parse", "--short=7", "HEAD")
        self.fake_gh(self.CREATED)
        self.write("c.py", "z = 1\n")  # a new file alone: it would stay out of the PR without a word
        self.assertIn(f"preview: changed — since the preview of @{shown}: c.py; re-check only these", self.line(self.run_prep("start")[1]))
        self.assertEqual(self.run_prep("open", draft)[0], 1)
        self.write("a.py", "x = 2\n")
        code, out = self.run_prep("start")
        self.assertEqual(code, 0, out)  # the prepared commits are not "a branch with its own history": no question
        self.assertIn(f"preview: changed — since the preview of @{shown}: a.py, c.py; re-check only these", self.line(out))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "fix: review")
        self.assertIn(f"preview: changed — since the preview of @{shown}: a.py, c.py", self.run_prep("start")[1])
        code, out = self.run_prep("open", draft)
        self.assertEqual(code, 1)
        self.assertIn(f"what would open is not what the preview of @{shown} showed — changed since: a.py, c.py; nothing pushed", out)
        self.assertFalse(self.pushed())
        self.assertEqual(self.record(draft)[0], 0)
        self.assertEqual(len(self.states()), 1)
        self.assertEqual(self.run_prep("open", draft)[0], 0)
        self.assertTrue(self.pushed())

    def test_an_amended_commit_is_not_the_one_that_was_shown(self):
        self.setting()
        self.commit_change()
        draft = self.draft()
        self.record(draft)
        self.write("a.py", "x = 9\n")
        self.git("commit", "-q", "-a", "--amend", "-m", "feat: a")
        self.assertIn("preview: changed — since the preview of @", self.run_prep("start")[1])
        self.assertIn(": a.py; re-check only these", self.run_prep("start")[1])
        self.fake_gh(self.CREATED)
        self.assertEqual(self.run_prep("open", draft)[0], 1)
        self.assertFalse(self.pushed())

    def test_files_left_out_on_purpose_are_not_a_change(self):
        self.setting()
        self.commit_change()
        self.write("README.md", "# app\nunrelated wip\n")
        draft = self.draft()
        code, out = self.record(draft, "--partial")
        self.assertEqual(code, 0, out)
        self.assertIn("preview: prepared — ", self.run_prep("start")[1])
        self.fake_gh(self.CREATED)
        code, out = self.run_prep("open", draft, "--partial")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.git("show", "origin/feat/x:README.md"), "# app")

    def test_a_draft_or_preview_file_that_is_no_longer_the_one_shown_is_a_change(self):
        self.setting()
        self.commit_change()
        draft = self.draft()
        self.record(draft)
        shown = Path(draft).read_text(encoding="utf-8")
        # another branch of the same checkout wrote its own PR over the shared draft path
        Path(draft).write_text(shown.replace("제목 한 줄", "다른 브랜치의 제목"), encoding="utf-8")
        self.assertIn(f"preview: changed — since the preview of @{self.git('rev-parse', '--short=7', 'HEAD')}: the PR draft ({draft})", self.run_prep("start")[1])
        self.fake_gh(self.CREATED)
        code, out = self.run_prep("open", draft)
        self.assertEqual(code, 1)
        self.assertIn("changed since: the PR draft", out)
        self.assertNotIn("pr create", self.gh_log())
        Path(draft).unlink()
        self.assertIn("preview: changed — ", self.run_prep("start")[1])
        Path(draft).write_text(shown, encoding="utf-8")
        self.assertIn("preview: prepared — ", self.run_prep("start")[1])
        Path(self.states()[0]["preview"]).unlink()
        self.assertIn("the preview file is missing", self.run_prep("start")[1])

    def test_only_an_image_link_on_one_line_is_left_out_of_the_draft_comparison(self):
        self.commit_change()
        unclosed = BODY + "\n![after](https://example.invalid/a.png\n검증: 통과 (로컬)\n"
        draft = self.draft(unclosed)
        self.record(draft)
        Path(draft).write_text(unclosed.replace("검증: 통과", "검증: 건너뜀"), encoding="utf-8")
        self.assertIn("preview: changed — ", self.run_prep("start")[1])
        self.assertIn("the PR draft", self.run_prep("start")[1])

    def test_a_one_off_preview_holds_open_to_the_shown_commit_too(self):
        self.commit_change()
        draft = self.draft()
        self.record(draft)  # no environment file: the user asked to see it first
        self.commit_change("x = 3\n", "fix: late")
        self.fake_gh(self.CREATED)
        self.assertEqual(self.run_prep("open", draft)[0], 1)
        self.assertFalse(self.pushed())

    def test_a_preview_of_another_branch_is_not_this_branchs(self):
        self.commit_change()
        self.record(self.draft())
        self.git("checkout", "-q", "main")
        self.git("checkout", "-q", "-b", "feat/y")
        self.write("b.py", "y = 1\n")
        self.assertNotIn("preview:", self.run_prep("start")[1])

    def test_an_open_pr_drops_the_record(self):
        self.commit_change()
        self.record(self.draft())
        self.fake_gh('case "$1 $2" in "pr view") echo \'{"number":5,"url":"https://github.com/o/r/pull/5","state":"OPEN"}\';; esac')
        self.assertNotIn("preview:", self.run_prep("start")[1])
        self.assertEqual(self.states(), [])

    def test_an_unreadable_environment_file_holds_the_pr_back_and_says_why(self):
        self.branch()
        self.write("a.py", "x = 1\n")
        missing = self.tmp / "moved-away.md"
        self.git("config", "gbase.conventions", str(missing))
        _, out = self.run_prep("start")
        self.assertIn(f"note: the environment file {missing} can't be read", out)
        self.assertNotIn("preview:", out)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: a")
        self.fake_gh(self.CREATED)
        # the file may hold `before the PR: preview`: saved in another encoding, it must not read as "no setting"
        env = self.tmp / "env.md"
        env.write_bytes("## Shipping\n- before the PR: preview (신규 입사 기간)\n".encode("cp949"))
        for path in (missing, env):
            self.git("config", "gbase.conventions", str(path))
            code, out = self.run_prep("open", self.draft())
            self.assertEqual(code, 1, path)
            self.assertIn(f"the environment file {path} can't be read", out)
            self.assertIn("nothing pushed", out)
            self.assertFalse(self.pushed())
        self.assertEqual(self.run_prep("open", self.draft(), "--no-preview")[0], 0)
        self.setting("# Environment\n")
        self.assertNotIn("can't be read", self.run_prep("start")[1])

    def test_a_reworded_or_lost_commit_is_not_the_one_that_was_shown(self):
        self.commit_change()
        draft = self.draft()
        self.record(draft)
        shown = self.git("rev-parse", "--short=7", "HEAD")
        self.git("commit", "-q", "--amend", "-m", "feat: a, reworded")  # same files, another commit: its message is part of the PR
        head = self.git("rev-parse", "--short=7", "HEAD")
        self.assertIn(f"preview: changed — since the preview of @{shown}: the commit itself (@{shown} → @{head})", self.run_prep("start")[1])
        # the previewed commit was pruned (gc after a rebuild): nothing to compare with, so nothing is taken as unchanged
        state_file = next((self.repo / ".git" / "gbase").glob("preview-*.json"))
        state = json.loads(state_file.read_text(encoding="utf-8"))
        state_file.write_text(json.dumps({**state, "head": "0" * 40}), encoding="utf-8")
        self.assertIn("preview: changed — since the preview of @0000000: the previewed commit @0000000 is gone", self.run_prep("start")[1])
        self.fake_gh(self.CREATED)
        self.assertEqual(self.run_prep("open", draft)[0], 1)
        self.assertFalse(self.pushed())

    def test_a_branch_pushed_by_hand_is_not_called_unpushed(self):
        self.commit_change()
        self.git("push", "-q", "origin", "feat/x")
        _, out = self.run_prep("preview", self.draft())
        self.assertRegex(out, r"ship: local feat/x @\w{7} — 1 commits, already on origin/feat/x, no PR\n")

if __name__ == "__main__":
    unittest.main()
