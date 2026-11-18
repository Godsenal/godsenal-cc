"""polish's added-comments: what counts as a comment on an added line, and the `next:` line that follows."""
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "plugins/base/skills/polish/scripts/added-comments"
loader = importlib.machinery.SourceFileLoader("added_comments", str(PATH))
spec = importlib.util.spec_from_loader("added_comments", loader)
ac = importlib.util.module_from_spec(spec)
loader.exec_module(ac)


def diff(path, *lines, start=1):
    """A unified diff that adds `lines` to `path`; a line given as ('-', text) or (' ', text) is removed or context."""
    rows = [f"+{line}" if isinstance(line, str) else f"{line[0]}{line[1]}" for line in lines]
    return "\n".join([f"diff --git a/{path} b/{path}", f"--- a/{path}", f"+++ b/{path}",
                      f"@@ -{start},{sum(1 for l in lines if not isinstance(l, str))} +{start},{sum(1 for l in lines if isinstance(l, str) or l[0] == ' ')} @@", *rows]) + "\n"


def lines_of(path, *lines):
    return ac.scan(diff(path, *lines)).get(path, [])


class Markers(unittest.TestCase):
    def test_line_comment_in_a_c_style_file(self):
        self.assertEqual(lines_of("src/a.ts", "const a = 1;", "// explains a", "const b = 2;"), [2])

    def test_trailing_comment_counts(self):
        self.assertEqual(lines_of("src/a.ts", "const a = 1; // why"), [1])

    def test_marker_inside_a_string_does_not_count(self):
        self.assertEqual(lines_of("src/a.ts", "const u = 'https://example.com/a';", 'const s = "a // b";', "const t = `# x`;"), [])

    def test_url_outside_a_string_does_not_count(self):
        self.assertEqual(lines_of("src/a.tsx", "<a href=https://example.com>x</a>"), [])

    def test_block_comment_runs_until_it_closes(self):
        self.assertEqual(lines_of("src/a.ts", "/**", " * doc", " */", "export const a = 1;"), [1, 2, 3])

    def test_block_continuation_whose_opening_is_above_the_hunk(self):
        self.assertEqual(lines_of("src/a.c", " * added to an old block", "*p = 1;"), [1])

    def test_one_line_block_comment_does_not_swallow_the_next_line(self):
        self.assertEqual(lines_of("src/a.css", "a { color: red; } /* brand */", "b { color: blue; }"), [1])

    def test_suppression_directive_counts(self):
        self.assertEqual(lines_of("src/a.ts", "// eslint-disable-next-line no-explicit-any", "// @ts-ignore"), [1, 2])

    def test_hash_comment_and_shebang(self):
        self.assertEqual(lines_of("run.sh", "#!/bin/sh", "set -e  # stop on error", 'echo "$#" "${x#a}"'), [2])

    def test_python_docstring_and_hash(self):
        self.assertEqual(lines_of("a.py", "def f():", '    """Does f."""', "    return 1  # noqa", 'x = "# not one"'), [2, 3])

    def test_hash_is_not_a_comment_in_a_c_style_file(self):
        self.assertEqual(lines_of("src/a.ts", "class A { #secret = 1 }"), [])

    def test_sql_dash_and_html_comment(self):
        self.assertEqual(lines_of("q.sql", "select a - -1 from t;", "-- drop later", "select 1; /* x */"), [2, 3])
        self.assertEqual(lines_of("index.html", "<p>a</p>", "<!-- note -->"), [2])

    def test_dash_comment_needs_no_space_after_it(self):
        self.assertEqual(lines_of("q.lua", "--TODO", "--[[ block ]]", "x = 1 --note", "y = a-- b"), [1, 2, 3])

    def test_apostrophe_in_a_word_does_not_open_a_string(self):
        self.assertEqual(lines_of("c.yml", "desc: Don't do it  # because it's bad", "name: 'a # b'"), [1])
        self.assertEqual(lines_of("run.sh", "echo it's # comment's"), [1])

    def test_prefixed_python_string_is_still_a_string(self):
        self.assertEqual(lines_of("a.py", "x = f'# {y}'", "z = rb'# raw'", "w = self.f('# arg')"), [])

    def test_hash_files_with_a_txt_name(self):
        self.assertEqual(lines_of("CMakeLists.txt", "project(a)", "# toolchain"), [2])
        self.assertEqual(lines_of("requirements-dev.txt", "pytest==8.0  # pinned"), [1])
        self.assertEqual(lines_of("notes.txt", "# heading"), [])

    def test_html_inline_script_comment(self):
        self.assertEqual(lines_of("index.html", "<script>", "  // init", "  /* later */", '<a href="https://example.com">x</a>'), [2, 3])

    def test_yaml_and_dockerfile(self):
        self.assertEqual(lines_of("ci.yml", "name: ci", "# cache key", "run: echo a#b"), [2])
        self.assertEqual(lines_of("Dockerfile", "FROM node:22", "# slim later"), [2])

    def test_prose_and_data_files_are_never_counted(self):
        for path in ("README.md", "docs/a.mdx", "package.json", "bun.lock"):
            self.assertEqual(lines_of(path, "# Heading", "<!-- marker -->", "// x"), [], path)

    def test_unknown_extension_counts_only_a_marker_that_starts_the_line(self):
        self.assertEqual(lines_of("view.erb", "<p>a // b</p>", "# note", "<!-- x -->", "#!shebang"), [2, 3])


class DiffSides(unittest.TestCase):
    def test_removed_and_context_lines_are_not_counted(self):
        text = diff("src/a.ts", ("-", "// removed comment"), (" ", "// old comment"), "const a = 1;")
        self.assertEqual(ac.scan(text), {})

    def test_line_numbers_are_the_new_side(self):
        text = diff("src/a.ts", "const a = 1;", (" ", "const old = 0;"), "// new", start=40)
        self.assertEqual(ac.scan(text), {"src/a.ts": [42]})

    def test_deleted_file_is_skipped(self):
        text = "diff --git a/x.ts b/x.ts\n--- a/x.ts\n+++ /dev/null\n@@ -1,1 +0,0 @@\n-// gone\n"
        self.assertEqual(ac.scan(text), {})

    def test_added_line_that_looks_like_a_file_header_is_content(self):
        self.assertEqual(lines_of("a.c", "int i;", "++ i;", "// after"), [3])
        text = diff("q.sql", ("-", "-- old note"), "select 1;", "-- new note")
        self.assertEqual(ac.scan(text), {"q.sql": [2]})

    def test_block_opener_inside_a_line_comment_opens_nothing(self):
        self.assertEqual(lines_of("a.ts", "// see /* x", "const a = 1;", "const b = 2;"), [1])

    def test_hunk_without_counts_and_no_newline_marker(self):
        text = "diff --git a/a.ts b/a.ts\n--- a/a.ts\n+++ b/a.ts\n@@ -3 +3 @@\n-const a = 1;\n+const a = 1; // why\n\\ No newline at end of file\n"
        self.assertEqual(ac.scan(text), {"a.ts": [3]})

    def test_two_files(self):
        text = diff("a.ts", "// one") + diff("b.py", "x = 1", "# two")
        self.assertEqual(ac.scan(text), {"a.ts": [1], "b.py": [2]})


class Report(unittest.TestCase):
    def test_comments_send_the_pass_to_its_reference(self):
        out = ac.report({"b.py": [2], "a.ts": [1, 4]}).splitlines()
        self.assertEqual(out, ["a.ts: 1, 4", "b.py: 2", "comments: 3 on added lines, in 2 files",
                               "next: comment pass — read references/comments.md"])

    def test_one_file_is_singular(self):
        self.assertIn("comments: 1 on added lines, in 1 file", ac.report({"a.ts": [1]}).splitlines())

    def test_no_comment_skips_the_pass(self):
        self.assertEqual(ac.report({}).splitlines(), ["comments: 0 on added lines",
                                                      "next: skip — report `Comments: skip — no comments on added lines`"])


class OnARepo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        (self.repo / "a.ts").write_text("export const a = 1;\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=self.repo, check=True, capture_output=True)

    def run_script(self, *args, stdin=None, cwd=None, path=None):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        if path is not None:
            env["PATH"] = path
        return subprocess.run([sys.executable, str(PATH), *args], cwd=cwd or self.repo, capture_output=True, text=True, input=stdin, env=env)

    def test_uncommitted_edit_and_untracked_file(self):
        (self.repo / "a.ts").write_text("export const a = 1;\n// tracked edit\n")
        (self.repo / "b.py").write_text("x = 1\n# untracked\n")
        (self.repo / "notes.md").write_text("# not counted\n")
        out = self.run_script().stdout.splitlines()
        self.assertEqual(out[:3], ["a.ts: 2", "b.py: 2", "comments: 2 on added lines, in 2 files"])
        self.assertTrue(out[3].startswith("next: comment pass"))

    def test_clean_diff_without_comments_skips(self):
        (self.repo / "a.ts").write_text("export const a = 2;\n")
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines()[0], "comments: 0 on added lines")
        self.assertTrue(result.stdout.splitlines()[1].startswith("next: skip"))

    def test_commit_range(self):
        (self.repo / "a.ts").write_text("export const a = 1;\nconst b = 2; // committed\n")
        self.git("commit", "-qam", "second")
        self.assertEqual(self.run_script("HEAD~1", "HEAD").stdout.splitlines()[0], "a.ts: 2")
        self.assertEqual(self.run_script().stdout.splitlines()[0], "comments: 0 on added lines")

    def test_paths_only_is_the_working_tree_against_head_with_untracked_files(self):
        (self.repo / "a.ts").write_text("export const a = 1;\n// staged\n")
        self.git("add", "a.ts")
        (self.repo / "new.ts").write_text("// untracked\n")
        (self.repo / "other.ts").write_text("// out of scope\n")
        out = self.run_script("--", "a.ts", "new.ts").stdout.splitlines()
        self.assertEqual(out[:3], ["a.ts: 2", "new.ts: 1", "comments: 2 on added lines, in 2 files"])

    def test_revision_with_paths_reads_no_untracked_file(self):
        (self.repo / "new.ts").write_text("// untracked\n")
        self.assertEqual(self.run_script("HEAD", "--", "new.ts").stdout.splitlines()[0], "comments: 0 on added lines")

    def test_from_a_subdirectory_the_whole_repo_is_read_with_root_relative_paths(self):
        (self.repo / "sub").mkdir()
        (self.repo / "sub" / "s.py").write_text("# in sub\n")
        (self.repo / "root.py").write_text("# at root\n")
        (self.repo / "a.ts").write_text("export const a = 1; // edit\n")
        out = self.run_script(cwd=self.repo / "sub").stdout.splitlines()
        self.assertEqual(out[:3], ["a.ts: 1", "root.py: 1", "sub/s.py: 1"])
        out = self.run_script("--", "s.py", cwd=self.repo / "sub").stdout.splitlines()
        self.assertEqual(out[:2], ["sub/s.py: 1", "comments: 1 on added lines, in 1 file"])

    def test_no_git_hands_the_decision_to_the_reader(self):
        result = self.run_script(path=str(self.repo / "no-bin"))
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stdout.startswith("next: read the diff yourself"))
        self.assertNotIn("Traceback", result.stderr)

    def test_diff_on_stdin(self):
        out = self.run_script("-", stdin=diff("a.ts", "// piped")).stdout.splitlines()
        self.assertEqual(out[0], "a.ts: 1")

    def test_unreadable_diff_hands_the_decision_to_the_reader(self):
        result = self.run_script("no-such-rev")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stdout.startswith("next: read the diff yourself"))
        self.assertNotIn("next: skip", result.stdout)


if __name__ == "__main__":
    unittest.main()
