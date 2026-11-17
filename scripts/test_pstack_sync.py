"""pstack-sync against a fake upstream checkout — no network."""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("pstack_sync", Path(__file__).with_name("pstack-sync.py"))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

TREE = "harness/pstack/claude-code"
ADAPTER_LINE = ("In Claude Code, read [the Claude Code adapter](../../docs/harness/claude-code.md) once per session "
                "before you follow this skill. It maps the Cursor names in pstack skills to Claude Code.\n\n")


def skill(name, body, extra=""):
    return f'---\nname: {name}\ndescription: "does {name}"\n{extra}---\n\n# {name.title()}\n\n{ADAPTER_LINE}{body}\n'


class SyncTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.up = Path(tmp.name) / "upstream"
        self.root = Path(tmp.name) / "repo"
        self.write_up({
            f"{TREE}/skills/alpha/SKILL.md": skill(
                "alpha", "Run the **how** skill, then [beta](../beta/SKILL.md), [setup](../gone/SKILL.md), "
                "[verify](../make-verify/SKILL.md), and [big](scripts/test/big.out).", "disable-model-invocation: true\n"),
            f"{TREE}/skills/alpha/scripts/run.sh": "#!/bin/sh\necho one\n",
            f"{TREE}/skills/alpha/scripts/test/big.out": "corpus\n",
            f"{TREE}/skills/beta/SKILL.md": skill("beta", "No flag upstream."),
            f"{TREE}/skills/how/SKILL.md": skill("how", "Upstream how, v1."),
            f"{TREE}/skills/make-verify/SKILL.md": skill("make-verify", "Upstream generator."),
            f"{TREE}/skills/gone/SKILL.md": skill("gone", "Never imported."),
            f"{TREE}/agents/helper.md": "---\nname: helper\ndescription: helps\nis_background: true\nmodel: claude-opus-5-5-xhigh-fast\n---\n\n# Helper\n\nBody.\n",
            f"{TREE}/docs/harness/claude-code.md": "# adapter v1\n",
            f"{TREE}/LICENSE": "MIT License\n",
            f"{TREE}/plugin.json": '{"name": "pstack", "version": "0.1.0"}\n',
            "pstack/automations/benny/FOR_AGENTS.md": "cursor only\n",
        })
        os.chmod(self.up / TREE / "skills/alpha/scripts/run.sh", 0o755)
        for rel in ("plugins/base/skills/how/SKILL.md", "plugins/base/skills/create-verify/SKILL.md",
                    "plugins/base/references/pstack-adapter.md"):
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("gbase's own\n")
        (self.root / "scripts/pstack").mkdir(parents=True)
        self.save_lock({
            "schema": 1,
            "upstream": {"repo": "cursor/plugins", "ref": "main", "tree": TREE},
            "exclude": [{"path": "skills/alpha/scripts/test/", "reason": "corpus"}],
            "items": {
                "alpha": {"mode": "follow"}, "beta": {"mode": "follow"},
                "how": {"mode": "merge", "into": "skills/how"},
                "make-verify": {"mode": "merge", "into": "skills/create-verify"},
                "gone": {"mode": "skip", "reason": "writes outside the repo"},
                "agents/helper": {"mode": "follow"},
                "docs/harness": {"mode": "merge", "into": "references/pstack-adapter.md"},
                "root/LICENSE": {"mode": "follow"},
                "root/plugin.json": {"mode": "skip", "reason": "manifest"},
                "automations/benny": {"mode": "unusable", "reason": "Cursor Automations"},
            },
        })

    def write_up(self, files):
        for rel, text in files.items():
            p = self.up / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)

    def save_lock(self, lock):
        (self.root / sync.LOCK).write_text(json.dumps(lock))

    def lock(self):
        return json.loads((self.root / sync.LOCK).read_text())

    def run_sync(self, mode, sha="aaa111", source=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sync.main([mode, "--source", str(source or self.up), "--sha", sha, "--root", str(self.root)])
        return code, json.loads(out.getvalue())

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): (p.read_bytes(), os.access(p, os.X_OK))
                for p in sorted(self.root.rglob("*")) if p.is_file()}

    def read(self, rel):
        return (self.root / "plugins/base" / rel).read_text()

    def test_first_apply_generates_followed_items_and_leaves_merged_ones(self):
        code, report = self.run_sync("--apply")
        self.assertEqual(code, 0)
        self.assertEqual(report["applied"], ["agents/helper", "alpha", "beta", "root/LICENSE"])
        self.assertEqual(report["scripts_new"], ["plugins/base/skills/alpha/scripts/run.sh"])
        self.assertEqual(report["pending"], [])
        alpha = self.read("skills/alpha/SKILL.md")
        self.assertIn("## 출력 언어", alpha)
        self.assertIn("](../../references/pstack-adapter.md)", alpha)
        self.assertNotIn("docs/harness/claude-code.md", alpha)
        self.assertLess(alpha.index("# Alpha"), alpha.index("## 출력 언어"))
        self.assertIn("[beta](../beta/SKILL.md)", alpha)  # followed: link kept
        self.assertIn("[setup](https://github.com/cursor/plugins/blob/main/pstack/skills/gone/SKILL.md)", alpha)  # skipped
        self.assertIn("[verify](../create-verify/SKILL.md)", alpha)  # merged under another name
        self.assertIn("[big](https://github.com/cursor/plugins/blob/main/pstack/skills/alpha/scripts/test/big.out)", alpha)  # excluded
        self.assertFalse((self.root / "plugins/base/skills/alpha/scripts/test").exists())
        self.assertTrue(os.access(self.root / "plugins/base/skills/alpha/scripts/run.sh", os.X_OK))
        self.assertIn("disable-model-invocation: true", self.read("skills/beta/SKILL.md"))  # added when upstream lacks it
        helper = self.read("agents/helper.md")
        self.assertNotIn("model:", helper)
        self.assertNotIn("is_background", helper)
        self.assertEqual(self.read("references/pstack-LICENSE"), "MIT License\n")
        self.assertEqual(self.read("skills/how/SKILL.md"), "gbase's own\n")
        self.assertFalse((self.root / "plugins/base/skills/gone").exists())
        self.assertEqual(self.lock()["upstream"]["sha"], "aaa111")
        self.assertEqual(self.lock()["upstream"]["version"], "0.1.0")
        self.assertEqual(sync.verify(self.root), [])

    def test_apply_twice_changes_nothing(self):
        self.run_sync("--apply")
        before = self.snapshot()
        code, report = self.run_sync("--apply")
        self.assertEqual((code, report["applied"], report["pending"], report["scripts_new"]), (0, [], [], []))
        self.assertEqual(self.snapshot(), before)
        code, report = self.run_sync("--check")
        self.assertEqual((code, report["changed"]), (0, False))

    def test_check_reports_each_kind_of_change(self):
        self.run_sync("--apply")
        self.write_up({
            f"{TREE}/skills/alpha/scripts/run.sh": "#!/bin/sh\necho two\n",
            f"{TREE}/skills/how/SKILL.md": skill("how", "Upstream how, v2."),
            f"{TREE}/skills/gone/SKILL.md": skill("gone", "Changed, still skipped."),
            f"{TREE}/skills/fresh/SKILL.md": skill("fresh", "New."),
        })
        (self.up / TREE / "skills/beta/SKILL.md").unlink()
        code, report = self.run_sync("--check", sha="bbb222")
        self.assertEqual(code, 0)
        self.assertEqual(report, {
            "upstream_sha": "bbb222", "locked_sha": "aaa111", "changed": True,
            "skills_changed": ["alpha"], "custom_changed": ["how"],
            "new_upstream": ["fresh"], "removed_upstream": ["beta"],
        })

    def test_apply_update_writes_merge_diff_and_lists_changed_scripts(self):
        self.run_sync("--apply")
        self.write_up({
            f"{TREE}/skills/alpha/scripts/run.sh": "#!/bin/sh\necho two\n",
            f"{TREE}/skills/alpha/scripts/new.py": "print(1)\n",
            f"{TREE}/skills/how/SKILL.md": skill("how", "Upstream how, v2."),
            f"{TREE}/skills/fresh/SKILL.md": skill("fresh", "New."),
        })
        (self.up / TREE / "skills/beta/SKILL.md").unlink()
        code, report = self.run_sync("--apply", sha="bbb222")
        self.assertEqual(code, 0)
        self.assertEqual(report["applied"], ["alpha"])
        self.assertEqual(report["scripts_changed"], ["plugins/base/skills/alpha/scripts/run.sh"])
        self.assertEqual(report["scripts_new"], ["plugins/base/skills/alpha/scripts/new.py"])
        self.assertEqual(report["removed"], ["beta"])
        self.assertEqual(report["new_upstream"], ["fresh"])
        self.assertEqual(report["pending"], ["scripts/pstack/pending/how.diff"])
        diff = (self.root / "scripts/pstack/pending/how.diff").read_text()
        self.assertIn("-Upstream how, v1.", diff)
        self.assertIn("+Upstream how, v2.", diff)
        self.assertIn("plugins/base/skills/how", diff.splitlines()[0])
        self.assertEqual(self.read("skills/how/SKILL.md"), "gbase's own\n")  # the merge is the agent's job
        self.assertFalse((self.root / "plugins/base/skills/beta").exists())
        self.assertFalse((self.root / "plugins/base/skills/fresh").exists())  # a new item waits for a mode
        self.assertNotIn("beta", self.lock()["items"])
        self.assertTrue(any("pending/how.diff" in p for p in sync.verify(self.root)))
        before = self.snapshot()
        code, report = self.run_sync("--apply", sha="bbb222")
        self.assertEqual((report["applied"], report["pending"]), ([], []))
        self.assertEqual(self.snapshot(), before)

    def test_verify_catches_a_hand_edit(self):
        self.run_sync("--apply")
        with (self.root / "plugins/base/skills/alpha/SKILL.md").open("a") as f:
            f.write("edited\n")
        problems = sync.verify(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("skills/alpha", problems[0])

    def test_unreachable_source_is_an_error_line_and_changes_nothing(self):
        before = self.snapshot()
        for mode in ("--check", "--apply"):
            code, report = self.run_sync(mode, source=self.up / "missing")
            self.assertEqual(code, 1)
            self.assertIn("error", report)
        self.assertEqual(self.snapshot(), before)

    def set_mode(self, name, entry):
        lock = self.lock()
        lock["items"][name] = entry
        self.save_lock(lock)

    def test_followed_item_turned_skip_loses_its_generated_copy(self):
        self.run_sync("--apply")
        self.set_mode("alpha", {**self.lock()["items"]["alpha"], "mode": "skip", "reason": "now runs a remote script"})
        self.assertTrue(any("alpha" in p for p in sync.verify(self.root)))  # check.py fails until --apply ran
        code, report = self.run_sync("--apply")
        self.assertEqual((code, report["removed"]), (0, ["alpha"]))
        self.assertFalse((self.root / "plugins/base/skills/alpha").exists())
        self.assertEqual(sync.verify(self.root), [])

    def test_follow_refuses_a_folder_it_did_not_generate(self):
        self.run_sync("--apply")
        self.write_up({f"{TREE}/skills/create-verify/SKILL.md": skill("create-verify", "Upstream's own.")})
        self.set_mode("create-verify", {"mode": "follow"})
        before = self.snapshot()
        code, report = self.run_sync("--apply", sha="bbb222")
        self.assertEqual(code, 1)
        self.assertIn("not a generated copy", report["error"])
        self.assertEqual(self.snapshot(), before)

    def test_failure_while_generating_writes_nothing(self):
        self.run_sync("--apply")
        self.write_up({
            f"{TREE}/skills/alpha/scripts/run.sh": "#!/bin/sh\necho two\n",
            f"{TREE}/skills/beta/SKILL.md": "no frontmatter\n",
        })
        before = self.snapshot()
        code, report = self.run_sync("--apply", sha="bbb222")
        self.assertEqual(code, 1)
        self.assertIn("beta", report["error"])
        self.assertEqual(self.snapshot(), before)
        (self.up / TREE / "skills/beta/SKILL.md").write_bytes(b"---\nname: beta\n---\n\xff\xfe")
        code, report = self.run_sync("--apply", sha="bbb222")
        self.assertEqual(code, 1)
        self.assertIn("not UTF-8", report["error"])

    def test_exec_bit_only_change_to_a_merged_item_leaves_no_diff(self):
        self.run_sync("--apply")
        os.chmod(self.up / TREE / "skills/how/SKILL.md", 0o755)
        code, report = self.run_sync("--apply", sha="bbb222")
        self.assertEqual((code, report["pending"]), (0, []))
        self.assertEqual(sync.verify(self.root), [])
        self.assertFalse(self.run_sync("--check", sha="bbb222")[1]["changed"])

    def test_links_in_code_stay_and_excluded_images_use_raw_urls(self):
        self.write_up({f"{TREE}/skills/beta/SKILL.md": skill(
            "beta", "![shot](scripts/shot.png) and `a[b](c)` stay.\n\n```ts\n# not a title\nconst r = handlers[name](event);\n```")})
        lock = self.lock()
        lock["exclude"].append({"path": "skills/beta/scripts/", "reason": "images"})
        self.save_lock(lock)
        self.run_sync("--apply")
        beta = self.read("skills/beta/SKILL.md")
        self.assertIn("![shot](https://raw.githubusercontent.com/cursor/plugins/main/pstack/skills/beta/scripts/shot.png)", beta)
        self.assertIn("`a[b](c)`", beta)
        self.assertIn("handlers[name](event);", beta)

    def test_block_goes_first_when_the_only_hash_line_is_in_a_fence(self):
        body = "Intro.\n\n```sh\n# install\n```\n"
        out = sync.insert_after_title(body, "BLOCK\n")
        self.assertTrue(out.startswith("BLOCK\nIntro."))
        self.assertEqual(sync.insert_after_title("# T\n\nx\n", "B\n"), "# T\n\nB\nx\n")

    def test_stray_runtime_files_do_not_fail_verify(self):
        self.run_sync("--apply")
        (self.root / "plugins/base/skills/alpha/.DS_Store").write_text("x")
        (self.root / "plugins/base/skills/alpha/scripts/node_modules").mkdir()
        (self.root / "plugins/base/skills/alpha/scripts/node_modules/x.js").write_text("x")
        self.assertEqual(sync.verify(self.root), [])

    def test_network_failure_is_an_error_line(self):
        def down(*a, **k):
            raise sync.SyncError("gh api: could not resolve host")

        def no_https(*a, **k):
            raise OSError("no route")

        real = sync.gh, sync.urllib.request.urlopen
        sync.gh, sync.urllib.request.urlopen = down, no_https
        self.addCleanup(lambda: (setattr(sync, "gh", real[0]), setattr(sync.urllib.request, "urlopen", real[1])))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sync.main(["--check", "--root", str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn("could not resolve host", json.loads(out.getvalue())["error"])


if __name__ == "__main__":
    unittest.main()
