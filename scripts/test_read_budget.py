"""read-budget: route sums, the limit check, and what a run log says the main session loaded."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("read_budget", Path(__file__).with_name("read-budget.py"))
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)


class Budget(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.old_root, rb.ROOT = rb.ROOT, self.root
        self.addCleanup(lambda: setattr(rb, "ROOT", self.old_root))
        for name, text in {"a.md": "가" * 100, "b.md": "b" * 50, "c.md": "c" * 30}.items():
            (self.root / name).write_text(text, encoding="utf-8")

    def budget(self, low_limit=150, medium_limit=180, extra_limit=None):
        return {"routes": {"low": {"target": 100, "limit": low_limit, "reads": ["a.md", "b.md"]},
                           "medium": {"target": 120, "limit": medium_limit, "extends": "low", "reads": ["c.md", "a.md"]},
                           "high": {"target": None, "limit": None, "extends": "medium", "reads": []}},
                "extras": {"headless": {"limit": extra_limit, "reads": ["c.md"]}}}

    def test_counts_characters_not_bytes_and_inherits_without_double_counting(self):
        m = rb.measure(self.budget())
        self.assertEqual((m["low"]["total"], m["medium"]["total"], m["high"]["total"], m["+headless"]["total"]), (150, 180, 180, 30))

    def test_at_the_limit_passes_one_over_fails(self):
        self.assertEqual(rb.problems(self.budget()), [])
        (self.root / "b.md").write_text("b" * 51)
        found = rb.problems(self.budget())
        self.assertEqual(len(found), 2)
        self.assertIn("route low loads 151 characters into the main session, over its limit of 150", found[0])

    def test_a_route_without_a_limit_is_only_measured(self):
        (self.root / "c.md").write_text("c" * 9999)
        self.assertEqual([p for p in rb.problems(self.budget(medium_limit=99999)) if "high" in p or "headless" in p], [])
        self.assertTrue(any("+headless" in p for p in rb.problems(self.budget(medium_limit=99999, extra_limit=10))))

    def test_a_listed_file_that_is_gone_fails(self):
        (self.root / "b.md").unlink()
        self.assertTrue(any("lists b.md, which doesn't exist" in p for p in rb.problems(self.budget())))

    def test_a_limit_below_the_target_is_a_mistake(self):
        self.assertTrue(any("limit 90 is below its target 100" in p for p in rb.problems(self.budget(low_limit=90))))

    def test_session_start_counts_listed_names_and_descriptions_not_bodies_or_hidden_skills(self):
        def write(rel, fm, body="x" * 500):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")
        write("p/skills/go/SKILL.md", 'name: go\ndescription: "Ships it."')
        write("p/skills/leaf/SKILL.md", "name: leaf\ndescription: Hidden.\ndisable-model-invocation: true")
        write("p/agents/scout.md", "name: scout\ndescription: >-\n  Reads\n  files.")
        (self.root / "p/.claude-plugin").mkdir()
        (self.root / "p/.claude-plugin/plugin.json").write_text('{"name": "g"}')
        budget = {"routes": {}, "extras": {"session-start": {"limit": 30, "reads": ["c.md"],
                                                            "listing": ["p/skills/*/SKILL.md", "p/agents/*.md"]}}}
        m = rb.measure(budget)["+session-start"]
        self.assertEqual(m["files"], [("c.md", 30), ("p/agents/scout.md (description)", 19), ("p/skills/go/SKILL.md (description)", 13)])
        self.assertEqual(m["total"], 62)
        self.assertTrue(any("route +session-start loads 62 characters" in p for p in rb.problems(budget)))

    def test_the_repo_budget_holds(self):
        rb.ROOT = self.old_root
        self.assertEqual(rb.problems(), [])


class Log(unittest.TestCase):
    def test_main_session_skills_and_plugin_reads_are_counted_subagents_are_not(self):
        def assistant(block, parent=None):
            return {"type": "assistant", "parent_tool_use_id": parent, "message": {"content": [block]}}

        def user(block, parent=None):
            return {"type": "user", "parent_tool_use_id": parent, "message": {"content": [block]}}

        events = [
            user({"type": "text", "text": "Base directory for this skill: /p/plugins/base/skills/work\n\n" + "w" * 100}),
            assistant({"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": "gbase:go"}}),
            user({"type": "tool_result", "tool_use_id": "t1", "content": "Launching skill: gbase:go"}),
            user({"type": "text", "text": "Base directory for this skill: /p/plugins/base/skills/go\n\n" + "g" * 200}),
            assistant({"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "/p/plugins/base/skills/monitor/references/settle.md"}}),
            user({"type": "tool_result", "tool_use_id": "t2", "content": [{"type": "text", "text": "s" * 40}]}),
            assistant({"type": "tool_use", "id": "t3", "name": "Read", "input": {"file_path": "/repo/src/app.ts"}}),
            user({"type": "tool_result", "tool_use_id": "t3", "content": "x" * 999}),
            assistant({"type": "tool_use", "id": "t4", "name": "Skill", "input": {"skill": "gbase:polish"}}, parent="agent1"),
            user({"type": "text", "text": "Base directory for this skill: /p/plugins/base/skills/polish\n\n" + "p" * 300}, parent="agent1"),
        ]
        events.append(assistant({"type": "tool_use", "id": "t5", "name": "Bash", "input": {
            "command": "R=/p/plugins/base/references; cat $R/headless.md; sed -n 1,5p /p/plugins/base/skills/monitor/references/settle.md; ls docs/x.md"}}))
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(json.dumps(e) for e in events) + "\nnot json\n")
        self.addCleanup(Path(f.name).unlink)
        skills, files = rb.log_reads(f.name)
        self.assertEqual(skills, {"work": 160, "gbase:go": 258})
        root = Path(__file__).resolve().parent.parent
        self.assertEqual(files, {
            "plugins/base/skills/monitor/references/settle.md": 40,
            "plugins/base/references/headless.md (via Bash)": len((root / "plugins/base/references/headless.md").read_text(encoding="utf-8")),
            "plugins/base/skills/monitor/references/settle.md (via Bash)": len((root / "plugins/base/skills/monitor/references/settle.md").read_text(encoding="utf-8")),
        })


if __name__ == "__main__":
    unittest.main()
