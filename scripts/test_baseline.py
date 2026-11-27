import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from shutil import rmtree
from pathlib import Path

spec = importlib.util.spec_from_file_location("baseline", Path(__file__).with_name("baseline.py"))
bl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bl)


def result_event(inp, create, read, out, cost):
    return {"type": "result", "total_cost_usd": cost,
            "usage": {"input_tokens": inp, "cache_creation_input_tokens": create, "cache_read_input_tokens": read, "output_tokens": out}}


def case(name, score, runs, per_case=3):
    return {"name": name, "runsPerCase": per_case, "aggregates": {"passRate": score, "score": score}, "arms": {"with": runs}}


class Runs(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def run_dir(self, name, result, logs=None):
        d = self.root / name
        d.mkdir()
        (d / "result.json").write_text(json.dumps(result), encoding="utf-8")
        for log, events in (logs or {}).items():
            (d / log).write_text("\n".join(json.dumps(e) for e in events) + "\nnot json\n", encoding="utf-8")
        return d

    def test_tokens_sum_every_result_event_across_logs(self):
        d = self.run_dir("r1", {"slot": "work", "status": "done"}, {
            "log.jsonl": [{"type": "assistant"}, result_event(10, 100, 1000, 5, 1.0), result_event(2, 20, 200, 1, 1.0)],
            "log-sonnet.jsonl": [result_event(1, 1, 1, 1, 0.1)],
        })
        self.assertEqual(bl.log_tokens(d), {"fresh": 134, "cache_read": 1201, "output": 7})

    def test_no_result_event_is_none_not_zero(self):
        d = self.run_dir("r1", {"slot": "work", "status": "failed"}, {"log.jsonl": [{"type": "assistant"}]})
        self.assertIsNone(bl.log_tokens(d))

    def test_trend_counts_all_runs_but_measures_done_ones(self):
        common = {"slot": "work", "started_at": "2026-11-01T10:00:00+0900"}
        self.run_dir("a", {**common, "status": "done", "finished_at": "2026-11-01T10:10:00+0900",
                           "sessions": {"opus": {"cost_usd": 2.0, "turns": 40}, "sonnet": {"cost_usd": 1.0, "turns": None}},
                           "gaps": ["x"], "unverified": []},
                     {"log.jsonl": [result_event(1, 9, 100, 10, 3.0)]})
        self.run_dir("old-no-turns", {**common, "status": "done", "finished_at": "2026-11-01T10:30:00+0900",
                                      "sessions": {"opus": {"cost_usd": 4.0}}, "gaps": [], "unverified": ["y"]},
                                {"log.jsonl": [result_event(1, 19, 300, 30, 4.0)]})
        self.run_dir("c", {**common, "status": "failed", "finished_at": "2026-11-01T10:01:00+0900",
                           "sessions": {"opus": {"cost_usd": 0.5, "turns": 3}}})
        self.run_dir("d", {**common, "status": "running", "finished_at": None})
        self.run_dir("e", {"slot": "review", "status": "done", "started_at": "bad", "finished_at": None})
        (self.root / "broken").mkdir()
        (self.root / "broken" / "result.json").write_text("{", encoding="utf-8")

        t = bl.trend(self.root)
        work = t["work"]
        self.assertEqual((work["n"], work["failed"], work["done"]), (4, 1, 2))
        self.assertEqual((work["minutes_p50"], work["minutes_p90"]), (20.0, 30.0))
        self.assertEqual(work["turns_p50"], 40)
        self.assertEqual((work["cost_p50"], work["cost_p90"]), (3.5, 4.0))
        self.assertEqual(work["tokens_p50"], {"fresh": 15.0, "cache_read": 200.0, "output": 20.0})
        self.assertEqual((work["gaps_rate"], work["unverified_rate"]), (0.5, 0.5))
        self.assertEqual(t["review"]["minutes_p50"], None)
        self.assertIsNone(t["review"]["tokens_p50"])


class Eval(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write_json(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def test_summary_from_eval_json(self):
        data = {"costUsd": 1.5, "durationSeconds": 90, "partial": False, "suite": {"threshold": 0.67},
                "aggregates": {"casesTotal": 2, "casesPassed": 1, "overallPassRate": 0.5},
                "cases": [
                    {"name": "a", "aggregates": {"passRate": 1, "score": 1},
                     "arms": {"with": [{"durationSeconds": 10, "costUsd": 0.2, "turns": 5, "error": None},
                                       {"durationSeconds": 30, "costUsd": 0.4, "turns": 7, "error": None}]}},
                    {"name": "b", "aggregates": {"passRate": 0, "score": 0},
                     "arms": {"with": [{"durationSeconds": 20, "costUsd": 0.3, "turns": None, "error": "timeout"}]}},
                ]}
        s = bl.eval_summary([self.write_json("eval.json", data)])
        self.assertEqual(s["cases"]["b"], {"pass": 0, "score": 0, "runs": 1, "errors": 1, "complete": True})
        self.assertEqual((s["passed"], s["total"], s["threshold"], s["cost_usd"], s["seconds"]), (1, 2, 0.67, 1.5, 90))
        self.assertEqual(s["speed"], {"seconds_p50": 20, "cost_p50": 0.3, "turns_p50": 6.0})
        self.assertIsNone(s["tokens"], "the eval JSON carries no token counts; say so instead of reporting 0")

    def test_partial_run_lists_unrun_cases_instead_of_failing_them(self):
        ok = {"durationSeconds": 10, "costUsd": 0.1, "turns": 3}
        root = self.root
        for name in ("ran", "short", "never", "ungraded", "skipped-by-cap", "other-filter"):
            (root / "evals" / name).mkdir(parents=True)
            (root / "evals" / name / "case.yaml").write_text("", encoding="utf-8")
        (root / "evals" / "results").mkdir()
        data = {"partial": True, "suite": {"root": str(root), "caseFilter": None},
                "aggregates": {"casesTotal": 4, "casesPassed": 1},
                "cases": [case("ran", 1, [ok, ok, ok]),
                          case("short", 1, [ok]),
                          case("never", 0, []),
                          case("ungraded", 1, [ok, ok, {**ok, "skippedPaidGraders": True}])]}
        s = bl.eval_summary([self.write_json("eval.json", data)])
        self.assertTrue(s["partial"])
        self.assertEqual(s["incomplete"], ["never", "short", "ungraded"])
        self.assertEqual(s["all_runs_passed"], 1)
        self.assertEqual(s["not_run"], ["other-filter", "skipped-by-cap"], "results/ has no case file, so it isn't a case")
        data["suite"]["caseFilter"] = "*-by-cap"
        self.assertEqual(bl.eval_summary([self.write_json("eval.json", data)])["not_run"], ["skipped-by-cap"])

    def test_rerun_merges_by_case_and_adds_cost(self):
        root = self.root
        for name in ("a", "b", "c"):
            (root / "evals" / name).mkdir(parents=True)
            (root / "evals" / name / "prompt.md").write_text("", encoding="utf-8")
        ok, fail = {"durationSeconds": 10, "costUsd": 1.0, "turns": 2}, {"durationSeconds": 50, "costUsd": 3.0, "turns": 9}
        first = {"partial": True, "costUsd": 40.0, "durationSeconds": 100, "suite": {"root": str(root), "threshold": 0.67},
                 "cases": [case("a", 1, [ok, ok, ok]), case("b", 0, [fail, fail])]}
        rerun = {"partial": False, "costUsd": 5.0, "durationSeconds": 30, "suite": {"root": str(root), "threshold": 0.67},
                 "cases": [case("b", 1, [ok, ok, ok])]}
        paths = [self.write_json("eval.json", first), self.write_json("eval2.json", rerun)]
        s = bl.eval_summary(paths)
        self.assertEqual(s["cases"]["b"]["runs"], 3, "the rerun's case replaces the cut-off one")
        self.assertEqual((s["passed"], s["total"], s["suite_total"], s["not_run"], s["incomplete"]), (2, 2, 3, ["c"], []))
        self.assertEqual((s["cost_usd"], s["seconds"], s["files"], s["partial"]), (45.0, 130, 2, True))
        self.assertEqual(s["speed"]["cost_p50"], 1.0, "the cut-off runs of b are dropped with it")
        (root / "evals" / "c" / "prompt.md").unlink()
        self.assertFalse(bl.eval_summary(paths)["partial"], "nothing left out once the rerun covers the rest")
        self.assertEqual(bl.eval_summary(paths[:1])["passed"], 1, "a case passes at the threshold, as the eval counts it")
        rmtree(root / "evals")
        self.assertFalse(bl.eval_summary(paths)["partial"], "with the suite folder gone, the last file's flag decides, not the capped first one")

    def test_each_case_meets_its_own_files_threshold(self):
        first = {"suite": {"threshold": 0.67}, "cases": [case("partly", 0.67, [{}] * 3)]}
        rerun = {"suite": {}, "cases": [case("strict", 0.8, [{}] * 3)]}  # no --threshold: the eval's default of 1.0
        s = bl.eval_summary([self.write_json("a.json", first), self.write_json("b.json", rerun)])
        self.assertEqual((s["passed"], s["all_runs_passed"], s["threshold"]), (1, 0, None))

    def test_read_budget_reuses_read_budget_py(self):
        rb = bl.read_budget()
        self.assertIn("low", rb)
        self.assertIn("+headless", rb)
        self.assertTrue(all(isinstance(v, int) for v in rb.values()))


class Diff(unittest.TestCase):
    OLD = {"version": "1.0.0", "date": "2026-11-01", "eval": {"passed": 20, "total": 31, "speed": None},
           "read_budget": {"low": 1000}, "trend": {"work": {"cost_p50": 4.0, "turns_p50": None}}}
    NEW = {"version": "1.1.0", "date": "2026-11-08", "eval": {"passed": 25, "total": 31, "speed": None},
           "read_budget": {"low": 900, "medium": 50}, "trend": {"work": {"cost_p50": 4.0, "turns_p50": None}}}

    def test_same_file_changes_nothing(self):
        rows = bl.diff(self.NEW, self.NEW)
        self.assertTrue(rows)
        self.assertTrue(all(change == 0 and rate == 0 for _, _, _, change, rate in rows))

    def test_signs_rates_and_missing_sides(self):
        rows = {key: (x, y, change, rate) for key, x, y, change, rate in bl.diff(self.OLD, self.NEW)}
        self.assertEqual(rows["eval.passed"], (20, 25, 5, 25.0))
        self.assertEqual(rows["read_budget.low"], (1000, 900, -100, -10.0))
        self.assertEqual(rows["read_budget.medium"], (None, 50, None, None))
        self.assertNotIn("trend.work.turns_p50", rows, "a metric neither side has is not a row")
        self.assertNotIn("version", rows)

    def test_printed_table(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            bl.print_diff(self.OLD, self.NEW)
        out = buf.getvalue()
        self.assertIn("| metric | 1.0.0 (2026-11-01) | 1.1.0 (2026-11-08) | change | % |", out)
        self.assertIn("| read_budget.low | 1,000 | 900 | -100 | -10.0% |", out)
        self.assertIn("| eval.passed | 20 | 25 | +5 | +25.0% |", out)


if __name__ == "__main__":
    unittest.main()
