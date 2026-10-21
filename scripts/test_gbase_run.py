"""Tests for scripts/gbase-run against a fake claude. Run: python3 -m unittest discover -s scripts"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parent / "gbase-run"

# Stands in for `claude -p --output-format stream-json`: asks one question through AGENT_ASK_CMD,
# appends an evidence line, and ends with a final message chosen by --model.
FAKE_CLAUDE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, subprocess, sys
    args = sys.argv[1:]
    model = args[args.index("--model") + 1] if "--model" in args else "default"
    assert args[args.index("--plugin-dir") + 1].endswith("plugins/base")
    assert "GITHUB_TOKEN" not in os.environ
    subprocess.run(["sh", "-c", os.environ["AGENT_ASK_CMD"] + ' "$@"', "ask", "Q?", "--recommend", "A", "--option", "B"])
    with open(os.environ["AGENT_EVIDENCE_FILE"], "a") as f:
        f.write(json.dumps({"step": "checks", "result": "pass", "command": "true", "detail": model}) + "\\n")
    finals = {
        "opus": "| # | severity | file:line | finding | action |\\n|---|---|---|---|---|\\n"
                "| 1 | high | `a.py:10` | null deref in `a \\\\| b` | needs decision |\\n| 2 | low | `b.py:3` | typo | needs decision |\\n",
        "sonnet": "| # | severity | file:line | finding | action |\\n|---|---|---|---|---|\\n"
                  "| 1 | medium | `a.py:12` | None not handled | needs decision |\\n",
    }
    final = finals.get(model, "done\\n결정 필요: x → y (다른 선택지: z)\\nship: local feat/x @abc1234 — 1 commits, not pushed\\n"
                              "PR 본문 초안: " + os.environ["AGENT_PR_BODY_FILE"] + "\\n  결정 필요: indented, not a report line")
    print(json.dumps({"type": "system", "subtype": "init", "session_id": "s-" + model, "model": model}))
    print(json.dumps({"type": "result", "result": final, "total_cost_usd": 0.01}))
''')


class GbaseRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "--allow-empty", "-m", "init"], check=True)
        fake = self.tmp / "claude"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        self.env = {**os.environ, "GBASE_CLAUDE": str(fake), "GBASE_HOME": str(self.tmp / "home"),
                    "GITHUB_TOKEN": "stale"}
        self.env.pop("GBASE_ASK_CMD", None)

    def run_cli(self, *args):
        r = subprocess.run([sys.executable, str(RUNNER), *args], env=self.env, capture_output=True, text=True)
        return r, r.stdout.strip().splitlines()

    def test_run_writes_result_and_prints_its_path_last(self):
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--model", "haiku")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["branch"], "main")
        self.assertEqual(result["decisions"], ["결정 필요: x → y (다른 선택지: z)"])
        self.assertTrue(result["ship"].startswith("ship: local feat/x"))
        self.assertEqual(result["pr_body_file"], str(Path(result["run_dir"]) / "pr-body.md"))
        self.assertEqual(result["evidence"][0]["detail"], "haiku")
        self.assertEqual(result["questions"], [{"question": "Q?", "recommend": "A", "options": ["B"]}])
        self.assertIsNone(result["settle"])
        status = json.loads(self.run_cli("status", result["run_id"])[0].stdout)
        self.assertEqual(status["status"], "done")
        listed = [json.loads(line) for line in self.run_cli("list")[1]]
        self.assertEqual(listed[0]["run_id"], result["run_id"])

    def test_answers_feed_prompt_inherit_run_and_answer_exact_question(self):
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "reproduce", "--task", "login 500s", "--model", "x")
        first = json.loads(Path(out[-1]).read_text())
        self.assertEqual(Path(first["prompt_path"]).read_text().strip(), "/gbase:reproduce login 500s")
        answers = self.tmp / "answers.json"
        answers.write_text(json.dumps({"run_id": first["run_id"], "answers": [{"decision": "Q?", "answer": "B"}]}))
        r, out = self.run_cli("--answers", str(answers))
        second = json.loads(Path(out[-1]).read_text())
        self.assertEqual((second["slot"], second["task"], second["answers_from"]), ("reproduce", "login 500s", first["run_id"]))
        self.assertIn("- Q? → B", Path(second["prompt_path"]).read_text())
        ask = subprocess.run([sys.executable, str(RUNNER), "question", second["run_id"], "ask", "Q?", "--recommend", "A"],
                             env=self.env, capture_output=True, text=True)
        self.assertEqual(ask.stdout.strip(), "B")

    def test_question_matches_answer_despite_spacing_punctuation_case_and_prefix(self):
        run_dir = self.tmp / "home" / "runs" / "r1"
        run_dir.mkdir(parents=True)
        (run_dir / "answers.json").write_text(json.dumps({"answers": [
            {"decision": "결정 필요:  Use  the CACHE", "answer": "fuzzy"},
            {"decision": "Use the cache?", "answer": "exact"},
            {"decision": "결정 필요： Bump to v1.2.0", "answer": "yes"},
            {"decision": "Drop logs?", "answer": "no"}, {"decision": "drop LOGS", "answer": "yes"},
            {"decision": "Set retries to -1?", "answer": "unlimited"}, {"decision": "Port it to C#?", "answer": "csharp"},
            {"decision": None, "answer": "x"}, {"decision": "?!", "answer": "empty"}]}, ensure_ascii=False))

        def ask(q):
            return subprocess.run([sys.executable, str(RUNNER), "question", "r1", "ask", q, "--recommend", "A"],
                                  env=self.env, capture_output=True, text=True).stdout.strip()

        self.assertEqual(ask("Use the cache?"), "exact")
        self.assertEqual(ask("bump to v1.2.0?"), "yes")
        self.assertEqual(ask("Bump to v12.0?"), "")
        self.assertEqual(ask("drop logs"), "")  # two different answers normalize alike
        self.assertEqual(ask("Use a cache?"), "")
        self.assertEqual(ask("..."), "")
        self.assertEqual(ask("set retries to -1"), "unlimited")
        self.assertEqual(ask("Set retries to 1?"), "")
        self.assertEqual(ask("port it to c#"), "csharp")
        self.assertEqual(ask("Port it to C?"), "")

    def test_review2_runs_both_models_and_merges_by_location(self):
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "review2")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(set(result["sessions"]), {"opus", "sonnet"})
        found = {f["location"]: (f["severity"], f["found_by"]) for f in result["findings"]}
        self.assertEqual(found, {"a.py:10": ("high", ["opus", "sonnet"]), "b.py:3": ("low", ["opus"])})
        self.assertIn("| both |", Path(result["report_file"]).read_text())
        self.assertEqual(result["findings"][0]["finding"], "null deref in `a | b`")

    def test_worktree_and_unknown_slot(self):
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "checks", "--worktree", "t1")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["branch"], "gbase/t1")
        self.assertIn("gbase:verify:start", Path(result["prompt_path"]).read_text())
        r, _ = self.run_cli("--repo", str(self.repo), "--slot", "nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown slot", r.stderr)
        r, _ = self.run_cli("--repo", str(self.repo), "--slot", "reproduce")
        self.assertIn("needs --task", r.stderr)

    def test_status_reports_dead_runner(self):
        run = Path(self.env["GBASE_HOME"]) / "runs" / "r1"
        run.mkdir(parents=True)
        (run / "result.json").write_text(json.dumps({"run_id": "r1", "status": "running", "pid": 999999}))
        self.assertEqual(json.loads(self.run_cli("status", "r1")[0].stdout)["status"], "dead")


if __name__ == "__main__":
    unittest.main()
