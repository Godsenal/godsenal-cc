import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("refs_watch", Path(__file__).with_name("refs-watch.py"))
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


class WatchTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "scripts/refs").mkdir(parents=True)
        self.upstream = {
            "a/one": ("s1", [("SKILL.md", "blob", "b0"), ("skills/x/SKILL.md", "blob", "bx"),
                             ("skills/x/notes.md", "blob", "bn"), ("skills/y", "tree", "ty"),
                             ("skills/y/SKILL.md", "blob", "by"), ("docs/NOT_SKILL.md", "blob", "bd")]),
            "b/two": ("t1", [("z/SKILL.md", "blob", "bz")]),
        }
        self.truncated = set()
        self.calls = []
        orig = watch.api
        watch.api = self.fake_api
        self.addCleanup(setattr, watch, "api", orig)
        self.write_lock({"a/one": {"ref": "main"}, "b/two": {"ref": "dev"}})

    def fake_api(self, path):
        self.calls.append(path)
        repo = "/".join(path.split("/")[1:3])
        sha, entries = self.upstream[repo]
        if "/commits/" in path:
            return {"sha": sha}
        if path.endswith(f"/git/trees/{sha}?recursive=1"):
            return {"truncated": repo in self.truncated,
                    "tree": [{"path": p, "type": t, "sha": s} for p, t, s in entries]}
        raise watch.WatchError(f"unexpected {path}")

    def write_lock(self, repos):
        (self.root / watch.LOCK).write_text(json.dumps({"repos": repos}))

    def lock(self):
        return json.loads((self.root / watch.LOCK).read_text())

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = watch.main([*args, "--root", str(self.root)])
        return code, json.loads(out.getvalue())

    def test_update_records_head_and_only_skill_files(self):
        code, report = self.run_main("--update")
        self.assertEqual(code, 0)
        self.assertEqual(report["a/one"], {"sha": "s1", "skills": 3, "was": None})
        entry = self.lock()["repos"]["a/one"]
        self.assertEqual(entry["sha"], "s1")
        self.assertEqual(entry["ref"], "main")
        self.assertEqual(entry["skills"], {"SKILL.md": "b0", "skills/x/SKILL.md": "bx", "skills/y/SKILL.md": "by"})
        self.assertIn("repos/b/two/commits/dev", self.calls)

    def test_check_after_update_reports_nothing(self):
        self.run_main("--update")
        code, report = self.run_main("--check")
        self.assertEqual(code, 0)
        for repo, sha in (("a/one", "s1"), ("b/two", "t1")):
            self.assertEqual(report[repo], {"changed": False, "sha": sha, "locked_sha": sha,
                                            "new_skills": [], "removed_skills": [], "changed_skills": []})

    def test_changed_locked_sha_marks_only_that_repo(self):
        self.run_main("--update")
        lock = self.lock()
        lock["repos"]["a/one"]["sha"] = "old"
        self.write_lock(lock["repos"])
        _, report = self.run_main("--check")
        self.assertTrue(report["a/one"]["changed"])
        self.assertEqual(report["a/one"]["locked_sha"], "old")
        self.assertEqual(report["a/one"]["sha"], "s1")
        self.assertFalse(report["b/two"]["changed"])

    def test_skill_added_removed_and_edited(self):
        self.run_main("--update")
        self.upstream["a/one"] = ("s2", [("SKILL.md", "blob", "b0"), ("skills/x/SKILL.md", "blob", "bx2"),
                                         ("skills/w/SKILL.md", "blob", "bw")])
        _, report = self.run_main("--check")
        self.assertEqual(report["a/one"], {"changed": True, "sha": "s2", "locked_sha": "s1",
                                           "new_skills": ["skills/w/SKILL.md"],
                                           "removed_skills": ["skills/y/SKILL.md"],
                                           "changed_skills": ["skills/x/SKILL.md"]})

    def test_check_does_not_write_the_lock(self):
        self.run_main("--update")
        before = (self.root / watch.LOCK).read_text()
        self.upstream["b/two"] = ("t2", [])
        self.run_main("--check")
        self.assertEqual((self.root / watch.LOCK).read_text(), before)

    def test_truncated_tree_is_an_error_not_a_short_list(self):
        self.truncated.add("b/two")
        code, report = self.run_main("--update")
        self.assertEqual(code, 1)
        self.assertIn("truncated", report["error"])
        self.assertNotIn("sha", self.lock()["repos"]["a/one"])

    def test_fetch_failure_prints_error(self):
        def down(path):
            raise watch.WatchError(f"{path}: offline")
        watch.api = down
        code, report = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn("offline", report["error"])

    def test_missing_lock_prints_error(self):
        (self.root / watch.LOCK).unlink()
        code, report = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn("error", report)

    def test_repo_lock_lists_the_four_references(self):
        lock = watch.load_lock(Path(__file__).resolve().parent.parent)
        self.assertLessEqual({"addyosmani/agent-skills", "anthropics/skills", "mattpocock/skills", "obra/superpowers"},
                             set(lock["repos"]))
        for repo, entry in lock["repos"].items():
            self.assertTrue(entry.get("sha") and entry.get("skills"), f"{repo}: run scripts/refs-watch.py --update")


class ApiTest(unittest.TestCase):
    def patch(self, run=None, urlopen=None):
        for mod, name, fn in ((watch.subprocess, "run", run), (watch.urllib.request, "urlopen", urlopen)):
            orig = getattr(mod, name)
            setattr(mod, name, fn)
            self.addCleanup(setattr, mod, name, orig)

    def test_gh_reply_is_used(self):
        def run(cmd, **kw):
            self.assertEqual(cmd, ["gh", "api", "repos/a/b"])
            self.assertNotIn("GITHUB_TOKEN", kw["env"])
            return watch.subprocess.CompletedProcess(cmd, 0, b'{"sha": "g"}', b"")
        def urlopen(*a, **kw):
            raise AssertionError("no https call when gh works")
        self.patch(run, urlopen)
        self.assertEqual(watch.api("repos/a/b"), {"sha": "g"})

    def test_gh_failure_falls_back_to_https(self):
        seen = []
        def urlopen(url, timeout):
            seen.append(url)
            return io.BytesIO(b'{"sha": "h"}')
        self.patch(lambda cmd, **kw: watch.subprocess.CompletedProcess(cmd, 1, b"", b"not logged in"), urlopen)
        self.assertEqual(watch.api("repos/a/b"), {"sha": "h"})
        self.assertEqual(seen, ["https://api.github.com/repos/a/b"])

    def test_both_failing_names_both(self):
        def run(cmd, **kw):
            raise FileNotFoundError("gh")
        def urlopen(url, timeout):
            raise OSError("no network")
        self.patch(run, urlopen)
        with self.assertRaises(watch.WatchError) as e:
            watch.api("repos/a/b")
        self.assertIn("gh", str(e.exception))
        self.assertIn("no network", str(e.exception))


if __name__ == "__main__":
    unittest.main()
