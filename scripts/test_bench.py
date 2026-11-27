import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

BENCH = Path(__file__).resolve().parent / "bench" / "run"
_loader = importlib.machinery.SourceFileLoader("bench_run", str(BENCH))
bench = importlib.util.module_from_spec(importlib.util.spec_from_loader("bench_run", _loader))
_loader.exec_module(bench)

FAKE_RUNNER = textwrap.dedent('''\
    import json, os, subprocess, sys
    args = sys.argv[1:]
    repo = args[args.index("--repo") + 1]
    assert os.environ["GBASE_HOME"].endswith("home") and "AGENT_HEADLESS" not in os.environ
    assert args[args.index("--slot") + 1] == "work" and "--max-budget-usd" in args
    readme = os.path.join(repo, "README.md")
    if os.path.exists(readme) and not os.environ.get("FAKE_BREAK"):
        text = open(readme).read()
        open(readme, "w").write(text.replace("Instalation", "Installation"))
    subprocess.run(["gh", "pr", "create"], capture_output=True)
    run_dir = os.path.join(os.environ["GBASE_HOME"], "runs", "r1")
    os.makedirs(run_dir)
    result = {"run_id": "r1", "status": "done", "cwd": repo, "duration_s": 100 + 20 * ("-2" in repo),
              "ship": "ship: local main @abc1234 — 1 commits, not pushed", "risk": "low", "budget_limit": None,
              "skills": [] if os.environ.get("FAKE_NO_GO") else ["gbase:work", "gbase:go"],
              "tokens": {"fresh": 10, "cache_read": 100, "output": 5 + 5 * ("-2" in repo)},
              "sessions": {"opus": {"cost_usd": 0.5}, "haiku": {"cost_usd": 0.25}}}
    result.update(json.loads(os.environ.get("FAKE_RESULT") or "{}"))
    if os.environ.get("FAKE_SLEEP"):
        import signal, time
        def stop(*_):
            open(os.environ["FAKE_STOPPED"], "w").write("SIGTERM")
            sys.exit(143)
        signal.signal(signal.SIGTERM, stop)
        time.sleep(float(os.environ["FAKE_SLEEP"]))
    path = os.path.join(run_dir, "result.json")
    json.dump(result, open(path, "w"))
    print(path)
''')


class Bench(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / "out"
        fake = Path(tmp.name) / "fake-runner"
        fake.write_text(FAKE_RUNNER, encoding="utf-8")
        self.old_runner, bench.RUNNER = bench.RUNNER, fake
        self.addCleanup(lambda: setattr(bench, "RUNNER", self.old_runner))
        os.environ["AGENT_HEADLESS"] = "1"
        self.addCleanup(os.environ.pop, "AGENT_HEADLESS", None)

    def test_low_twice_writes_runs_p50_and_the_noise(self):
        self.assertEqual(bench.main(["--out", str(self.out), "--task", "low", "--runs", "2"]), 0)
        data = json.loads((self.out / "bench.json").read_text())
        low = data["tasks"]["low"]
        self.assertEqual((low["runs"], low["passed"], low["pass"]), (2, 2, True))
        self.assertEqual((low["seconds"], low["seconds_range"], low["cost_usd"]), (110, 20, 0.75))
        self.assertEqual(low["tokens"], {"fresh": 10, "cache_read": 100, "output": 7.5})
        run = data["runs"][0]
        self.assertEqual(low["risk"], "low")
        self.assertEqual(run["checks"], {"go ran": True, "ship: local": True, "within budget": True, "typo fixed": True})
        self.assertEqual(run["gh_calls"], 1, "the fake gh records what the run asked of it")
        self.assertEqual(data["spent_usd"], 1.5)
        self.assertIn("Instalation", (bench.FIXTURES / "low" / "README.md").read_text())

    def test_a_failed_check_fails_the_run(self):
        os.environ["FAKE_BREAK"] = "1"
        self.addCleanup(os.environ.pop, "FAKE_BREAK", None)
        self.assertEqual(bench.main(["--out", str(self.out), "--task", "low"]), 1)
        run = json.loads((self.out / "bench.json").read_text())["runs"][0]
        self.assertEqual((run["pass"], run["checks"]["typo fixed"]), (False, False))

    def test_a_run_that_skipped_go_fails(self):
        os.environ["FAKE_NO_GO"] = "1"
        self.addCleanup(os.environ.pop, "FAKE_NO_GO", None)
        self.assertEqual(bench.main(["--out", str(self.out), "--task", "low"]), 1)
        run = json.loads((self.out / "bench.json").read_text())["runs"][0]
        self.assertEqual((run["pass"], run["checks"]["go ran"]), (False, False))

    def test_with_adds_earlier_runs_to_the_summary_not_the_spend(self):
        earlier = self.out.parent / "earlier.json"
        earlier.write_text(json.dumps({"runs": [{"task": "low", "n": 1, "pass": True, "seconds": 60,
                                                 "cost_usd": 2.0, "tokens": None, "risk": "medium"}]}))
        self.assertEqual(bench.main(["--out", str(self.out), "--task", "low", "--runs", "2",
                                     "--with", str(earlier)]), 0)
        data = json.loads((self.out / "bench.json").read_text())
        low = data["tasks"]["low"]
        self.assertEqual((low["runs"], low["seconds"], low["seconds_range"]), (3, 100, 60))
        self.assertEqual((low["risk"], low["risks"]), ("low", {"medium": 1, "low": 2}))
        self.assertEqual([r["n"] for r in data["runs"]], [1, 2, 3], "a top-up numbers after the earlier runs")
        self.assertEqual(data["spent_usd"], 1.5)

    def env(self, **kw):
        for k, v in kw.items():
            os.environ[k] = v
            self.addCleanup(os.environ.pop, k, None)

    def test_a_run_that_hit_its_cost_cap_fails(self):
        self.env(FAKE_RESULT='{"budget_limit": 2.0}')
        self.assertEqual(bench.main(["--out", str(self.out), "--task", "low"]), 1)
        run = json.loads((self.out / "bench.json").read_text())["runs"][0]
        self.assertEqual((run["pass"], run["checks"]["within budget"]), (False, False))

    def test_a_run_past_the_timeout_gets_sigterm_and_fails(self):
        stopped = self.out.parent / "stopped"
        self.env(FAKE_SLEEP="30", FAKE_STOPPED=str(stopped))
        self.assertEqual(bench.main(["--out", str(self.out), "--task", "low", "--run-timeout", "1"]), 1)
        run = json.loads((self.out / "bench.json").read_text())["runs"][0]
        self.assertFalse(run["pass"])
        self.assertIn("stopped after 1s", run["error"])
        self.assertEqual(stopped.read_text(), "SIGTERM", "gbase-run needs SIGTERM to end the claude groups it started")

    def test_tokens_are_the_main_session_count(self):
        self.env(FAKE_RESULT='{"tokens": {"fresh": 10, "cache_read": 100, "output": 5, '
                            '"subagent": {"fresh": 4, "cache_read": 40, "output": 2}}}')
        self.assertEqual(bench.main(["--out", str(self.out), "--task", "low"]), 0)
        low = json.loads((self.out / "bench.json").read_text())["tasks"]["low"]
        self.assertEqual(low["tokens"], {"fresh": 6, "cache_read": 60, "output": 3})

    def test_end_state_checks_of_high_headless_and_ui(self):
        def check(task, label, result, cwd=""):
            return dict(bench.TASKS[task]["checks"])[label](result, cwd)
        self.assertTrue(check("high", "risk high", {"risk": "high"}))
        self.assertFalse(check("high", "risk high", {"risk": "medium"}))
        self.assertTrue(check("headless", "second slice left", {"followups": ["SQLite 로 옮기기"]}))
        self.assertFalse(check("headless", "second slice left", {"followups": []}))
        self.assertTrue(check("ui", "design-taste loaded", {"skills": ["gbase:work", "gbase:design-taste"]}))
        self.assertFalse(check("ui", "design-taste loaded", {"skills": ["gbase:work"]}))
        repo = bench.scratch_repo("ui", self.out)
        self.assertFalse(check("ui", "screen changed", {}, repo))
        (repo / "index.html").write_text("<p>할 일이 없어요</p>\n")
        self.assertTrue(check("ui", "screen changed", {}, repo))

    def test_a_run_whose_cap_would_pass_the_total_is_skipped(self):
        self.assertEqual(bench.main(["--out", str(self.out), "--task", "low", "--task", "high",
                                     "--max-total-usd", "4"]), 1)
        data = json.loads((self.out / "bench.json").read_text())
        self.assertEqual((list(data["tasks"]), data["skipped"]), (["low"], ["high-1"]))

    def test_hidden_tests_judge_the_fixture_as_shipped(self):
        repo = bench.scratch_repo("high", self.out)
        self.assertFalse(bench.run_tests(repo, bench.HIGH_HIDDEN), "the fixture's bug fails the hidden tests")
        self.assertFalse((repo / "tests" / "test_bench_hidden.py").exists())
        (repo / "src" / "retry.py").write_text(textwrap.dedent('''\
            def call_with_retry(fn, attempts=3, delay=0.0):
                for i in range(attempts):
                    try:
                        return fn()
                    except TimeoutError:
                        if i == attempts - 1:
                            raise
        '''))
        self.assertTrue(bench.run_tests(repo, bench.HIGH_HIDDEN))

    def test_medium_fixture_fails_its_hidden_tests(self):
        repo = bench.scratch_repo("medium", self.out)
        self.assertFalse(bench.run_tests(repo, bench.MEDIUM_HIDDEN))
        (repo / "src" / "pricing.py").write_text('def line_total(item):\n    return item["price"] * item.get("qty", 1)\n')
        self.assertTrue(bench.run_tests(repo, bench.MEDIUM_HIDDEN))



GIT_ENV = {"GIT_AUTHOR_NAME": "Dev", "GIT_AUTHOR_EMAIL": "dev@localhost",
           "GIT_COMMITTER_NAME": "Dev", "GIT_COMMITTER_EMAIL": "dev@localhost"}


def edit(repo, rel, old, new):
    path = repo / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, (rel, old)
    path.write_text(text.replace(old, new), encoding="utf-8")


class HardTasks(unittest.TestCase):
    def grade(self, task, fix=None):
        with tempfile.TemporaryDirectory() as tmp:
            repo = bench.scratch_repo(task, Path(tmp))
            if fix:
                fix(repo)
            return {label: bool(fn({}, repo)) for label, fn in bench.TASKS[task]["checks"]}

    def assert_trap(self, task, right, *wrongs):
        self.assertFalse(all(self.grade(task).values()), f"{task}: the untouched fixture passes")
        for wrong in wrongs:
            self.assertFalse(all(self.grade(task, wrong).values()), f"{task}: {wrong.__name__} passes")
        self.assertEqual(set(self.grade(task, right).values()), {True}, f"{task}: the right fix fails")

    def test_rootcause_symptom_patch_in_the_report_fails(self):
        def wrong(repo):
            edit(repo, "src/report.py", 'row.get("region")', 'row.get("region") or row.get("\\ufeffregion")')
        def one_reader(repo):
            edit(repo, "src/csvio.py", 'encoding="utf-8"', 'encoding="utf-8-sig"')
        def right(repo):
            one_reader(repo)
            edit(repo, "src/targets.py", 'encoding="utf-8"', 'encoding="utf-8-sig"')
        self.assert_trap("rootcause", right, wrong, one_reader)

    def test_blast_lowercasing_alone_locks_out_stored_users(self):
        def wrong(repo):
            edit(repo, "src/users.py", "email.strip()", "email.strip().lower()")
        def right(repo):
            wrong(repo)
            edit(repo, "src/store.py", "self.users = json.load(f)",
                 "self.users = {k.strip().lower(): v for k, v in json.load(f).items()}")
        self.assert_trap("blast", right, wrong)

    def test_mirror_divmod_fix_gets_refunds_and_bad_n_wrong(self):
        def wrong(repo):
            edit(repo, "src/split.py", "    share = total_cents // n\n    return [share] * n",
                 "    share, extra = divmod(total_cents, n)\n    return [share + 1] * extra + [share] * (n - extra)")
        def right(repo):
            edit(repo, "src/split.py", "    share = total_cents // n\n    return [share] * n",
                 "    if not isinstance(n, int) or n <= 0:\n        raise ValueError(n)\n"
                 "    sign = -1 if total_cents < 0 else 1\n"
                 "    share, extra = divmod(abs(total_cents), n)\n"
                 "    return [sign * (share + 1)] * extra + [sign * share] * (n - extra)")
        self.assert_trap("mirror", right, wrong)

    def test_strict_needs_branch_sign_off_subject_changelog_and_the_rate_untouched(self):
        subject = "fix(billing): round VAT half up"
        def code(repo, branch="fix/vat-rounding", changelog=True):
            if branch:
                subprocess.run(["git", "-C", str(repo), "switch", "-c", branch], check=True, capture_output=True)
            edit(repo, "src/billing/tax.py", "round(amount_won * VAT_PERCENT / 100)",
                 "(amount_won * VAT_PERCENT + 50) // 100")
            if changelog:
                edit(repo, "CHANGELOG.md", "## Unreleased\n", "## Unreleased\n\n- fix(billing): 부가세 반올림\n")
        def commit(repo, *args):
            subprocess.run(["git", "-C", str(repo), "commit", "-qam", *args], check=True, env={**os.environ, **GIT_ENV})
        def on_main(repo):
            code(repo, branch=None)
            commit(repo, subject, "-s")
        def no_changelog(repo):
            code(repo, changelog=False)
            commit(repo, subject, "-s")
        def unsigned(repo):
            code(repo)
            commit(repo, subject)
        def bad_subject(repo):
            code(repo)
            commit(repo, "Fix VAT rounding", "-s")
        def rate_changed(repo):
            code(repo)
            edit(repo, "src/billing/rates.py", "10", "10.0")
            commit(repo, subject, "-s")
        def back_to_main(repo):
            subprocess.run(["git", "-C", str(repo), "switch", "-q", "main"], check=True)
        def rate_changed_then_main(repo):
            rate_changed(repo)
            back_to_main(repo)
        def right(repo):
            code(repo)
            commit(repo, subject, "-s")
        def right_then_main_with_a_backup_ref(repo):  # ship-prep's unsigned backup commit is not the run's commit
            right(repo)
            subprocess.run(["git", "-C", str(repo), "update-ref", "refs/gbase/backup/1",
                            subprocess.run(["git", "-C", str(repo), "commit-tree", "HEAD^{tree}", "-m", "backup"],
                                           capture_output=True, text=True, check=True,
                                           env={**os.environ, **GIT_ENV}).stdout.strip()], check=True)
            back_to_main(repo)
        self.assert_trap("strict", right, unsigned, bad_subject, rate_changed, on_main, no_changelog,
                         rate_changed_then_main)
        self.assertEqual(set(self.grade("strict", right_then_main_with_a_backup_ref).values()), {True})
        self.assertFalse(self.grade("strict", code)["commits follow CONTRIBUTING"], "no commit at all fails")

    def test_hard_tasks_run_only_when_named(self):
        ran = []
        old, bench.run_one = bench.run_one, lambda task, n, out, timeout: ran.append(task) or {
            "task": task, "n": n, "pass": True, "cost_usd": 0.0}
        self.addCleanup(setattr, bench, "run_one", old)
        with tempfile.TemporaryDirectory() as tmp:
            bench.main(["--out", tmp])
            self.assertEqual(ran, ["low", "medium", "high", "headless", "ui"])
            ran.clear()
            bench.main(["--out", tmp, "--task", "blast"])
            self.assertEqual(ran, ["blast"])


if __name__ == "__main__":
    unittest.main()
