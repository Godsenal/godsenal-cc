"""monitor's pr-status: every classification and verdict, on hand-built GraphQL responses — no network."""
import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "plugins/base/skills/monitor/scripts/pr-status"
loader = importlib.machinery.SourceFileLoader("pr_status", str(PATH))
spec = importlib.util.spec_from_loader("pr_status", loader)
ps = importlib.util.module_from_spec(spec)
loader.exec_module(ps)

HEAD = "a" * 40
T0 = "2026-11-17T02:00:00Z"   # head pushed (its first check starts)
T1 = "2026-11-17T02:05:00Z"
BEFORE = "2026-11-16T00:00:00Z"
ME = "me"
USER = {"login": "alice", "__typename": "User"}
BOT = {"login": "review-bot", "__typename": "Bot"}
MINE = {"login": ME, "__typename": "User"}


def run(name="check", status="COMPLETED", conclusion="SUCCESS", required=False, app="github-actions", check_id=1):
    return {"__typename": "CheckRun", "name": name, "status": status, "conclusion": conclusion, "startedAt": T0, "databaseId": check_id,
            "detailsUrl": f"https://github.com/o/r/actions/runs/1/job/{check_id}", "isRequired": required, "checkSuite": {"app": {"slug": app}}}


def comment(author, body="text", at=T1, assoc="NONE", cid=10):
    return {"databaseId": cid, "author": author, "authorAssociation": assoc, "body": body, "createdAt": at, "updatedAt": at, "url": f"u{cid}"}


def thread(*comments, resolved=False):
    return {"isResolved": resolved, "isOutdated": False, "path": "src/a.ts", "line": 7, "comments": {"nodes": list(comments)}}


def review(author, state, body="", at=T1, oid=HEAD, assoc="NONE", rid=20):
    return {"databaseId": rid, "author": author, "authorAssociation": assoc, "state": state, "body": body, "submittedAt": at,
            "commit": {"oid": oid}, "url": f"r{rid}"}


def data(checks=(), threads=(), reviews=(), comments=(), requests=(), merged_bots=(), head_author=ME, **pr):
    return {"repository": {
        "pullRequest": {"number": 7, "url": "https://github.com/o/r/pull/7", "state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE",
                        "mergeStateStatus": "CLEAN", "reviewDecision": None, "baseRefName": "main", "headRefName": "feat/x", "headRefOid": HEAD,
                        "commits": {"nodes": [{"commit": {"author": {"user": {"login": head_author}},
                                                           "statusCheckRollup": {"contexts": {"nodes": list(checks)}}}}]},
                        "reviewThreads": {"nodes": list(threads)}, "reviews": {"nodes": list(reviews)},
                        "comments": {"nodes": list(comments)},
                        "reviewRequests": {"nodes": [{"requestedReviewer": r} for r in requests]}, **pr},
        "pullRequests": {"nodes": [{"reviews": {"nodes": [{"author": b} for b in merged_bots]}}]}}}


def snap(**kw):
    annotations = kw.pop("annotations", lambda check_id: ())
    polls = kw.pop("polls", ())
    return ps.normalize(data(**kw), ME, annotations, polls)


def decide(s, waited=600, pushed=0, settle_rules=True):
    first_seen = ps.epoch(T0)
    return ps.decide(s, first_seen, first_seen + waited, pushed, settle_rules)


class Time(unittest.TestCase):
    def test_github_timestamps_are_read_as_utc_whatever_the_local_zone(self):
        self.assertEqual(ps.epoch("1970-01-02T00:00:00Z"), 86400)
        self.assertEqual(ps.epoch("2026-07-01T12:00:00Z") - ps.epoch("2026-01-01T12:00:00Z"), 181 * 86400)
        self.assertEqual(ps.epoch(None), 0)


class CheckKinds(unittest.TestCase):
    def test_check_run_states(self):
        cases = {("IN_PROGRESS", None): "pending", ("QUEUED", None): "pending", ("COMPLETED", "SUCCESS"): "passed",
                 ("COMPLETED", "NEUTRAL"): "passed", ("COMPLETED", "SKIPPED"): "skipped", ("COMPLETED", "FAILURE"): "failed",
                 ("COMPLETED", "TIMED_OUT"): "failed", ("COMPLETED", "CANCELLED"): "failed", ("COMPLETED", "STARTUP_FAILURE"): "failed"}
        for (status, conclusion), kind in cases.items():
            self.assertEqual(ps.check_kind(run(status=status, conclusion=conclusion)), kind, (status, conclusion))

    def test_status_context_states(self):
        for state, kind in {"SUCCESS": "passed", "PENDING": "pending", "EXPECTED": "pending", "FAILURE": "failed", "ERROR": "failed"}.items():
            self.assertEqual(ps.check_kind({"__typename": "StatusContext", "state": state}), kind)

    def test_a_job_the_account_could_not_start_is_not_a_diff_failure(self):
        note = "The job was not started because recent account payments have failed or your spending limit needs to be increased."
        s = snap(checks=[run(conclusion="FAILURE")], annotations=lambda check_id: [note])
        self.assertEqual(s["checks"][0]["kind"], "not-started")
        v = decide(s)
        self.assertFalse(any(n.startswith("ci") for n in v["next"]))
        self.assertIn("사람 필요", v["settle"])
        self.assertIn("CI 미실행", v["settle"])

    def test_a_failing_test_that_mentions_billing_is_a_real_failure(self):
        for note in ("billing › charges twice: expected 1 received 2", "src/billing/charge.test.ts:12:5", "raise the spending limit test"):
            s = snap(checks=[run(conclusion="FAILURE")], annotations=lambda check_id, note=note: [note])
            self.assertEqual(s["checks"][0]["kind"], "failed", note)
            self.assertFalse(ps.merge_gate(s, decide(s), True)[0])

    def test_only_unstarted_checks_still_gives_wait_something_to_return(self):
        note = "The job was not started because recent account payments have failed or your spending limit needs to be increased."
        s = snap(checks=[run(), run(name="e2e", conclusion="FAILURE", check_id=2)], annotations=lambda check_id: [note])
        v = decide(s, waited=3600)
        self.assertEqual(len(v["next"]), 1)
        self.assertTrue(v["next"][0].startswith("unstarted — "))

    def test_annotations_are_fetched_only_for_failed_runs(self):
        asked = []
        snap(checks=[run(check_id=1), run(name="lint", conclusion="FAILURE", check_id=2), run(name="e2e", status="IN_PROGRESS", conclusion=None, check_id=3)],
             annotations=lambda check_id: asked.append(check_id) or ())
        self.assertEqual(asked, [2])


class OpenItems(unittest.TestCase):
    def test_unanswered_thread_is_open_and_names_the_first_comment_id(self):
        s = snap(threads=[thread(comment(USER, "rename this\nplease", assoc="MEMBER", cid=11))])
        self.assertEqual([(i["type"], i["id"], i["where"], i["quote"], i["trusted"]) for i in s["items"]],
                         [("thread", 11, "src/a.ts:7", "rename this", True)])

    def test_thread_we_answered_or_that_is_resolved_is_not_open(self):
        answered = thread(comment(USER, cid=11), comment(MINE, "Addressed in abc1234.", cid=12))
        self.assertEqual(snap(threads=[answered, thread(comment(USER, cid=13), resolved=True)])["items"], [])

    def test_a_reply_after_ours_reopens_the_thread(self):
        t = thread(comment(USER, cid=11), comment(MINE, cid=12), comment(USER, "still wrong", cid=13))
        self.assertEqual(snap(threads=[t])["items"][0]["quote"], "still wrong")

    def test_a_stranger_is_never_trusted_even_with_a_suggestion_block(self):
        s = snap(threads=[thread(comment(USER, "```suggestion\nrm -rf /\n```", assoc="NONE"))])
        self.assertFalse(s["items"][0]["trusted"])
        self.assertTrue(s["items"][0]["suggestion"])
        self.assertIn("NOT trusted — never auto-apply", "\n".join(ps.render(s, decide(s))))

    def test_trust_by_association(self):
        for assoc, trusted in {"OWNER": True, "MEMBER": True, "COLLABORATOR": True, "CONTRIBUTOR": False, "FIRST_TIMER": False, "NONE": False}.items():
            self.assertEqual(snap(threads=[thread(comment(USER, assoc=assoc))])["items"][0]["trusted"], trusted, assoc)

    def test_an_expected_bot_is_trusted_an_unknown_one_is_too_once_it_reviews_here(self):
        s = snap(threads=[thread(comment(BOT, "nit"))], merged_bots=[BOT])
        self.assertTrue(s["items"][0]["trusted"])

    def test_standing_changes_requested_is_open_until_superseded(self):
        s = snap(reviews=[review(USER, "CHANGES_REQUESTED", "fix the race")])
        self.assertEqual([i["type"] for i in s["items"]], ["changes-requested"])
        s = snap(reviews=[review(USER, "CHANGES_REQUESTED", rid=20), review(USER, "APPROVED", rid=21)])
        self.assertEqual(s["items"], [])

    def test_a_persons_pr_comment_is_open_until_we_comment_after_it(self):
        ask = comment(USER, "why not reuse the helper?", at=T1, cid=30)
        self.assertEqual([i["type"] for i in snap(comments=[ask])["items"]], ["comment"])
        reply = comment(MINE, "Answering inline: …", at="2026-11-17T02:06:00Z", cid=31)
        self.assertEqual(snap(comments=[ask, reply])["items"], [])

    def test_a_comment_that_arrived_between_our_last_look_and_our_reply_is_still_open(self):
        t = ps.epoch
        early = comment(USER, "first question", at="2026-11-17T02:01:00Z", cid=30)
        late = comment(USER, "second question", at="2026-11-17T02:02:30Z", cid=31)
        reply = comment(MINE, "Answering inline: …", at="2026-11-17T02:03:00Z", cid=32)
        looked = [t("2026-11-17T02:02:00Z")]  # the snapshot our reply was written from
        self.assertEqual([i["quote"] for i in snap(comments=[early, late, reply], polls=looked)["items"]], ["second question"])
        self.assertEqual(snap(comments=[early, late, reply])["items"], [])  # no earlier snapshot in this watch: the reply covers both

    def test_a_bots_pr_level_text_is_a_note_shown_once_and_again_when_edited(self):
        finding = comment(BOT, "Found 2 issues: null deref in a.ts:10", cid=40)
        summary = review(BOT, "COMMENTED", "Reviewed 3 files, 1 comment", rid=41)
        s = snap(checks=[run()], comments=[finding], reviews=[summary])
        self.assertEqual(s["items"], [])
        self.assertEqual([n["id"] for n in s["notes"]], [40, 41])
        state = {"heads": {}, "links": []}
        self.assertEqual(len(ps.observe(state, s, 100.0)[2]), 2)
        self.assertEqual(ps.observe(state, s, 130.0)[2], [])
        edited = snap(checks=[run()], comments=[dict(finding, updatedAt="2026-11-17T03:00:00Z")], reviews=[summary])
        self.assertEqual([n["id"] for n in ps.observe(state, edited, 160.0)[2]], [40])
        v = decide(s)
        v["new_notes"] = s["notes"]
        self.assertIn("note [40] review-bot (bot): Found 2 issues: null deref in a.ts:10", "\n".join(ps.render(s, v)))

    def test_our_own_comments_are_ignored(self):
        self.assertEqual(snap(comments=[comment(MINE)])["items"], [])


class Reviewers(unittest.TestCase):
    def test_expected_bots_come_from_recent_merged_prs_this_pr_and_pending_requests(self):
        s = snap(merged_bots=[BOT], requests=[{"__typename": "Bot", "login": "copilot"}],
                 threads=[thread(comment({"login": "cursor[bot]", "__typename": "Bot"}, at=BEFORE))])
        self.assertEqual(s["expected"], ["copilot", "cursor", "review-bot"])

    def test_a_bot_that_only_comments_is_never_waited_on(self):
        s = snap(checks=[run()], comments=[comment({"login": "vercel[bot]", "__typename": "Bot"}, at=BEFORE),
                                          comment({"login": "linear[bot]", "__typename": "Bot"}, at=BEFORE, cid=11)])
        self.assertEqual(s["expected"], [])
        self.assertEqual(decide(s)["settle"], "settle: 수렴 @aaaaaaa")

    def test_people_and_github_actions_are_not_expected_reviewers(self):
        s = snap(merged_bots=[USER, {"login": "github-actions", "__typename": "Bot"}], requests=[USER])
        self.assertEqual(s["expected"], [])

    def test_a_bot_that_has_not_touched_this_head_is_waited_on(self):
        s = snap(checks=[run()], merged_bots=[BOT], reviews=[review(BOT, "COMMENTED", at=BEFORE, oid="b" * 40)])
        v = decide(s)
        self.assertEqual(v["waiting"], ["review-bot"])
        self.assertFalse(v["settled"])
        self.assertTrue(v["next"][-1].startswith("wait"))

    def test_a_review_of_the_head_finishes_the_bot(self):
        s = snap(checks=[run()], merged_bots=[BOT], reviews=[review(BOT, "COMMENTED", oid=HEAD)])
        self.assertEqual(decide(s)["waiting"], [])

    def test_a_comment_or_edit_after_the_push_finishes_the_bot(self):
        old = comment(BOT, at=BEFORE)
        edited = dict(old, updatedAt=T1)
        self.assertEqual(decide(snap(checks=[run()], comments=[old], merged_bots=[BOT]))["waiting"], ["review-bot"])
        self.assertEqual(decide(snap(checks=[run()], comments=[edited], merged_bots=[BOT]))["waiting"], [])

    def test_the_bots_own_concluded_check_finishes_it(self):
        s = snap(checks=[run(), run(name="bot review", app="review-bot", check_id=2)], merged_bots=[BOT])
        self.assertEqual(decide(s)["waiting"], [])
        s = snap(checks=[run(), run(name="bot review", app="review-bot", status="IN_PROGRESS", conclusion=None, check_id=2)], merged_bots=[BOT])
        self.assertEqual(decide(s)["waiting"], ["review-bot"])


class Verdict(unittest.TestCase):
    def test_all_green_and_nothing_open_settles(self):
        v = decide(snap(checks=[run()]))
        self.assertTrue(v["settled"])
        self.assertEqual(v["settle"], "settle: 수렴 @aaaaaaa")
        self.assertEqual(v["next"], ["settled — nothing open on this head"])

    def test_unknown_mergeability_is_never_settled(self):
        v = decide(snap(checks=[run()], mergeable="UNKNOWN", mergeStateStatus="UNKNOWN"))
        self.assertFalse(v["settled"])
        self.assertIsNone(v["settle"])
        self.assertIn("GitHub's mergeability check", v["next"][0])
        s = snap(checks=[run()], mergeable="UNKNOWN", mergeStateStatus="UNKNOWN")
        self.assertFalse(ps.merge_gate(s, v)[0])
        self.assertIn("미확정", decide(s, waited=ps.GIVE_UP_SECONDS)["settle"])

    def test_pending_check_waits_and_has_no_verdict(self):
        v = decide(snap(checks=[run(status="IN_PROGRESS", conclusion=None)]))
        self.assertIsNone(v["settle"])
        self.assertIn("still running: check", v["next"][0])

    def test_no_checks_yet_is_a_wait_only_during_the_grace_period(self):
        self.assertTrue(decide(snap(), waited=30)["next"][0].startswith("wait"))
        self.assertEqual(decide(snap(), waited=ps.CHECK_GRACE_SECONDS + 1)["settle"], "settle: 수렴 @aaaaaaa")

    def test_thirty_minutes_on_one_head_gives_up_with_what_did_not_arrive(self):
        s = snap(checks=[run(status="IN_PROGRESS", conclusion=None)], merged_bots=[BOT])
        v = decide(s, waited=ps.GIVE_UP_SECONDS)
        self.assertEqual(v["settle"], "settle: 미확정 @aaaaaaa — 안 옴: check, review-bot")
        self.assertTrue(v["next"][0].startswith("give up"))

    def test_handling_order_is_conflict_then_comments_then_ci(self):
        s = snap(checks=[run(conclusion="FAILURE")], threads=[thread(comment(USER))], mergeable="CONFLICTING")
        self.assertEqual([n.split(" — ")[0] for n in decide(s)["next"]], ["conflict", "comments", "ci"])

    def test_person_needed_wins_over_unsettled(self):
        s = snap(checks=[run(conclusion="FAILURE"), run(name="e2e", status="IN_PROGRESS", conclusion=None, check_id=2)])
        v = decide(s, waited=ps.GIVE_UP_SECONDS)
        self.assertTrue(v["settle"].startswith("settle: 사람 필요 @aaaaaaa — 실패한 체크 check"))

    def test_a_failed_check_never_settles_as_converged(self):
        v = decide(snap(checks=[run(conclusion="FAILURE")]))
        self.assertNotIn("수렴", v["settle"])
        self.assertTrue(v["next"][0].startswith("ci — check"))

    def test_after_three_pushed_heads_no_more_fixes(self):
        s = snap(checks=[run(conclusion="FAILURE")])
        self.assertFalse(decide(s, pushed=2)["next"][0].startswith("limit"))
        self.assertTrue(decide(s, pushed=3)["next"][0].startswith("limit"))
        self.assertFalse(any(n.startswith("limit") for n in decide(snap(checks=[run()]), pushed=3)["next"]))

    def test_the_settle_limits_apply_only_under_until_settled(self):
        failing = snap(checks=[run(conclusion="FAILURE")])
        self.assertFalse(any(n.startswith("limit") for n in decide(failing, pushed=5, settle_rules=False)["next"]))
        pending = snap(checks=[run(status="IN_PROGRESS", conclusion=None)])
        v = decide(pending, waited=ps.GIVE_UP_SECONDS * 3, settle_rules=False)
        self.assertTrue(v["next"][0].startswith("wait"))
        self.assertIsNone(v["settle"])

    def test_only_our_own_new_heads_count_as_pushed_fixes(self):
        state = {"heads": {}, "links": []}
        ps.observe(state, snap(), 1.0)                                              # the head the watch started on
        ps.observe(state, snap(headRefOid="b" * 40, head_author="teammate"), 2.0)   # someone else pushed
        self.assertEqual(state.get("pushed", 0), 0)
        ps.observe(state, snap(headRefOid="c" * 40), 3.0)
        ps.observe(state, snap(headRefOid="c" * 40), 4.0)                           # the same head again
        self.assertEqual(state["pushed"], 1)

    def test_merged_or_closed_pr_is_done(self):
        for state in ("MERGED", "CLOSED"):
            v = decide(snap(state=state))
            self.assertTrue(v["next"][0].startswith("done"))
            self.assertIsNone(v["settle"])


class MergeGate(unittest.TestCase):
    def gate(self, verified=False, **kw):
        s = snap(**kw)
        return ps.merge_gate(s, decide(s), verified)

    def test_green_clean_pr_passes(self):
        self.assertEqual(self.gate(checks=[run()]), (True, []))

    def test_blockers(self):
        cases = [
            (dict(checks=[run(conclusion="FAILURE")], mergeStateStatus="UNSTABLE"), "failing: check"),
            (dict(checks=[run(status="IN_PROGRESS", conclusion=None)], mergeStateStatus="UNSTABLE"), "not settled"),
            (dict(checks=[run()], mergeable="CONFLICTING", mergeStateStatus="DIRTY"), "merge conflict"),
            (dict(checks=[run()], isDraft=True, mergeStateStatus="DRAFT"), "still a draft"),
            (dict(checks=[run()], reviews=[review(USER, "CHANGES_REQUESTED")], reviewDecision="CHANGES_REQUESTED"), "CHANGES_REQUESTED"),
            (dict(checks=[run()], threads=[thread(comment(USER))]), "1 unanswered review comments"),
            (dict(checks=[run()], mergeStateStatus="BLOCKED"), "merge state BLOCKED"),
            (dict(checks=[run()], mergeStateStatus="BEHIND"), "merge state BEHIND"),
            (dict(checks=[run()], state="MERGED"), "the PR is merged"),
        ]
        for kw, reason in cases:
            ok, reasons = self.gate(**kw)
            self.assertFalse(ok, reason)
            self.assertTrue(any(reason in r for r in reasons), (reason, reasons))

    def test_a_failing_optional_check_blocks_too(self):
        checks = [run(required=True), run(name="optional", conclusion="FAILURE", check_id=2)]
        self.assertEqual(self.gate(checks=checks, mergeStateStatus="UNSTABLE"), (False, ["failing: optional"]))
        checks = [run(required=True, conclusion="FAILURE"), run(name="optional", check_id=2)]
        self.assertFalse(self.gate(checks=checks, mergeStateStatus="BLOCKED")[0])

    def test_unstable_without_an_unstarted_check_is_not_mergeable(self):
        ok, reasons = self.gate(checks=[run()], mergeStateStatus="UNSTABLE")
        self.assertEqual((ok, reasons), (False, ["merge state UNSTABLE"]))

    def test_push_triggers_are_found_in_every_yaml_form(self):
        import tempfile
        from pathlib import Path as P
        forms = {"map.yml": "on:\n  push:\n    branches: [main]\n", "scalar.yml": "on: push\n", "list.yaml": "on: [pull_request, push]\n",
                 "seq.yml": "on:\n  - push\n  - workflow_dispatch\n", "pr.yml": "on:\n  pull_request:\njobs:\n  a:\n    steps:\n      - run: git push\n",
                 "release.yml": "on:\n  release:\n    types: [published]\n"}
        with tempfile.TemporaryDirectory() as d:
            for name, text in forms.items():
                (P(d) / name).write_text(text)
            self.assertEqual(ps.push_workflows(P(d)), ["list.yaml", "map.yml", "scalar.yml", "seq.yml"])

    def test_checks_that_never_started_merge_only_when_verified_locally(self):
        note = "job was not started because recent account payments have failed"
        kw = dict(checks=[run(conclusion="FAILURE")], mergeStateStatus="UNSTABLE", annotations=lambda check_id: [note])
        ok, reasons = self.gate(**kw)
        self.assertFalse(ok)
        self.assertIn("checks never started (account) and no `verified-locally`: check", reasons)
        self.assertEqual(self.gate(verified=True, **kw), (True, []))

    def test_method_follows_recent_merges_within_what_the_repo_allows(self):
        allow_all = {"squashMergeAllowed": True, "mergeCommitAllowed": True, "rebaseMergeAllowed": True}
        self.assertEqual(ps.merge_method(allow_all, ["fix: a (#12)", "feat: b (#13)"]), "squash")
        self.assertEqual(ps.merge_method(allow_all, ["Merge pull request #12 from o/b", "Merge pull request #13 from o/c"]), "merge")
        self.assertEqual(ps.merge_method(dict(allow_all, squashMergeAllowed=False), ["fix: a (#12)"]), "merge")
        self.assertEqual(ps.merge_method({"squashMergeAllowed": False, "mergeCommitAllowed": False, "rebaseMergeAllowed": True}, []), "rebase")
        self.assertEqual(ps.merge_method(allow_all, []), "squash")


class LinksAndRender(unittest.TestCase):
    def test_testable_links_from_bots_and_checks_once_each_docs_and_logs_skipped(self):
        body = "Preview: https://app-git-x.vercel.app and https://expo.dev/preview/update?id=1 · [logs](https://github.com/o/r/actions/runs/1)"
        s = snap(checks=[run()], comments=[comment({"login": "vercel[bot]", "__typename": "Bot"}, body),
                                          comment({"login": "vercel[bot]", "__typename": "Bot"}, body, cid=11)])
        self.assertEqual([l["url"] for l in s["links"]], ["https://app-git-x.vercel.app", "https://expo.dev/preview/update?id=1"])

    def test_a_link_with_trailing_punctuation_is_the_same_link(self):
        s = snap(comments=[comment(BOT, "See https://x.pages.dev. Again: https://x.pages.dev")])
        self.assertEqual([l["url"] for l in s["links"]], ["https://x.pages.dev"])

    def test_docs_and_badge_links_are_not_something_to_try(self):
        body = "Docs https://docs.expo.dev/eas ![b](https://app.vercel.app/badge.svg) try https://expo.dev/accounts/a/builds/1"
        self.assertEqual([l["url"] for l in snap(comments=[comment(BOT, body)])["links"]], ["https://expo.dev/accounts/a/builds/1"])

    def test_a_link_is_shown_once_per_watch(self):
        s = snap(comments=[comment(BOT, "https://x.pages.dev")])
        state = {"heads": {}, "links": []}
        self.assertEqual(len(ps.observe(state, s, 100.0)[1]), 1)
        self.assertEqual(ps.observe(state, s, 130.0)[:2], (100.0, []))

    def test_a_new_head_gets_its_own_timer(self):
        state = {"heads": {}, "links": []}
        ps.observe(state, snap(), 100.0)
        other = snap(headRefOid="c" * 40)
        self.assertEqual(ps.observe(state, other, 500.0)[0], 500.0)
        self.assertEqual(len(state["heads"]), 2)

    def test_render_names_the_failing_log_command_and_the_verdict(self):
        s = snap(checks=[run(conclusion="FAILURE", required=True, check_id=99)])
        text = "\n".join(ps.render(s, decide(s)))
        self.assertIn("failed: check (required) · gh run view --job 99 --log-failed", text)
        self.assertIn("settle: 사람 필요 @aaaaaaa", text)
        self.assertIn("next: ci — check", text)


class Patch(unittest.TestCase):
    """`pr-status patch` on a throwaway repo: main moves, the branch is rebased or merged, and the verified head is origin's."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = self.tmp / "repo"
        self.env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
        self.git("init", "-q", "--bare", "-b", "main", str(self.tmp / "origin.git"), cwd=self.tmp)
        self.git("clone", "-q", str(self.tmp / "origin.git"), str(self.repo), cwd=self.tmp)
        self.commit({"app.py": "a = 1\nb = 2\nc = 3\n", "README.md": "# app\n"}, "init")
        self.git("push", "-q", "-u", "origin", "main")
        self.git("checkout", "-q", "-b", "feat/x")
        self.commit({"app.py": "a = 1\nb = 2\nc = 30\n", "docs.md": "old words\n"}, "change c")
        self.git("push", "-q", "-u", "origin", "feat/x")   # the head that was verified

    def git(self, *args, cwd=None, check=True):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=self.env, capture_output=True, text=True, check=check).stdout.strip()

    def commit(self, files, message):
        for name, text in files.items():
            (self.repo / name).write_text(text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def main_moves(self, files):
        self.git("checkout", "-q", "main")
        self.commit(files, "main moves")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "feat/x")

    def patch(self, *args, base=("--base", "origin/main"), env=None):
        p = subprocess.run([sys.executable, str(PATH), "patch", *base, *args], cwd=self.repo, env=env or self.env,
                           capture_output=True, text=True)
        return p.returncode, p.stdout

    def path_with(self, **scripts):
        """An env whose PATH holds only git and the given fake commands."""
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir(exist_ok=True)
        for name, body in {"git": f'exec "{shutil.which("git")}" "$@"', **scripts}.items():
            (bin_dir / name).write_text(f"#!/bin/sh\n{body}\n")
            (bin_dir / name).chmod(0o755)
        return {**self.env, "PATH": str(bin_dir)}

    def test_a_clean_rebase_keeps_the_verification(self):
        self.main_moves({"other.py": "x = 1\n"})
        self.git("rebase", "-q", "origin/main")
        code, out = self.patch()
        self.assertEqual(code, 0)
        self.assertIn("patch: same", out)
        self.assertIn("next: nothing to re-verify", out)

    def test_merging_the_base_in_keeps_it_too(self):
        self.main_moves({"other.py": "x = 1\n"})
        self.git("merge", "-q", "--no-edit", "origin/main")
        self.assertIn("patch: same", self.patch()[1])

    def test_a_resolution_that_changed_code_gets_one_verifier_for_those_files(self):
        self.main_moves({"app.py": "a = 1\nb = 2\nc = 4\n"})
        self.git("rebase", "origin/main", check=False)   # conflicts on c
        (self.repo / "app.py").write_text("a = 1\nb = 2\nc = 34\n")
        self.git("add", "-A")
        self.git("-c", "core.editor=true", "rebase", "--continue")
        code, out = self.patch()
        self.assertEqual(code, 0)
        self.assertIn("patch: changed", out)
        self.assertIn("next: one verifier — rerun the checks and the behavior check that cover app.py (references/conflicts.md)", out)
        self.assertNotIn("docs.md", out)   # its part of the change was replayed untouched

    def test_a_fix_commit_on_top_counts_as_a_changed_patch(self):
        self.commit({"app.py": "a = 1\nb = 20\nc = 30\n"}, "small fix")
        self.assertIn("next: one verifier", self.patch()[1])

    def test_a_reindented_block_or_a_replaced_binary_is_a_changed_patch(self):
        # `git patch-id` alone ignores whitespace and binary hunks
        self.commit({"app.py": "a = 1\nb = 2\n    c = 30\n"}, "indent c")
        self.assertIn("next: one verifier", self.patch()[1])
        self.git("push", "-q", "origin", "feat/x")
        (self.repo / "img.bin").write_bytes(b"\x00\x01\xff")
        self.commit({}, "add image")
        self.git("push", "-q", "origin", "feat/x")
        (self.repo / "img.bin").write_bytes(b"\x00\x02\xff\xfe")
        self.commit({}, "replace image")
        out = self.patch()[1]
        self.assertIn("patch: changed", out)
        self.assertIn("img.bin", out)

    def test_a_wording_only_change_needs_no_verifier(self):
        self.commit({"docs.md": "new words\n"}, "reword")
        out = self.patch()[1]
        self.assertIn("patch: changed", out)
        self.assertIn("next: nothing to re-verify — only wording changed", out)

    def test_a_code_file_named_like_a_wording_file_gets_a_verifier(self):
        for name in ("license.py", "Notice.tsx", "changelog.ts", "page.mdx"):
            self.commit({name: f"{name} changed\n"}, f"touch {name}")
            self.assertIn(f"next: one verifier — rerun the checks and the behavior check that cover {name} ", self.patch()[1], name)
            self.git("push", "-q", "origin", "feat/x")

    def test_license_changelog_and_notice_are_wording(self):
        self.commit({"LICENSE": "MIT\n", "CHANGELOG": "1.0\n", "notice.txt": "n\n", "guide.rst": "g\n"}, "wording")
        self.assertIn("next: nothing to re-verify — only wording changed", self.patch()[1])

    def test_a_file_name_git_would_quote_is_still_compared(self):
        for name in ('has"quote.py', "한글.py"):
            self.commit({name: "x = 1\n"}, "odd name")
            out = self.patch()[1]
            self.assertIn(f"that cover {name} ", out, name)
            self.git("push", "-q", "origin", "feat/x")

    def test_a_changed_patch_with_no_differing_file_goes_to_the_verifier(self):
        real = {k: getattr(ps, k) for k in ("sh", "patch_id", "changed_files")}
        self.addCleanup(vars(ps).update, real)
        vars(ps).update(sh=lambda cmd, check=True: cmd[-1], changed_files=lambda fork, rev: set(),
                        patch_id=lambda fork, rev, path=None: rev)   # the whole patches differ, no file does
        out = ps.patch_lines("origin/main", "was", "head")
        self.assertIn("no single file found", out[0])
        self.assertIn("next: one verifier — rerun the checks and the behavior check that cover the whole change", out[1])

    def test_a_diff_that_is_not_utf8_is_still_compared(self):
        (self.repo / "latin1.py").write_bytes(b"name = 'caf\xe9'\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "latin-1 source")
        code, out = self.patch()
        self.assertEqual(code, 0)
        self.assertIn("that cover latin1.py ", out)

    def test_without_base_it_is_the_prs_base_on_origin(self):
        self.git("branch", "-q", "release", "main")
        self.git("push", "-q", "origin", "release")
        self.commit({"app.py": "a = 1\nb = 20\nc = 30\n"}, "small fix")
        self.assertIn("onto origin/release", self.patch("--was", "HEAD", base=(), env=self.path_with(gh="echo release"))[1])

    def test_without_a_pr_or_without_gh_the_base_is_origin_head(self):
        self.git("remote", "set-head", "origin", "main")
        for scripts in ({"gh": "exit 1"}, {}):   # no PR for this branch; no gh on PATH
            (self.tmp / "bin" / "gh").unlink(missing_ok=True)
            code, out = self.patch("--was", "HEAD", base=(), env=self.path_with(**scripts))
            self.assertEqual(code, 0, out)
            self.assertIn("onto origin/main", out)

    def test_the_verified_head_can_be_named(self):
        self.commit({"app.py": "a = 1\nb = 20\nc = 30\n"}, "small fix")
        self.assertIn("patch: same", self.patch("--was", "HEAD")[1])

    def test_no_pushed_head_to_compare_says_how_to_name_it(self):
        self.git("checkout", "-q", "-b", "feat/local-only")
        code, out = self.patch()
        self.assertEqual(code, 1)
        self.assertIn("next: name them — pr-status patch --base", out)


if __name__ == "__main__":
    unittest.main()
