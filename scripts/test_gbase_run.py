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
    cfg = os.environ.get("CLAUDE_CONFIG_DIR", "")
    marker = lambda name: bool(cfg) and os.path.exists(os.path.join(cfg, name))
    if "--max-turns" in args and args[args.index("-p") + 1] == "ok":  # gbase-run's account preflight: logged-out fails it, logged-out-run doesn't
        if cfg:
            open(os.path.join(cfg, "preflights"), "a").write("x")
        bad = marker("logged-out")
        print(json.dumps({"type": "result", "is_error": bad, "result": "Not logged in · Please run /login" if bad else "ok"}))
        sys.exit(1 if bad else 0)
    if marker("logged-out") or marker("logged-out-run") or marker("limited-run"):  # ends before any tool call
        print(json.dumps({"type": "system", "subtype": "init", "session_id": "s-x", "model": model}))
        limited = marker("limited-run")
        print(json.dumps({"type": "result", "is_error": True, "terminal_reason": "api_error",
                          **({"api_error": "usage_limit_reached"} if limited else {}),
                          "result": "You've hit your 5-hour limit · resets 1:50pm" if limited else "Not logged in · Please run /login"}))
        sys.exit(1)
    assert args[args.index("--plugin-dir") + 1].endswith("plugins/base")
    assert "ScheduleWakeup" in args[args.index("--disallowedTools") + 1]
    assert "GITHUB_TOKEN" not in os.environ and "GBASE_NOTIFY_CMD" not in os.environ
    run_dir = os.path.dirname(os.environ["AGENT_EVIDENCE_FILE"])
    assert os.environ["GBASE_RUN_ID"] == os.path.basename(run_dir)
    with open(os.path.join(run_dir, "plugin-dirs"), "w") as f:
        f.write("\\n".join(args[i + 1] for i, a in enumerate(args) if a == "--plugin-dir"))
    if model == "hang":  # a session that never ends, with a grandchild like a subagent's shell
        child = subprocess.Popen(["sleep", "300"])
        open(os.path.join(run_dir, "child.pid"), "w").write(str(child.pid))
        print(json.dumps({"type": "system", "subtype": "init", "session_id": "s-hang", "model": model}), flush=True)
        child.wait()
    open(os.path.join(run_dir, "ran-on"), "a").write(os.path.basename(cfg) + "\\n")
    print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill",
                                                                    "input": {"skill": "gbase:go"}}]}}))
    if model == "commits":  # a session that commits c.txt in its checkout
        open("c.txt", "w").write(os.environ.get("FAKE_CONTENT", "run") + "\\n")
        subprocess.run(["git", "add", "c.txt"], check=True)
        subprocess.run(["git", "commit", "-q", "-m", "run commit"], check=True)
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
        "lessons": "카드 1편 완료\\n교훈: content-common — 2026-10-29 \\"이거별로\\": 규칙 A\\n교훈: instagram-card-news — 규칙 B\\n",
        "agent": "PR을 열었습니다\\npr: <https://github.com/o/r/pull/9>.\\nsettle: 수렴 @abc1234\\n"
                 if os.environ["AGENT_SHIP_OWNER"] == "agent" else "no ship owner\\n",
        # go → monitor ran long and the last message kept only the settle line
        "settled": "PR #64를 정리했습니다\\nsettle: 사람 필요 @7b0a03f\\n",
    }
    final = finals.get(model, "done\\n결정 필요: x → y (추천: z; 다른 선택지: z / w)\\nship: local feat/x @abc1234 — 1 commits, not pushed\\n"
                              "PR 본문 초안: " + os.environ["AGENT_PR_BODY_FILE"] + "\\n  결정 필요: indented, not a report line")
    print(json.dumps({"type": "system", "subtype": "init", "session_id": "s-" + model, "model": model}))
    print(json.dumps({"type": "result", "result": final, "total_cost_usd": 0.01}))
    if model == "stops":  # go ended its turn on review's table: the change sits uncommitted, no PR
        if "--resume" in args:
            final = "pr: https://github.com/o/r/pull/12\\nsettle: 수렴 @abc1234\\n"
            open(os.path.join(run_dir, "resume-prompt"), "w").write(args[args.index("-p") + 1])
        else:
            open("change.txt", "w").write("x")
            final = "| # | severity | file:line | finding | action |\\n|---|---|---|---|---|\\n| 1 | low | `a.py:1` | x | auto-fixed |\\n"
        print(json.dumps({"type": "result", "result": final, "total_cost_usd": 0.5}))
        sys.exit(0)
    if model == "capped":  # the turn cap ended the session mid-work; the wrap-up session reports what's left
        if "--resume" in args:
            open(os.path.join(run_dir, "wrapup-args"), "w").write(json.dumps(args))
            print(json.dumps({"type": "result", "result": "절반 했습니다\\n남은 작업: B 화면 붙이기\\n남은 작업: C 마이그레이션\\n"
                                                           "결정 필요: 이어서 할지 → 멈춤", "total_cost_usd": 0.1}))
            sys.exit(0)
        open("change.txt", "w").write("x")
        print(json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True, "total_cost_usd": 2.0}))
        sys.exit(1)
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
                    "GITHUB_TOKEN": "stale", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        for k in ("GBASE_ASK_CMD", "GBASE_ACCOUNTS", "CLAUDE_CONFIG_DIR"):
            self.env.pop(k, None)

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
                                                "applied": "y", "recommend": "z", "options": ["z", "w"], "human": None,
                                                "incomplete": False}])
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
        line = f"Claude Code · agent · 계정 default · run {result['run_id']} · 스킬 gbase:work→go"
        self.assertEqual((result["provenance"], result["account"]), (line, "default"))
        self.assertEqual(self.run_cli("cite", result["run_id"])[1], [line])
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
        self.assertEqual(second["model"], "x")

    def test_slot_default_model_unless_given_or_answered_on_the_same_slot(self):
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship")
        ship = json.loads(Path(out[-1]).read_text())
        self.assertEqual((ship["model"], ship["evidence"][0]["detail"]), ("sonnet", "sonnet"))
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "work", "--task", "T", "--model", "x")
        work = json.loads(Path(out[-1]).read_text())
        answers = self.tmp / "answers.json"
        answers.write_text(json.dumps({"run_id": work["run_id"], "answers": []}))
        _, out = self.run_cli("--answers", str(answers), "--slot", "ship")
        self.assertEqual(json.loads(Path(out[-1]).read_text())["model"], "sonnet")

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
        self.assertEqual([d.pop("incomplete") for d in parsed], [False] * 5)
        self.assertEqual(parsed, [
            {"question": "rename a → b?", "applied": "열어둠 (draft)", "recommend": "고침", "options": ["x → y", "z (w)"], "human": None},
            {"question": "x", "applied": "y", "recommend": None, "options": ["z"], "human": None},
            {"question": "merge", "applied": "하지 않음", "recommend": None, "options": [], "human": "gh pr merge 7"},
            {"question": "no arrow (aside)", "applied": None, "recommend": None, "options": [], "human": None},
            {"question": "Pick A · B?", "applied": "A · B", "recommend": None, "options": [], "human": None}])

    def test_a_decision_that_points_at_the_report_is_incomplete(self):
        # run 20261102-121409-work-3e7261: the question is only in final.md
        d = gbase_run.parse_decision("결정 필요: 위 2건을 확인해 주세요. 그대로 두면 이 PR 상태대로 머지 대기입니다.")
        self.assertEqual((d["recommend"], d["options"], d["incomplete"]), (None, [], True))
        self.assertTrue(gbase_run.parse_decision("결정 필요: 이 PR의 2건 → 그대로 둠")["incomplete"])
        self.assertFalse(gbase_run.parse_decision("결정 필요: 위 2건 → 둠 (추천: 고침)")["incomplete"])  # 추천 says what
        # run 20261102-235341-work-bae706: self-contained, so not incomplete; the prompt had put push out of scope,
        # which headless.md now keeps from becoming a decision at all
        d = gbase_run.parse_decision("결정 필요: `feat/feedback`를 원격에 올리거나 PR을 열려면 쓸 수 있는 remote를 정하고 "
                                     "push를 따로 요청해 주세요")
        self.assertFalse(d["incomplete"])
        self.assertFalse(gbase_run.parse_decision("결정 필요: 위험한 마이그레이션을 지금 돌릴까요? → 안 돌림")["incomplete"])

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
        prompt = Path(result["prompt_path"]).read_text()
        self.assertTrue(prompt.startswith("인스타 카드뉴스 1편: 'quoted' $(not run)\n\n"), prompt)
        # a bare task loads no skill: the headless rules ride in the prompt
        self.assertIn("약관·법적 동의, 대표자·본인 확인 체크, 사실 진술 체크박스", prompt)
        self.assertIn("`결정 필요: [질문] → [적용한 것] (추천: [추천]; 다른 선택지: [a] / [b])`", prompt)
        self.assertIn(str(gbase_run.PLUGIN_DIR / "references" / "headless.md"), prompt)
        # the copy bots paste into a direct `claude -p` template is the same paragraph
        harness = (gbase_run.PLUGIN_DIR / "references" / "harness.md").read_text()
        self.assertIn(gbase_run.TASK_HEADLESS.format(headless="(gbase checkout)/plugins/base/references/headless.md"),
                      harness)
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
        r, out = self.run_cli("stop", pids[0].parent.name, "--reason", "TTL만 넣는 작업이라 끊음")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((json.loads(out[-1])["stopped_by"], json.loads(out[-1])["stop_reason"]),
                         ("SIGTERM", "TTL만 넣는 작업이라 끊음"))
        runner.wait(timeout=10)
        result = json.loads((pids[0].parent / "result.json").read_text())
        self.assertEqual((result["status"], result["stopped_by"]), ("failed", "SIGTERM"))
        time.sleep(0.2)
        self.assertFalse(_alive(child))

    def test_lessons_hand_off_to_a_work_run(self):
        self.accounts(a=[])  # no missing-accounts warning in `next`
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "content", "--task", "카드뉴스", "--model", "lessons")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["lessons"], ['교훈: content-common — 2026-10-29 "이거별로": 규칙 A',
                                             "교훈: instagram-card-news — 규칙 B"])
        lessons_md = Path(result["run_dir"]) / "lessons.md"
        self.assertIn("교훈: instagram-card-news — 규칙 B", lessons_md.read_text())
        self.assertEqual(out[-2], f"next: {result['next']}")
        self.assertIn(f"--slot work --task-file {lessons_md} --worktree lessons --exclusive", result["next"])
        self.assertIn("교훈:", Path(result["sessions"]["lessons"]["final_path"]).read_text())
        # a work run is the one that ships them
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "work", "--task", "T", "--model", "lessons")
        self.assertIsNone(json.loads(Path(out[-1]).read_text())["next"])
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship")
        self.assertEqual((json.loads(Path(out[-1]).read_text())["lessons"], len(out)), ([], 1))

    def test_repo_key_matches_clones_by_origin(self):
        g = lambda repo, *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)
        other = self.tmp / "other-name"
        subprocess.run(["git", "clone", "-q", str(self.repo), str(other)], check=True)
        g(self.repo, "remote", "add", "origin", "git@github.com:Godsenal/godsenal-cc.git")
        g(other, "remote", "set-url", "origin", "https://github.com/godsenal/godsenal-cc/")
        self.assertEqual(gbase_run.repo_key(self.repo), "github.com/godsenal/godsenal-cc")
        self.assertEqual(gbase_run.repo_key(other), "github.com/godsenal/godsenal-cc")
        g(other, "remote", "set-url", "origin", "ssh://git@github.com:22/godsenal/godsenal-cc.git")
        self.assertEqual(gbase_run.repo_key(other), "github.com:22/godsenal/godsenal-cc")

    def test_run_on_a_linked_worktree_records_the_main_checkout(self):
        wt = self.tmp / "wt"
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "-b", "feat", str(wt)], check=True)
        _, out = self.run_cli("--repo", str(wt), "--slot", "ship")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["repo"], result["cwd"], result["branch"]), (str(self.repo.resolve()), str(wt.resolve()), "feat"))
        # --worktree reuses the worktree that already has the branch, wherever it is
        subprocess.run(["git", "-C", str(self.repo), "branch", "gbase/x"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", str(self.tmp / "old-x"), "gbase/x"], check=True)
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "x")
        self.assertEqual(json.loads(Path(out[-1]).read_text())["cwd"], str((self.tmp / "old-x").resolve()))

    def seed_running(self, run_id, pid):
        run = Path(self.env["GBASE_HOME"]) / "runs" / run_id
        run.mkdir(parents=True)
        (run / "result.json").write_text(json.dumps({"run_id": run_id, "status": "running", "pid": pid,
                                                     "repo": str(self.repo)}))

    def test_concurrent_run_on_the_same_repo_warns_and_exclusive_waits(self):
        self.seed_running("00000000-000000-work-aaaaaa", os.getpid())
        self.seed_running("00000000-000000-work-dead00", 999999)
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship")
        self.assertEqual(json.loads(Path(out[-1]).read_text())["concurrent"], ["00000000-000000-work-aaaaaa"])
        self.assertIn("running on the same repo", r.stderr)
        # a runner that isn't our child (a child would linger as a zombie, which still looks alive)
        (Path(self.env["GBASE_HOME"]) / "runs" / "00000000-000000-work-aaaaaa" / "result.json").unlink()
        pid = subprocess.run(["sh", "-c", "sleep 2 >/dev/null 2>&1 & echo $!"], capture_output=True, text=True).stdout
        self.seed_running("00000000-000001-work-bbbbbb", int(pid))
        started = time.time()
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--exclusive")
        self.assertGreaterEqual(time.time() - started, 2)
        self.assertIn("waiting for them to end", r.stderr)
        self.assertEqual(json.loads(Path(out[-1]).read_text())["status"], "done")

    def test_exclusive_runs_take_turns_on_a_repo_lock(self):
        key = gbase_run.repo_key(self.repo)
        lock_path = Path(self.env["GBASE_HOME"]) / "locks" / f"{gbase_run.hashlib.sha1(key.encode()).hexdigest()[:12]}.lock"
        lock_path.parent.mkdir(parents=True)
        held = open(lock_path, "w")
        gbase_run.fcntl.flock(held, gbase_run.fcntl.LOCK_EX)  # an earlier --exclusive run started the same second
        waiting = subprocess.Popen([sys.executable, str(RUNNER), "--repo", str(self.repo), "--slot", "ship", "--exclusive"],
                                   env=self.env, stdout=subprocess.PIPE, text=True)
        deadline = time.time() + 20
        while not (runs := list((Path(self.env["GBASE_HOME"]) / "runs").glob("*/result.json"))) and time.time() < deadline:
            time.sleep(0.2)
        time.sleep(1)  # past the first lock attempt
        self.assertTrue(json.loads(runs[0].read_text())["waiting"])
        self.assertIsNone(waiting.poll())
        # a run still in line isn't one to wait for, so the lock holder doesn't wait on it
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship")
        self.assertNotIn("concurrent", json.loads(Path(out[-1]).read_text()))
        held.close()
        out, _ = waiting.communicate(timeout=30)
        result = json.loads(Path(out.splitlines()[-1]).read_text())
        self.assertEqual((result["status"], "waiting" in result), ("done", False))

    def test_a_reused_pid_is_not_the_runner(self):
        self.seed_running("r-reused", os.getpid())
        path = Path(self.env["GBASE_HOME"]) / "runs" / "r-reused" / "result.json"
        path.write_text(json.dumps({**json.loads(path.read_text()), "started_at": "2001-01-01T00:00:00+0000"}))
        self.assertEqual(json.loads(self.run_cli("status", "r-reused")[0].stdout)["status"], "dead")
        path.write_text(json.dumps({**json.loads(path.read_text()), "started_at": gbase_run.now()}))
        self.assertEqual(json.loads(self.run_cli("status", "r-reused")[0].stdout)["status"], "running")

    def test_a_shipping_run_that_stops_before_its_pr_is_resumed_once(self):
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "work", "--task", "T", "--ship-owner", "agent",
                              "--model", "stops")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["pr_url"], result["settle"]), ("https://github.com/o/r/pull/12", "settle: 수렴 @abc1234"))
        self.assertEqual((result["sessions"]["stops"]["resumed"], result["sessions"]["stops"]["cost_usd"]), (True, 1.0))
        self.assertIn("no `pr:` line", (Path(result["run_dir"]) / "resume-prompt").read_text())
        # nothing in the worktree: nothing to resume
        (self.repo / "change.txt").unlink()
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--ship-owner", "agent", "--model", "lessons")
        self.assertNotIn("resumed", json.loads(Path(out[-1]).read_text())["sessions"]["lessons"])

    def test_a_run_that_reaches_the_turn_cap_wraps_up_and_reports_what_is_left(self):
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "work", "--task", "T", "--ship-owner", "agent",
                              "--model", "capped", "--max-turns", "7")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["turn_limit"], result["status"]), (7, "done"))
        self.assertEqual(result["followups"], ["B 화면 붙이기", "C 마이그레이션"])
        self.assertIn("이어서 할지", [d["question"] for d in result["decisions"]])
        self.assertIsNone(result["pr_url"])
        session = result["sessions"]["capped"]
        self.assertEqual((session["cost_usd"], session.get("resumed")), (2.1, None))  # wrapped up, not resumed to ship
        args = json.loads((Path(result["run_dir"]) / "wrapup-args").read_text())
        self.assertIn("turn limit (7)", args[args.index("-p") + 1])
        self.assertEqual(args[args.index("--max-turns") + 1], str(gbase_run.WRAPUP_TURNS))
        # an uncapped run passes the default cap and reports no limit
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--model", "haiku")
        self.assertIsNone(json.loads(Path(out[-1]).read_text())["turn_limit"])

    def test_a_worktree_whose_pr_ended_starts_over(self):
        g = lambda *a: subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "lessons")
        first = Path(json.loads(Path(out[-1]).read_text())["cwd"])
        tip = g("rev-parse", "gbase/lessons")
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(f"#!/bin/sh\necho '[{{\"number\": 5, \"state\": \"MERGED\", \"headRefOid\": \"{tip}\"}}]'\n")
        (bin_dir / "gh").chmod(0o755)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "lessons")
        self.assertEqual(json.loads(Path(out[-1]).read_text())["cwd"], str(first))  # a fresh one at the same path
        self.assertTrue(Path(f"{first}-pr5").is_dir())
        self.assertEqual(g("rev-parse", "gbase/lessons-pr5"), tip)
        # the fresh branch isn't the merged PR's head, so the next run reuses it
        g("-C", str(first), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "next")
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "lessons")
        self.assertEqual(json.loads(Path(out[-1]).read_text())["branch"], "gbase/lessons")
        self.assertFalse(Path(f"{first}-pr5-pr5").exists())

    def test_settle_finds_the_branch_pr_without_a_pr_line(self):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text("#!/bin/sh\necho https://github.com/o/r/pull/33\n")
        (bin_dir / "gh").chmod(0o755)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "settle", "--model", "settle")
        self.assertEqual(json.loads(Path(out[-1]).read_text())["pr_url"], "https://github.com/o/r/pull/33")
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship")
        self.assertIsNone(json.loads(Path(out[-1]).read_text())["pr_url"])  # an orchestrator-owned run opens no PR to look up

    def fake_gh(self, url):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(f"#!/bin/sh\necho {url}\n")
        (bin_dir / "gh").chmod(0o755)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"

    def test_agent_owned_work_run_finds_its_pr_without_a_pr_line(self):
        self.fake_gh("https://github.com/o/r/pull/64")
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "work", "--task", "T", "--ship-owner", "agent",
                              "--model", "settled")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["pr_url"], result["settle"]), ("https://github.com/o/r/pull/64", "settle: 사람 필요 @7b0a03f"))
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "work", "--task", "T", "--model", "settled")
        self.assertIsNone(json.loads(Path(out[-1]).read_text())["pr_url"])  # an orchestrator-owned run opens no PR

    def test_dir_runs_task_and_content_in_a_plain_folder(self):
        folder = self.tmp / "tasks" / "carousel"
        folder.mkdir(parents=True)
        (folder / "prompt.md").write_text("캐러셀 초안 1편\n")
        r, out = self.run_cli("--dir", str(folder), "--slot", "task", "--task-file", str(folder / "prompt.md"))
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["status"], result["repo"], result["dir"], result["cwd"]),
                         ("done", None, str(folder.resolve()), str(folder.resolve())))
        self.assertEqual((result["branch"], result["base"]), (None, None))
        self.assertTrue(Path(result["prompt_path"]).read_text().startswith("캐러셀 초안 1편\n\n"))
        # a follow-up answers run continues in the same folder
        answers = self.tmp / "answers.json"
        answers.write_text(json.dumps({"run_id": result["run_id"], "answers": [{"decision": "Q?", "answer": "B"}]}))
        _, out = self.run_cli("--answers", str(answers))
        self.assertEqual(json.loads(Path(out[-1]).read_text())["cwd"], str(folder.resolve()))
        _, out = self.run_cli("--dir", str(folder), "--slot", "content", "--task", "카드뉴스", "--model", "lessons")
        self.assertTrue(json.loads(Path(out[-1]).read_text())["next"])
        for args, err in [(["--slot", "work", "--task", "T"], "needs a --repo"),
                          (["--slot", "task", "--task", "T", "--worktree", "w"], "drop --repo"),
                          (["--slot", "task", "--task", "T", "--exclusive"], "drop --repo")]:
            r, _ = self.run_cli("--dir", str(folder), *args)
            self.assertIn(err, r.stderr)
        r, _ = self.run_cli("--dir", str(self.tmp / "nope"), "--slot", "task", "--task", "T")
        self.assertIn("is not a directory", r.stderr)

    def test_start_returns_at_once_and_the_run_goes_on(self):
        folder = self.tmp / "job"
        folder.mkdir()
        started = time.time()
        r, out = self.run_cli("start", "--dir", str(folder), "--slot", "task", "--task", "T", "--model", "hang")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(time.time() - started, 10)  # the session itself never ends
        run_id, path = out
        self.assertEqual(Path(path), Path(self.env["GBASE_HOME"]).resolve() / "runs" / run_id / "result.json")
        self.assertEqual(json.loads(self.run_cli("status", run_id)[0].stdout)["status"], "running")
        r, out = self.run_cli("stop", run_id)
        self.assertEqual(json.loads(out[-1])["stopped_by"], "SIGTERM")
        # a run that ends on its own leaves the runner's output in runner.log
        _, (run_id, path) = self.run_cli("start", "--dir", str(folder), "--slot", "task", "--task", "T")
        deadline = time.time() + 30
        while json.loads(self.run_cli("status", run_id)[0].stdout)["status"] == "running" and time.time() < deadline:
            time.sleep(0.2)
        self.assertEqual(json.loads(Path(path).read_text())["status"], "done")
        self.assertEqual((Path(path).parent / "runner.log").read_text().strip().splitlines()[-1], path)
        # a run that can't start fails the start itself
        r, out = self.run_cli("start", "--dir", str(folder), "--slot", "work")
        self.assertEqual((r.returncode != 0, out), (True, []))
        self.assertIn("needs a --repo", r.stderr)

    def accounts(self, **markers):
        """GBASE_ACCOUNTS of config dirs a, b, … ; markers name files the fake claude reacts to (logged-out fails
        the preflight too, logged-out-run and limited-run only the real session)."""
        names = []
        for name, files in markers.items():
            d = self.tmp / "acct" / name
            d.mkdir(parents=True, exist_ok=True)
            for f in d.iterdir():
                f.unlink()
            for f in files:
                (d / f).touch()
            names.append(f"{name}:{d}")
        self.env.update(GBASE_ACCOUNTS=",".join(names), GBASE_PREFLIGHT_TTL="0")

    def g(self, *args, cwd=None):
        r = subprocess.run(["git", "-C", str(cwd or self.repo), *args], capture_output=True, text=True, env=self.env)
        return r.stdout.strip()

    def test_a_logged_out_account_hands_the_run_to_the_next_and_leaves_no_worktree(self):
        # the session itself fails on "Not logged in" (the preflight passed): the same prompt runs on b
        self.accounts(a=["logged-out-run"], b=[])
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "w1")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["status"], result["account"], result["failure"]), ("done", "b", None))
        self.assertEqual([(f["kind"], f["account"], f["stage"]) for f in result["failures"]], [("auth", "a", "run")])
        self.assertEqual((Path(result["run_dir"]) / "ran-on").read_text().split(), ["b"])
        self.assertIn("계정 b", result["provenance"])
        # the preflight catches it: no session, and no worktree made for the account that can't run
        self.accounts(a=["logged-out"], b=["logged-out"])
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "w2")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["status"], result["failure"]["kind"], result["account"]), ("failed", "auth", None))
        self.assertEqual([f["stage"] for f in result["failures"]], ["preflight", "preflight"])
        self.assertIn("no account can run", r.stderr)
        self.assertFalse(gbase_run.worktree_path(self.repo.resolve(), "w2").exists())
        self.assertEqual(self.g("branch", "--list", "gbase/w2"), "")
        # every session fails before any tool call: the worktree made for the run goes with it
        self.accounts(a=["logged-out-run"], b=["limited-run"])
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "w3")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["failure"]["kind"], result["failure"]["account"], result["worktree_removed"]),
                         ("usage_limit", "b", True))
        self.assertIn("5-hour limit", result["failure"]["detail"])
        self.assertFalse(Path(result["cwd"]).exists())
        self.assertEqual(self.g("branch", "--list", "gbase/w3"), "")

    def test_an_account_that_auth_failed_on_the_task_goes_last_and_answers_keep_the_account(self):
        self.accounts(a=["logged-out-run"], b=[])
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "reproduce", "--task", "T-9")
        self.assertEqual(json.loads(Path(out[-1]).read_text())["account"], "b")
        self.accounts(a=[], b=[])  # a works again, but the same task starts on b
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "reproduce", "--task", "T-9")
        first = json.loads(Path(out[-1]).read_text())
        self.assertEqual((first["account"], first["failures"]), ("b", []))
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "reproduce", "--task", "T-10")
        self.assertEqual(json.loads(Path(out[-1]).read_text())["account"], "a")
        answers = self.tmp / "answers.json"
        answers.write_text(json.dumps({"run_id": first["run_id"], "answers": []}))
        _, out = self.run_cli("--answers", str(answers))
        self.assertEqual(json.loads(Path(out[-1]).read_text())["account"], "b")

    def test_without_an_accounts_list_the_run_warns_in_next(self):
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["status"], "done")
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("계정 목록 없음", result["next"])
        self.assertIn("gbase-run doctor", result["next"])
        self.assertEqual(out[-2], f"next: {result['next']}")
        self.accounts(a=[])
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["warnings"], result["next"], len(out)), ([], None, 1))

    def test_account_flag_goes_first_and_aliases_are_one_account(self):
        self.accounts(a=[], b=[])
        self.env["GBASE_ACCOUNTS"] += f",vixen:{self.tmp / 'acct' / 'b'}"
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--account", "b")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["account"], (Path(result["run_dir"]) / "ran-on").read_text().split()), ("b", ["b"]))
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--account", "vixen")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["account"], "b")  # the alias runs as the first name on its config dir
        self.assertIn("계정 b", self.run_cli("cite", result["run_id"])[1][0])
        # an account that's down still hands the run on
        self.accounts(a=[], b=["logged-out-run"])
        self.env["GBASE_ACCOUNTS"] += f",vixen:{self.tmp / 'acct' / 'b'}"
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--account", "vixen")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((result["account"], [f["account"] for f in result["failures"]]), ("a", ["b"]))
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--account", "nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--account nope is not in the accounts list (a, b, vixen", r.stderr)
        # no list: the recipe's --account still runs, as default
        self.env.pop("GBASE_ACCOUNTS")
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--account", "c5")
        self.assertEqual((r.returncode, json.loads(Path(out[-1]).read_text())["account"]), (0, "default"), r.stderr)
        self.assertIn("--account c5 ignored: no accounts list", r.stderr)

    def test_notify_runs_once_per_run_and_its_failure_keeps_the_status(self):
        calls = self.tmp / "notified"
        script = self.tmp / "notify.sh"
        script.write_text(f'#!/bin/sh\nshift\necho "$@" >> {calls}\n')
        script.chmod(0o755)
        self.env["GBASE_NOTIFY_CMD"] = f"{script} --key=SECRETKEY"  # a key the command carries stays out of records
        self.accounts(a=[])
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship")
        ok = json.loads(Path(out[-1]).read_text())
        self.accounts(a=["logged-out"])
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship")
        failed = json.loads(Path(out[-1]).read_text())
        self.assertEqual((ok["status"], ok["notify"], failed["status"], failed["notify"]), ("done", "ok", "failed", "ok"))
        self.assertEqual(calls.read_text().splitlines(), [f"{ok['run_id']} done 0 {out[-1].replace(failed['run_id'], ok['run_id'])}",
                                                          f"{failed['run_id']} failed 1 {out[-1]}"])
        for run in (ok, failed):
            for f in Path(run["run_dir"]).iterdir():
                self.assertNotIn("SECRETKEY", f.read_text(), f)
        self.assertNotIn("SECRETKEY", r.stderr + r.stdout)
        # a notify command that fails, given on the command line: the run is still done
        self.accounts(a=[])
        r, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--notify-cmd", "false")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual((r.returncode, result["status"], result["notify"]), (0, "done", "failed"))
        self.assertIn("notify command failed (exit 1)", r.stderr)
        self.assertEqual(len(calls.read_text().splitlines()), 2)  # --notify-cmd replaced GBASE_NOTIFY_CMD

    def test_doctor_reports_accounts_gc_and_worktrees(self):
        r, _ = self.run_cli("doctor")
        report = json.loads(r.stdout)
        self.assertEqual((r.returncode, report["accounts_source"], report["gc_last"]), (1, None, None))
        self.assertTrue(any("계정 목록 없음" in p for p in report["problems"]))
        self.assertTrue(any("gc 기록 없음" in p for p in report["problems"]))
        self.accounts(a=[], b=["logged-out"])
        self.env["GBASE_ACCOUNTS"] += f",vixen:{self.tmp / 'acct' / 'a'},gone:{self.tmp / 'acct' / 'nope'}"
        self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "w1")
        self.run_cli("gc", "--older-than", "3d", "--dry-run")
        r, _ = self.run_cli("doctor")
        report = json.loads(r.stdout)
        self.assertEqual([(a["name"], a["ok"], a["aliases"]) for a in report["accounts"]],
                         [("a", True, ["vixen"]), ("b", False, []), ("gone", False, [])])
        self.assertIn("auth", report["accounts"][1]["problem"])
        self.assertEqual(report["accounts"][2]["problem"], "config dir 없음")
        self.assertEqual((report["gc_last"], report["gc_dry_run_last"]["keep"]), (None, 1))
        self.assertEqual(report["worktrees"]["count"], 1)
        self.assertGreater(report["worktrees"]["size_kb"], 0)
        self.accounts(a=[])
        self.run_cli("gc", "--older-than", "3d")
        r, _ = self.run_cli("doctor")
        report = json.loads(r.stdout)
        self.assertEqual((r.returncode, report["problems"], report["gc_last"]["keep"]), (0, [], 1))
        # a gc that stopped, and a claude binary that's gone (preflight alone would call every account ok)
        (Path(self.env["GBASE_HOME"]) / "gc-last.json").write_text('{"at": "2026-01-01T00:00:00+0900"}')
        self.env["GBASE_CLAUDE"] = str(self.tmp / "no-claude")
        r, _ = self.run_cli("doctor")
        problems = json.loads(r.stdout)["problems"]
        self.assertEqual(r.returncode, 1)
        self.assertTrue(any("마지막 gc가 2026-01-01" in p for p in problems), problems)
        self.assertTrue(any("claude 실행 파일 없음" in p for p in problems), problems)

    def test_preflight_is_cached(self):
        self.accounts(a=[])
        self.env["GBASE_PREFLIGHT_TTL"] = "300"
        for _ in range(2):
            self.run_cli("--repo", str(self.repo), "--slot", "ship")
        self.assertEqual((self.tmp / "acct" / "a" / "preflights").read_text(), "x")

    def test_without_origin_the_base_is_the_checked_out_branch_and_land_brings_the_commit(self):
        self.g("checkout", "-q", "-b", "feat/feedback")
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "fb", "--model", "commits")
        result = json.loads(Path(out[-1]).read_text())
        self.assertEqual(result["base"], {"ref": "feat/feedback", "ahead": 1, "behind": 0})
        self.assertEqual(result["landed"], {"ref": "feat/feedback", "contains_head": False})
        self.assertEqual(result["next"], f"커밋 {result['head_sha'][:7]}는 gbase/fb에만 있음. feat/feedback에 넣으려면 "
                                         f"`gbase-run land {result['run_id']}`")
        self.assertEqual(out[-2], f"next: {result['next']}")
        r, out = self.run_cli("land", result["run_id"])
        self.assertEqual((r.returncode, json.loads(out[-1])["method"]), (0, "fast-forward"), r.stderr)
        self.assertEqual(self.g("rev-parse", "HEAD"), result["head_sha"])
        self.assertEqual(self.g("status", "--porcelain"), "")  # the checked-out branch moved with its files
        landed = json.loads(self.run_cli("status", result["run_id"])[0].stdout)
        self.assertEqual((landed["landed"]["contains_head"], landed["next"]), (True, None))
        # the branch moved on meanwhile: the run's commit is cherry-picked
        self.env["FAKE_CONTENT"] = "second"
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "fb", "--model", "commits")
        second = json.loads(Path(out[-1]).read_text())
        self.g("commit", "-q", "--allow-empty", "-m", "elsewhere")
        r, out = self.run_cli("land", second["run_id"])
        self.assertEqual((r.returncode, json.loads(out[-1])["method"]), (0, "cherry-pick"), r.stderr)
        self.assertEqual((self.repo / "c.txt").read_text(), "second\n")
        # a later run on the same worktree: the commit landed by cherry-pick isn't picked again
        self.env["FAKE_CONTENT"] = "second-b"
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "fb", "--model", "commits")
        r, out = self.run_cli("land", json.loads(Path(out[-1]).read_text())["run_id"])
        self.assertEqual((r.returncode, json.loads(out[-1])["method"]), (0, "cherry-pick"), r.stderr)
        self.assertEqual((self.repo / "c.txt").read_text(), "second-b\n")
        # a conflict stops it with the branch where it was
        self.env["FAKE_CONTENT"] = "third"
        _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", "fb", "--model", "commits")
        third = json.loads(Path(out[-1]).read_text())
        (self.repo / "c.txt").write_text("mine\n")
        self.g("commit", "-qam", "mine")
        tip = self.g("rev-parse", "HEAD")
        r, _ = self.run_cli("land", third["run_id"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("conflict", r.stderr)
        self.assertEqual((self.g("rev-parse", "HEAD"), self.g("status", "--porcelain")), (tip, ""))
        self.assertEqual(self.g("worktree", "list").count("\n"), 1)  # the scratch worktree is gone

    def test_gc_removes_landed_worktrees_and_keeps_dirty_or_unlanded_ones(self):
        runs = {}
        for name, model in [("merged", "commits"), ("empty", None), ("dirty", None), ("open", "commits"),
                            ("open-pr42", "commits")]:
            self.env["FAKE_CONTENT"] = name
            _, out = self.run_cli("--repo", str(self.repo), "--slot", "ship", "--worktree", name,
                                  *(("--model", model) if model else ()))
            runs[name] = json.loads(Path(out[-1]).read_text())
        self.g("merge", "-q", "--ff-only", "gbase/merged")
        (Path(runs["dirty"]["cwd"]) / "notes.txt").write_text("wip")
        r, out = self.run_cli("gc", "--older-than", "3d")
        self.assertTrue(all(json.loads(line)["action"] == "keep" for line in out), out)  # all younger than 3 days
        r, out = self.run_cli("gc", "--older-than", "0m", "--dry-run")
        planned = {Path(json.loads(line)["path"]).name.rsplit("-", 1)[-1]: json.loads(line)["action"] for line in out}
        self.assertEqual(planned, {"merged": "would remove", "empty": "would remove", "dirty": "keep", "open": "keep",
                                   "pr42": "keep"})  # a name ending in -pr<N> isn't an ended PR by itself
        self.assertTrue(Path(runs["merged"]["cwd"]).exists())
        r, out = self.run_cli("gc", "--older-than", "0m")
        self.assertEqual(r.returncode, 0, r.stderr)
        gone = {name: not Path(run["cwd"]).exists() for name, run in runs.items()}
        self.assertEqual(gone, {"merged": True, "empty": True, "dirty": False, "open": False, "open-pr42": False})
        self.assertNotEqual(self.g("branch", "--list", "gbase/merged"), "")  # branches stay

    def test_gc_removes_old_backup_refs_and_keeps_recent_ones(self):
        self.run_cli("--repo", str(self.repo), "--slot", "ship")  # gc looks only at repos a run used
        head = self.g("rev-parse", "HEAD")
        self.g("update-ref", "refs/gbase/backup/20261101-000000-1", head)
        lines = lambda out: [json.loads(line) for line in out if '"ref"' in line]
        _, out = self.run_cli("gc")  # the commit is seconds old: kept under the 14-day default
        self.assertEqual(lines(out), [])
        _, out = self.run_cli("gc", "--backups-older-than", "0m", "--dry-run")
        self.assertEqual([(l["ref"], l["action"]) for l in lines(out)],
                         [("refs/gbase/backup/20261101-000000-1", "would remove")])
        self.assertNotEqual(self.g("for-each-ref", "refs/gbase/backup"), "")
        _, out = self.run_cli("gc", "--backups-older-than", "0m")
        self.assertEqual(lines(out)[0]["action"], "remove")
        self.assertEqual(self.g("for-each-ref", "refs/gbase/backup"), "")
        self.assertEqual(json.loads((self.tmp / "home" / "gc-last.json").read_text())["backups remove"], 1)

    def test_status_reports_dead_runner(self):
        run = Path(self.env["GBASE_HOME"]) / "runs" / "r1"
        run.mkdir(parents=True)
        (run / "result.json").write_text(json.dumps({"run_id": "r1", "status": "running", "pid": 999999}))
        self.assertEqual(json.loads(self.run_cli("status", "r1")[0].stdout)["status"], "dead")


if __name__ == "__main__":
    unittest.main()
