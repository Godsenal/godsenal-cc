"""go's stage-delta: the snapshot leaves the repo as it was, and each `next:` line follows from what changed."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "plugins/base/skills/go/scripts/stage-delta"
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@e", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "AGENT_HEADLESS": "", "AGENT_SHIP_OWNER": ""}


class Repo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.write("src/a.ts", "export const a = 1;\nexport const b = 2;\n")
        self.write(".gitignore", "build/\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.dir, env=ENV, capture_output=True, text=True, check=True).stdout

    def write(self, path, text):
        file = self.dir / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)

    def run_script(self, *args, cwd=None, env=None):
        result = subprocess.run([str(SCRIPT), *args], cwd=cwd or self.dir, env={**ENV, **(env or {})},
                                capture_output=True, text=True)
        return result.returncode, result.stdout.strip().splitlines()

    def mark(self):
        code, out = self.run_script("mark", "medium")
        self.assertEqual(code, 0, out)
        self.assertTrue(out[0].startswith("mark: "), out)
        return out[0].split()[1]


class Mark(Repo):
    def test_leaves_index_stash_and_tree_alone(self):
        self.write("src/a.ts", "export const a = 3;\nexport const b = 2;\n")
        self.write("src/new.ts", "export const c = 1;\n")
        self.git("add", "src/a.ts")
        before = (self.git("diff", "--cached", "--name-only"), self.git("status", "--porcelain"),
                  self.git("stash", "list"))
        self.mark()
        after = (self.git("diff", "--cached", "--name-only"), self.git("status", "--porcelain"),
                 self.git("stash", "list"))
        self.assertEqual(before, after)

    def test_captures_untracked_files_and_skips_ignored_ones(self):
        self.write("src/new.ts", "export const c = 1;\n")
        self.write("build/out.js", "x\n")
        tree = self.mark()
        names = self.git("ls-tree", "-r", "--name-only", tree).split()
        self.assertIn("src/new.ts", names)
        self.assertNotIn("build/out.js", names)

    def test_the_mark_lives_in_the_git_dir(self):
        tree = self.mark()
        self.assertEqual((self.dir / ".git/gbase/stage-mark").read_text(), f"{tree}\nfinder: code-review medium\n")
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_low_owes_no_finder_unless_headless(self):
        _, out = self.run_script("mark", "low")
        self.assertEqual(out[1:], ["finder: none — low risk; monitor's self-review covers it", "next: launch polish"])
        code, out = self.run_script("mark", "low", env={"AGENT_HEADLESS": "1"})
        self.assertEqual(code, 0)
        self.assertEqual(out[1], "finder: code-review low — owed")
        self.assertTrue(out[-1].startswith("next: launch polish and the finder in one message"), out)

    def test_no_review_owes_no_finder(self):
        _, out = self.run_script("mark", "high", "--no-review", env={"AGENT_HEADLESS": "1"})
        self.assertEqual(out[1:], ["finder: none — review skipped (--no-review, or a scope review skips)", "next: launch polish"])

    def test_mark_needs_a_risk(self):
        code, _ = self.run_script("mark")
        self.assertEqual(code, 2)
        code, _ = self.run_script("mark", "urgent")
        self.assertEqual(code, 2)

    def test_the_owed_finder_survives_polish(self):
        self.run_script("mark", "low", env={"AGENT_HEADLESS": "1"})
        _, out = self.run_script("polish")
        self.assertTrue(out[-1].startswith("next: wait for the finder (code-review low), then Step 3 of /"), out)
        self.assertTrue((self.dir / ".git/gbase/stage-mark").read_text().endswith("finder: code-review low\n"))

    def test_without_a_finder_nothing_waits(self):
        self.run_script("mark", "low")
        _, out = self.run_script("polish")
        self.assertEqual(out[-1], "next: nothing to review")

    def test_an_orchestrator_owned_low_run_owes_a_finder(self):
        _, out = self.run_script("mark", "low", env={"AGENT_SHIP_OWNER": "orchestrator"})
        self.assertEqual(out[1], "finder: code-review low — owed")

    def test_mark_names_the_script_for_its_later_calls(self):
        _, out = self.run_script("mark", "medium")
        self.assertTrue(out[-1].endswith(f"its later calls are `{SCRIPT.resolve()} polish|review`"), out)

    def test_an_unknown_command_prints_usage(self):
        code, out = self.run_script("polsih")
        self.assertEqual(code, 2)
        self.assertIn("stage-delta mark", "\n".join(out))

    def test_says_what_comes_next(self):
        _, out = self.run_script("mark", "medium")
        self.assertEqual(out[1], "finder: code-review medium — owed")
        self.assertRegex(out[-1], r"^next: launch polish and the finder in one message: .*/go/references/review\.md")

    def test_a_failed_mark_leaves_no_earlier_mark_behind(self):
        self.mark()
        stale = self.dir / ".git/gbase/stage-mark"
        objects = self.dir / ".git/objects"
        objects.chmod(0o500)
        try:
            self.write("src/a.ts", "export const a = 9;\n")
            code, out = self.run_script("mark", "medium")
        finally:
            objects.chmod(0o755)
        self.assertEqual(code, 1)
        self.assertTrue(out[-1].startswith("next: read the diff yourself — take each stage's changes"), out)
        self.assertFalse(stale.exists())
        code, out = self.run_script("polish")
        self.assertEqual(code, 1, out)

    def test_outside_a_repo_mark_says_read_the_diff_yourself(self):
        with tempfile.TemporaryDirectory() as bare:
            code, out = self.run_script("mark", "medium", cwd=bare)
        self.assertEqual(code, 1)
        self.assertTrue(out[-1].startswith("next: read the diff yourself — take each stage's changes"), out)

    def test_from_a_subdirectory_it_starts_from_the_real_index(self):
        self.write("gen/x.py", "a = 1\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "gen")
        self.write(".gitignore", "build/\ngen/\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "ignore gen")
        sub = self.dir / "src"
        self.run_script("mark", "medium", cwd=sub)
        self.write("gen/x.py", "a = 2\n")
        _, out = self.run_script("polish", cwd=sub)
        self.assertIn("gen/x.py: -1, +1", out)

    def test_diff_relative_does_not_hide_files_outside_cwd(self):
        self.git("config", "diff.relative", "true")
        self.write("lib/b.ts", "export const b = 1;\n")
        sub = self.dir / "src"
        self.run_script("mark", "medium", cwd=sub)
        self.write("lib/b.ts", "export const b = 2;\n")
        _, out = self.run_script("polish", cwd=sub)
        self.assertIn("lib/b.ts: -1, +1", out)


class Polish(Repo):
    def test_outside_a_repo_says_read_the_diff_yourself(self):
        with tempfile.TemporaryDirectory() as bare:
            code, out = self.run_script("polish", cwd=bare)
        self.assertEqual(code, 1)
        self.assertEqual(out[-1], "next: read the diff yourself — a polish edit to a line that is not a comment → review it; none → nothing to review")

    def test_polish_without_a_mark_says_read_the_diff_yourself(self):
        code, out = self.run_script("polish")
        self.assertEqual(code, 1)
        self.assertEqual(out[-1], "next: read the diff yourself — a polish edit to a line that is not a comment → review it; none → nothing to review")

    def test_no_change_since_the_mark(self):
        self.write("src/a.ts", "export const a = 5;\nexport const b = 2;\n")  # the change under review
        tree = self.mark()
        _, out = self.run_script("polish")
        self.assertEqual(out[:2], [f"mark: {tree}", "polish delta: none"])
        self.assertTrue(out[-1].startswith("next: wait for the finder (code-review medium), then Step 3 of "), out)

    def test_deleted_comments_only_need_no_review(self):
        self.write("src/a.ts", "// narrates a\nexport const a = 1;\nexport const b = 2;\n")
        self.mark()
        self.write("src/a.ts", "export const a = 1;\nexport const b = 2;\n")
        self.write("README.md", "prose\n")
        _, out = self.run_script("polish")
        self.assertTrue(out[-1].startswith("next: wait for the finder (code-review medium), then Step 3 of "), out)
        self.assertTrue(out[1].startswith("polish delta: comments or prose only, in 2 files"), out)

    def test_a_code_edit_is_sent_to_review_with_its_lines(self):
        tree = self.mark()
        self.write("src/a.ts", "export const a = 1;\nexport const b = a + 1;\n")
        _, out = self.run_script("polish")
        self.assertIn("src/a.ts: -2, +2", out)
        self.assertIn("polish delta: code in 1 file", out)
        self.assertTrue(any(line.startswith(f"diff: git diff --no-relative {tree} ") for line in out), out)
        self.assertRegex(out[-1], r"^next: review the polish delta — .*candidates; read /.*/go/references/deltas\.md$")

    def test_an_edit_to_an_untracked_file_counts(self):
        self.write("src/new.ts", "export const c = 1;\n")
        self.mark()
        self.write("src/new.ts", "export const c = 2;\n")
        _, out = self.run_script("polish")
        self.assertIn("src/new.ts: -1, +1", out)

    def test_a_json_edit_is_code(self):
        self.write("cfg.json", '{"a": 1}\n')
        self.mark()
        self.write("cfg.json", '{"a": 2}\n')
        _, out = self.run_script("polish")
        self.assertRegex(out[-1], r"^next: review the polish delta — .*candidates; read /.*/go/references/deltas\.md$")

    def test_its_mark_is_where_review_starts(self):
        tree = self.mark()
        self.write("src/a.ts", "export const a = 1;\nexport const b = a + 1;\n")
        _, out = self.run_script("polish")
        after = out[0].split()[1]
        self.assertNotEqual(after, tree)
        _, out = self.run_script("review")
        self.assertEqual(out, ["review delta: none", "next: nothing to polish"])

    def test_a_code_line_with_a_trailing_comment_is_code(self):
        self.mark()
        self.write("src/a.ts", "export const a = 1;\nexport const b = 3; // was 2\n")
        _, out = self.run_script("polish")
        self.assertIn("src/a.ts: -2, +2", out)

    def test_an_open_block_comment_does_not_hide_the_next_hunk(self):
        body = ["/**", " * doc", " */", "export const a = 1;"] + [f"export const x{i} = {i};" for i in range(8)] + ["export const b = 2;"]
        self.write("src/a.ts", "\n".join(body) + "\n")
        self.mark()
        changed = list(body)
        changed[0] = "/** reworded"  # a hunk that opens a block comment and leaves it open
        changed[-1] = "export const b = 5;"  # a later hunk with code
        self.write("src/a.ts", "\n".join(changed) + "\n")
        _, out = self.run_script("polish")
        self.assertIn(f"src/a.ts: -{len(body)}, +{len(body)}", out)

    def test_requirements_and_cmake_files_are_code(self):
        self.write("requirements-dev.txt", "pytest==7\n")
        self.write("CMakeLists.txt", "add_executable(a a.c)\n")
        self.write("notes.txt", "prose\n")
        self.mark()
        self.write("requirements-dev.txt", "pytest==8\n")
        self.write("CMakeLists.txt", "add_executable(a b.c)\n")
        self.write("notes.txt", "more prose\n")
        _, out = self.run_script("polish")
        self.assertIn("CMakeLists.txt: -1, +1", out)
        self.assertIn("requirements-dev.txt: -1, +1", out)
        self.assertFalse(any(line.startswith("notes.txt") for line in out), out)

    def test_a_line_that_only_starts_like_a_comment_is_code(self):
        cases = {
            "src/m.ts": ["  * b; // x", "/* a */ f(2);", "--i; // dec"],
            "src/m.c": ["#define X 1 // y", "*/ foo();"],
            "src/m.html": ["<!-- x --> <div>"],
            "src/m.css": ["* { color: red } /* x */"],
        }
        for path, code in cases.items():
            self.write(path, "\n".join(f"keep{i}();" for i in range(len(code))) + "\n")
        self.mark()
        for path, code in cases.items():
            self.write(path, "\n".join(code) + "\n")
        _, out = self.run_script("polish")
        for path, code in cases.items():
            self.assertIn(f"{path}: " + ", ".join([f"-{i + 1}" for i in range(len(code))] + [f"+{i + 1}" for i in range(len(code))]), out)

    def test_comments_in_each_language_are_not_code(self):
        cases = {"src/m.ts": ["// a", "/* b */", "/*", " * c", "*/"], "src/m.py": ["# a", '"""b"""'],
                 "src/m.sql": ["-- a"], "src/m.html": ["<!-- a -->"], "src/m.css": ["/*", " * a", " */"]}
        for path in cases:
            self.write(path, "")
        self.mark()
        for path, comments in cases.items():
            self.write(path, "\n".join(comments) + "\n")
        _, out = self.run_script("polish")
        self.assertTrue(out[-1].startswith("next: wait for the finder (code-review medium), then Step 3 of "), out)

    def test_a_binary_or_mode_change_is_code(self):
        self.write("img.bin", "a\0b")
        self.write("run.sh", "echo hi\n")
        self.mark()
        self.write("img.bin", "a\0c")
        (self.dir / "run.sh").chmod(0o755)
        _, out = self.run_script("polish")
        self.assertIn("img.bin: binary or mode change", out)
        self.assertIn("run.sh: binary or mode change", out)
        self.assertRegex(out[-1], r"^next: review the polish delta")

    def test_a_deleted_comment_line_alone_is_not_code(self):
        self.write("src/a.ts", "export const a = 1; \n/* note */\nexport const b = 2;\n")
        self.mark()
        self.write("src/a.ts", "export const a = 1; \nexport const b = 2;\n")
        _, out = self.run_script("polish")
        self.assertTrue(out[-1].startswith("next: wait for the finder (code-review medium), then Step 3 of "), out)


    def test_noprefix_does_not_cut_paths(self):
        self.git("config", "diff.noprefix", "true")
        self.write("b/a.ts", "export const a = 1;\n")
        self.mark()
        self.write("b/a.ts", "export const a = 2;\n")
        _, out = self.run_script("polish")
        self.assertIn("b/a.ts: -1, +1", out)

    def test_a_star_line_outside_a_known_block_is_code(self):
        self.write("src/a.ts", "export const z = 0\n  * height\n")
        self.mark()
        self.write("src/a.ts", "export const z = 0\n  * (height + pad)\n")
        _, out = self.run_script("polish")
        self.assertIn("src/a.ts: -2, +2", out)

    def test_a_string_built_from_a_triple_quoted_literal_is_code(self):
        self.write("q.py", "Q = 1\n'''SELECT a'''.format(x)\n")
        self.mark()
        self.write("q.py", "Q = 1\n'''SELECT b'''.format(x)\n")
        _, out = self.run_script("polish")
        self.assertIn("q.py: -2, +2", out)


class Review(Repo):
    def test_a_fix_without_a_comment(self):
        self.mark()
        self.write("src/a.ts", "export const a = 1;\nexport const b = a ?? 2;\n")
        _, out = self.run_script("review")
        self.assertEqual(out[0], "review delta: 1 file, no comment on an added line")
        self.assertEqual(out[-1], "next: nothing to polish")

    def test_a_fix_that_adds_a_comment_gets_the_comment_pass(self):
        self.write("src/a.ts", "// already here\nexport const a = 1;\nexport const b = 2;\n")
        self.mark()
        self.write("src/a.ts", "// already here\nexport const a = 1;\n// The first check counts nothing.\nexport const b = 2;\n")
        _, out = self.run_script("review")
        self.assertEqual(out[0], "src/a.ts: 3")
        self.assertIn("review delta: 1 file, 1 comment on added lines", out)
        self.assertRegex(out[-1], r"^next: comment pass on review's fixes — .*risk: low.*; read /.*/go/references/deltas\.md$")

    def test_review_without_a_mark_says_read_the_diff_yourself(self):
        code, out = self.run_script("review")
        self.assertEqual(code, 1)
        self.assertEqual(out[-1], "next: read the diff yourself — a comment a review fix added → comment pass on it; none → nothing to polish")

    def test_outside_a_repo_review_says_read_the_diff_yourself(self):
        with tempfile.TemporaryDirectory() as bare:
            code, out = self.run_script("review", cwd=bare)
        self.assertEqual(code, 1)
        self.assertTrue(out[-1].startswith("next: read the diff yourself — a comment a review fix added"), out)

    def test_no_fix(self):
        self.mark()
        _, out = self.run_script("review")
        self.assertEqual(out, ["review delta: none", "next: nothing to polish"])


if __name__ == "__main__":
    unittest.main()
