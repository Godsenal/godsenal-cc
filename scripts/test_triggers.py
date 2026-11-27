import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("triggers", Path(__file__).with_name("triggers.py"))
tr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tr)

DOCS = {
    "deploy": "deploy the app to production servers rollout",
    "review": "review a diff for bugs regressions security holes",
    "screens": "design taste for app screens onboarding empty states",
}


def cases(skills, max_similarity=0.9, similar_pairs=()):
    skills = {n: {"train": [], **s} for n, s in skills.items()}
    return {"max_similarity": max_similarity, "similar_pairs": list(similar_pairs), "skills": skills}


class Tokens(unittest.TestCase):
    def test_english_is_stemmed_and_stopwords_dropped_korean_becomes_bigrams(self):
        self.assertEqual(tr.tokens("Reviews of the screens 화면을 줘"), ["review", "screen", "화면", "면을"])

    def test_inflections_of_one_word_share_a_stem(self):
        for group in (("change", "changes", "changed", "changing"), ("fix", "fixes", "fixed", "fixing"),
                      ("process", "processes"), ("case", "cases"), ("size", "sizes"), ("make", "making"), ("status",)):
            self.assertEqual({tr.stem(w) for w in group}, {tr.stem(group[0])}, group)
        self.assertEqual(tr.stem("status"), "status")


class Problems(unittest.TestCase):
    def test_every_test_prompt_first_passes_and_prints_the_ratio(self):
        line, found = tr.problems(cases({"review": {"test": ["find bugs in my diff"]}}), DOCS)
        self.assertEqual(found, [])
        self.assertEqual(line, "triggers: rank1 1/1 (100%) across 1 skills (held-out test; Korean 0/0)")

    def test_korean_prompts_are_counted_apart(self):
        line = tr.problems(cases({"screens": {"test": ["onboarding screens", "화면 손봐"], "min_rank1": 1}}),
                           DOCS)[0]
        self.assertTrue(line.endswith("(held-out test; Korean 0/1)"), line)

    def test_a_train_miss_is_never_judged(self):
        skill = {"test": ["find bugs"], "train": ["ship to production"]}
        self.assertEqual(tr.problems(cases({"review": skill}), DOCS)[1], [])
        self.assertEqual(tr.measure(cases({"review": skill}), DOCS, "train")[0]["review"]["rank1"], 0)

    def test_a_prompt_in_both_train_and_test_fails(self):
        (problem,) = tr.problems(cases({"review": {"test": ["find bugs"], "train": ["find bugs"]}}), DOCS)[1]
        self.assertIn("in both train and test", problem)

    def test_a_miss_below_the_default_floor_says_fix_the_description(self):
        (problem,) = tr.problems(cases({"review": {"test": ["find bugs", "ship to production"]}}), DOCS)[1]
        self.assertIn("review: 1/2 test prompts pick it first, floor 2 — fix its description", problem)
        self.assertIn("'ship to production' → deploy", problem)

    def test_a_floor_at_the_actual_passes_above_or_below_fails(self):
        skill = {"test": ["find bugs", "ship to production"]}
        for floor, failing in ((0, True), (1, False), (2, True)):
            found = tr.problems(cases({"review": {**skill, "min_rank1": floor}}), DOCS)[1]
            self.assertEqual(bool(found), failing, floor)

    def test_a_negative_hit_fails_unless_allowed(self):
        skill = {"test": ["deploy to production"], "negative": ["rollout the servers"]}
        (problem,) = tr.problems(cases({"deploy": skill}), DOCS)[1]
        self.assertIn("deploy: 1 negative prompts pick it first, allowed 0", problem)
        self.assertEqual(tr.problems(cases({"deploy": {**skill, "max_negative_hits": 1}}), DOCS)[1], [])

    def test_similar_descriptions_fail_unless_the_pair_is_listed(self):
        docs = {**DOCS, "review2": "review a diff for bugs regressions"}
        (problem,) = tr.problems(cases({}, max_similarity=0.5), docs)[1]
        self.assertTrue(problem.startswith("review and review2: descriptions are"), problem)
        self.assertEqual(tr.problems(cases({}, 0.5, [["review2", "review"]]), docs)[1], [])

    def test_a_pair_listed_in_reverse_of_listing_order_is_exempted(self):
        docs = {"zeta": "review a diff for bugs regressions", **DOCS}
        self.assertTrue(tr.problems(cases({}, max_similarity=0.5), docs)[1])
        self.assertEqual(tr.problems(cases({}, 0.5, [["review", "zeta"]]), docs)[1], [])

    def test_a_prompt_that_matches_nothing_picks_no_skill(self):
        line, found = tr.problems(cases({"deploy": {"test": ["줘"], "min_rank1": 0}}), DOCS)
        self.assertEqual((line, found), ("triggers: rank1 0/1 (0%) across 1 skills (held-out test; Korean 0/1)", []))

    def test_a_floor_below_the_actual_asks_to_raise_it(self):
        (problem,) = tr.problems(cases({"review": {"test": ["find bugs", "ship to production"], "min_rank1": 0}}), DOCS)[1]
        self.assertIn("review: 1 test prompts pick it first, above its floor 0 — raise min_rank1 to 1", problem)
        (problem,) = tr.problems(cases({"deploy": {"test": ["deploy"], "negative": ["find bugs"], "max_negative_hits": 1}}), DOCS)[1]
        self.assertIn("below max_negative_hits 1 — lower it", problem)

    def test_an_unknown_skill_name_fails(self):
        (problem,) = tr.problems(cases({"gone": {"test": ["x"]}}), DOCS)[1]
        self.assertTrue(problem.startswith("gone: no model-invocable skill"), problem)


class Listing(unittest.TestCase):
    def test_a_skill_name_in_two_plugins_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            for plugin in ("a", "b"):
                md = Path(tmp, "plugins", plugin, "skills", "review", "SKILL.md")
                md.parent.mkdir(parents=True)
                md.write_text("---\nname: review\ndescription: review things\n---\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "two plugins have a skill named review"):
                tr.listing(tr.check_module().frontmatter, Path(tmp))


class RealListing(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads(tr.CASES.read_text(encoding="utf-8"))
        self.docs = tr.listing(tr.check_module().frontmatter)

    def test_the_repo_passes_its_own_floors(self):
        self.assertEqual(tr.problems(self.cases, self.docs)[1], [])

    def test_followed_pstack_skills_are_not_in_the_listing(self):
        self.assertIn("design-taste", self.docs)
        self.assertNotIn("poteto-mode", self.docs)

    def test_descriptions_without_their_korean_phrasings_fail(self):
        # held-out Korean prompts reach these skills only through the Korean phrasings in their descriptions
        docs = {n: re.sub(r"[가-힣]+", "", d) if n in self.cases["skills"] else d for n, d in self.docs.items()}
        found = tr.problems(self.cases, docs)[1]
        self.assertTrue(any("test prompts pick it first, floor" in p for p in found), found)

if __name__ == "__main__":
    unittest.main()
