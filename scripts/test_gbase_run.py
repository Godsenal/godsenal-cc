"""Tests for scripts/gbase-run against a fake claude. Run: python3 -m unittest discover -s scripts"""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parent / "gbase-run"
_loader = importlib.machinery.SourceFileLoader("gbase_run", str(RUNNER))
gbase_run = importlib.util.module_from_spec(importlib.util.spec_from_loader("gbase_run", _loader))
_loader.exec_module(gbase_run)

# Stands in for `claude -p --output-format stream-json`: asks one question through AGENT_ASK_CMD,
# appends an evidence line, and ends with a final message chosen by --model.
FAKE_CLAUDE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, subprocess, sys
    args = sys.argv[1:]
    model = args[args.index("--model") + 1] if "--model" in args else "default"
    assert args[args.index("--plugin-dir") + 1].endswith("plugins/base")
    assert "ScheduleWakeup" in args[args.index("--disallowedTools") + 1]
    assert "GITHUB_TOKEN" not in os.environ
    run_dir = os.path.dirname(os.environ["AGENT_EVIDENCE_FILE"])
    with open(os.path.join(run_dir, "plugin-dirs"), "w") as f:
        f.write("\\n".join(args[i + 1] for i, a in enumerate(args) if a == "--plugin-dir"))
    if model == "hang":  # a session that never ends, with a grandchild like a subagent's shell
        child = subprocess.Popen(["sleep", "300"])
        open(os.path.join(run_dir, "child.pid"), "w").write(str(child.pid))
        print(json.dumps({"type": "system", "subtype": "init", "session_id": "s-hang", "model": model}), flush=True)
        child.wait()
    subprocess.run(["sh", "-c", os.environ["AGENT_ASK_CMD"] + ' "$@"', "ask", "Q?", "--recommend", "A", "--option", "B"])
    with open(os.environ["AGENT_EVIDENCE_FILE"], "a") as f:
        f.write(json.dumps({"step": "checks", "result": "pass", "command": "true", "detail": model}) + "\\n")
    finals = {
        "opus": "| # | severity | file:line | finding | action |\\n|---|---|---|---|---|\\n"
                "| 1 | high | `a.py:10` | null deref in `a \\\\| b` | needs decision |\\n| 2 | low | `b.py:3` | typo | needs decision |\\n",
        "sonnet": "| # | severity | file:line | finding | action |\\n|---|---|---|---|---|\\n"
                  "| 1 | medium | `a.py:12` | None not handled | needs decision |\\n",
        "mockup": "시안 2개\\nmockup: /m/app-onboarding-r2/index.html\\nmockup url: none — tailscale 없음\\n"
                  "mockup shots: /m/app-onboarding-r2/shots\\n",
        "settle": "ship: local feat/x @def5678 — 1 commits, not pushed\\nPR 본문 초안: " + os.environ["AGENT_PR_BODY_FILE"]
                  + "\\nsettle: 미확정 @abc1234 — 푸시 대기: 1 commits\\n",
        # agent-owned work run: go opened the PR and settled it
        "agent": "PR을 열었습니다\\npr: <https://github.com/o/r/pull/9>.\\nsettle: 수렴 @abc1234\\n"
                 if os.environ["AGENT_SHIP_OWNER"] == "agent" else "no ship owner\\n",
    }
    final = finals.get(model, "done\\n결정 필요: x → y (추천: z; 다른 선택지: z / w)\\nship: local feat/x @abc1234 — 1 commits, not pushed\\n"
                              "PR 본문 초안: " + os.environ["AGENT_PR_BODY_FILE"] + "\\n  결정 필요: indented, not a report line")
    print(json.dumps({"type": "system", "subtype": "init", "session_id": "s-" + model, "model": model}))
    print(json.dumps({"type": "result", "result": final, "total_cost_usd": 0.01}))
    if model == "twoturns":  # a later turn (a background task finishing) with no report lines
        print(json.dumps({"type": "result", "result": "기다리던 작업이 끝났습니다. 할 일은 없습니다.", "total_cost_usd": 0.02}))
''')


def _alive(pid):
    """True while pid runs and isn't a zombie (ps shows Z for a reaped-later child)."""
    r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
    return r.returncode == 0 and not r.stdout.strip().startswith("Z")


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

    def seed_answers(self, answers):
        run_dir = self.tmp / "home" / "runs" / "r1"
        run_dir.mkdir(parents=True)
        (run_dir / "answers.json").write_text(json.dumps({"answers": answers}, ensure_ascii=False))

    def ask(self, q, run_id="r1"):
        """What the run's AGENT_ASK_CMD prints for q."""
        return subprocess.run([sys.executable, str(RUNNER), "question", run_id, "ask", q, "--recommend", "A"],
                              env=self.env, capture_output=True, text=True).stdout.strip()

    def run_cli(self, *args):
        r = subprocess.run([sys.executable, str(RUNNER), *args], env=self.env, capture_output=True, text=True)
        return r, r.stdout.strip().splitlines()

    def test_run_writes_result_and_prints_its_path_last(self):
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--model", "haiku")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["branch"], "main")
        self.assertEqual(result["decisions"], [{"text": "결정 필요: x → y (추천: z; 다른 선택지: z / w)", "question": "x",
                                                "applied": "y", "recommend": "z", "options": ["z", "w"], "human": None}])
        self.assertTrue(result["ship"].startswith("ship: local feat/x"))
        self.assertEqual(result["pr_body_file"], str(Path(result["run_dir"]) / "pr-body.md"))
        self.assertEqual(result["evidence"][0]["detail"], "haiku")
        self.assertEqual(result["questions"], [{"question": "Q?", "recommend": "A", "options": ["B"]}])
        self.assertIsNone(result["settle"])
        self.assertIsNone(result["pr_url"])
        status = json.loads(self.run_cli("status", result["run_id"])[0].stdout)
        self.assertEqual(status["status"], "done")
        listed = [json.loads(line) for line in self.run_cli("list")[1]]
        self.assertEqual(listed[0]["run_id"], result["run_id"])

    def test_settle_reports_local_fixes_without_pushing(self):
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "settle", "--model", "settle")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["ship_owner"], "orchestrator")
        self.assertEqual(result["ship"], "ship: local feat/x @def5678 — 1 commits, not pushed")
        self.assertEqual(result["settle"], "settle: 미확정 @abc1234 — 푸시 대기: 1 commits")
        self.assertEqual(result["pr_body_file"], str(Path(result["run_dir"]) / "pr-body.md"))

    def test_agent_owned_work_run_reports_pr_url_and_settle(self):
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "work", "--task", "T-1", "--ship-owner", "agent",
                              "--model", "agent")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["ship_owner"], "agent")
        self.assertEqual(result["pr_url"], "https://github.com/o/r/pull/9")
        self.assertEqual(result["settle"], "settle: 수렴 @abc1234")
        self.assertIsNone(result["ship"])
        # answering its decisions keeps the run agent-owned
        answers = self.tmp / "answers.json"
        answers.write_text(json.dumps({"run_id": result["run_id"], "answers": []}))
        _, out = self.run_cli("--answers", str(answers))
        self.assertEqual(json.loads(Path(out[-1]).read_text())["ship_owner"], "agent")

    def test_mockup_lines_and_task_fill_the_slot(self):
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "mockup", "--task", "온보딩 시안", "--model", "mockup")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(Path(result["prompt_path"]).read_text().strip(), "/gbase:mockup 온보딩 시안")
        self.assertEqual(result["mockup"], {"html": "/m/app-onboarding-r2/index.html", "url": None,
                                            "screenshots": "/m/app-onboarding-r2/shots"})
        self.assertEqual(gbase_run.mockup("mockup url: http://100.1.2.3:8765/x/index.html")["url"],
                         "http://100.1.2.3:8765/x/index.html")
        self.assertIsNone(gbase_run.mockup("done"))

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
        self.assertEqual(self.ask("Q?", second["run_id"]), "B")

    def test_question_matches_answer_despite_spacing_punctuation_case_and_prefix(self):
        self.seed_answers([
            {"decision": "결정 필요:  Use  the CACHE", "answer": "fuzzy"},
            {"decision": "Use the cache?", "answer": "exact"},
            {"decision": "결정 필요： Bump to v1.2.0", "answer": "yes"},
            {"decision": "Drop logs?", "answer": "no"}, {"decision": "drop LOGS", "answer": "yes"},
            {"decision": "Set retries to -1?", "answer": "unlimited"}, {"decision": "Port it to C#?", "answer": "csharp"},
            {"decision": None, "answer": "x"}, {"decision": "?!", "answer": "empty"}])

        self.assertEqual(self.ask("Use the cache?"), "exact")
        self.assertEqual(self.ask("bump to v1.2.0?"), "yes")
        self.assertEqual(self.ask("Bump to v12.0?"), "")
        self.assertEqual(self.ask("drop logs"), "")  # two different answers normalize alike
        self.assertEqual(self.ask("Use a cache?"), "")
        self.assertEqual(self.ask("..."), "")
        self.assertEqual(self.ask("set retries to -1"), "unlimited")
        self.assertEqual(self.ask("Set retries to 1?"), "")
        self.assertEqual(self.ask("port it to c#"), "csharp")
        self.assertEqual(self.ask("Port it to C?"), "")

    def test_decision_lines_parse_into_parts(self):
        lines = ["결정 필요: rename a → b? → 열어둠 (draft) (추천: 고침; 다른 선택지: x → y / z (w)) · AGENT_ASK_CMD 에 넘김",
                 "결정 필요: x → y (다른 선택지: z)", "결정 필요: merge → 하지 않음 (사람이 할 일: gh pr merge 7)",
                 "결정 필요: no arrow (aside)", "결정 필요: Pick A · B? → A · B"]
        parsed = [gbase_run.parse_decision(line) for line in lines]
        self.assertEqual([d.pop("text") for d in parsed], lines)
        self.assertEqual(parsed, [
            {"question": "rename a → b?", "applied": "열어둠 (draft)", "recommend": "고침", "options": ["x → y", "z (w)"], "human": None},
            {"question": "x", "applied": "y", "recommend": None, "options": ["z"], "human": None},
            {"question": "merge", "applied": "하지 않음", "recommend": None, "options": [], "human": "gh pr merge 7"},
            {"question": "no arrow (aside)", "applied": None, "recommend": None, "options": [], "human": None},
            {"question": "Pick A · B?", "applied": "A · B", "recommend": None, "options": [], "human": None}])

    def test_question_matches_a_pasted_full_report_line(self):
        self.seed_answers([
            {"decision": "결정 필요: Use the cache? → 안 씀 (추천: 안 씀; 다른 선택지: 씀) · AGENT_ASK_CMD 에 넘김", "answer": "씀"},
            {"decision": "Rename a → b?", "answer": "yes"}])

        self.assertEqual(self.ask("Use the cache?"), "씀")
        self.assertEqual(self.ask("rename a → b"), "yes")  # a bare question keeps its arrow
        self.assertEqual(self.ask("Rename a?"), "")

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

    def test_new_worktree_branches_from_origin_not_the_checked_out_branch(self):
        origin = self.tmp / "origin.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(origin)], check=True)
        g = lambda *a: subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()
        g("remote", "add", "origin", str(origin))
        g("fetch", "-q", "origin")
        g("remote", "set-head", "origin", "main")
        g("checkout", "-q", "-b", "other")  # the main checkout sits on a branch with an unpushed commit
        g("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "unpushed")
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "w1")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["head_sha"], g("rev-parse", "origin/main"))
        wt = result["cwd"]  # no upstream: a bare `git push` must not land on main
        self.assertNotEqual(subprocess.run(["git", "-C", wt, "rev-parse", "@{u}"], capture_output=True).returncode, 0)
        self.assertEqual(result["base"], {"ref": "origin/main", "ahead": 0, "behind": 0})
        # reused later: not rebased, and base shows how far it is
        g("push", "-q", "origin", "other:main")
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "w1")
        self.assertEqual(json.loads(Path(out[-1]).read_text())["base"], {"ref": "origin/main", "ahead": 0, "behind": 1})
        r, _ = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "w2", "--base", "nope")
        self.assertIn("--base nope", r.stderr)

    def test_report_lines_survive_a_later_empty_turn(self):
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--model", "twoturns")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["ship"], "ship: local feat/x @abc1234 — 1 commits, not pushed")
        self.assertEqual(len(result["decisions"]), 1)
        self.assertIn("ship: local", Path(result["sessions"]["twoturns"]["final_path"]).read_text())

    def test_content_and_task_slots_load_every_plugin(self):
        task = self.tmp / "task.md"
        task.write_text("인스타 카드뉴스 1편: 'quoted' $(not run)\n")
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "task", "--task-file", str(task))
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(Path(result["prompt_path"]).read_text().strip(), "인스타 카드뉴스 1편: 'quoted' $(not run)")
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "content", "--task", "카드뉴스")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(Path(result["prompt_path"]).read_text().strip(), "/gshorts:content-common 카드뉴스")
        dirs = (Path(result["run_dir"]) / "plugin-dirs").read_text().splitlines()
        self.assertEqual([Path(d).name for d in dirs], ["base", "shorts"])
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship")
        dirs = (Path(json.loads(Path(out[-1]).read_text())["run_dir"]) / "plugin-dirs").read_text().splitlines()
        self.assertEqual([Path(d).name for d in dirs], ["base"])  # gapp/gshorts skills stay out of dev runs
        r, _ = self.run_cli("--repo", str(self.repo), "--slot", "task")
        self.assertIn("needs --task", r.stderr)

    def test_every_slot_prompt_fills_its_placeholders(self):
        # the runner fills only `<...>`; any other placeholder syntax ({ticket}) would reach claude as literal text
        slots = json.loads((gbase_run.PLUGIN_DIR / ".claude-plugin" / "factory.json").read_text())["slots"]
        for slot, spec in slots.items():
            if spec["invoke"] is None:
                continue
            prompt = gbase_run.build_prompt(slot, spec, "T-1 로그인 500", None)
            self.assertNotRegex(prompt, r"[<{][^>}]*[>}]", slot)
            self.assertIn("T-1 로그인 500", prompt, slot)
        r, _ = self.run_cli("--repo", str(self.repo), "--slot", "work")
        self.assertIn("needs --task", r.stderr)

    def test_review_table_and_missing_plugin(self):
        table = "| # | severity | file:line | finding | action |\n|---|---|---|---|---|\n| 1 | high | `a.py:1` | x | y |\n"
        self.assertEqual(gbase_run.final_text([table, "기다리던 작업이 끝났습니다."]), table)
        with self.assertRaises(SystemExit):
            gbase_run.plugin_dirs("content", "/nope:content-common")

    def test_stop_ends_the_session_process_group(self):
        runner = subprocess.Popen([sys.executable, str(RUNNER), "--repo", str(self.repo), "--slot", "ship", "--model", "hang"],
                                  env=self.env, stdout=subprocess.DEVNULL)
        runs = Path(self.env["GBASE_HOME"]) / "runs"
        for _ in range(100):
            pids = list(runs.glob("*/child.pid"))
            if pids and pids[0].read_text():
                break
            time.sleep(0.1)
        child = int(pids[0].read_text())
        r, out = self.run_cli("stop", pids[0].parent.name)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(out[-1])["stopped_by"], "SIGTERM")
        runner.wait(timeout=10)
        result = json.loads((pids[0].parent / "result.json").read_text())
        self.assertEqual((result["status"], result["stopped_by"]), ("failed", "SIGTERM"))
        time.sleep(0.2)
        self.assertFalse(_alive(child))

    def test_status_reports_dead_runner(self):
        run = Path(self.env["GBASE_HOME"]) / "runs" / "r1"
        run.mkdir(parents=True)
        (run / "result.json").write_text(json.dumps({"run_id": "r1", "status": "running", "pid": 999999}))
        self.assertEqual(json.loads(self.run_cli("status", "r1")[0].stdout)["status"], "dead")


if __name__ == "__main__":
    unittest.main()
