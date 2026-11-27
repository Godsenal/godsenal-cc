import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "plugins/base/skills"


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module


ps = load("pr_status_setting", BASE / "monitor/scripts/pr-status")
sp = load("ship_prep_setting", BASE / "branch-pr/scripts/ship-prep")

REPLIES = ("review replies", "draft")
PREVIEW = ("before the PR", "preview")
SIGNOFF = ("commit sign-off", "on")

ON = (
    "- {k}: {v}",
    "{k}: {v}",
    "  - {k}: {v}",
    "* {k}: {v}",
    "> - {k}: {v}",
    "- `{k}`: {v}",
    "- `{k}`: `{v}`",
    "* **{K}**: `{v}`",
    "- **{k}:** {v}",
    "- _{k}_: {v}",
    "- {k} : {v}",
    "- {k}:{v}",
    "- {k}： {v}",
    "- {UP}: {VUP}",
    "- {k}: {v} (신규 입사 기간)",
    "- {k}: {v}.",
    "# Environment: acme\n\n## Conventions\n- Branch: `feat/<slug>`\n\n## Shipping\n- {k}: {v}\n- merge: squash",
    "## Shipping\r\n- {k}: {v}\r\n",
    "- {k}:\n  {v}",
)
OFF = (
    "",
    "## Shipping\n",
    "- {k}: {v}s-later",
    "- {k}: {v}_mode",
    "- {k}: not {v}",
    "- {k}: off",
    "- {k} {v}",
    "- {k}",
    "- {k}:\n- {v}",
    "we used to have {k}: {v}",
    "# {k}: {v}",
    "1. {k}: {v}",
    "- the {k}: {v}",
)


def fill(form, setting):
    k, v = setting
    return form.format(k=k, v=v, K=k[0].upper() + k[1:], UP=k.upper(), VUP=v.upper())


class SameLineFormat(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.env = Path(tmp.name) / "env.md"
        sp.environment_file = lambda: str(self.env)

    def signoff_pr_status(self, text):
        return any("sign-off: on" in line for line in ps.commit_rules(str(self.env), text))

    def signoff_ship_prep(self, text):
        self.env.write_bytes(text.encode("utf-8"))
        return sp.review_policy().get("signoff", False)

    def test_both_scripts_read_the_sign_off_line_in_the_same_forms(self):
        for form in ON:
            with self.subTest(form=form):
                self.assertTrue(self.signoff_pr_status(fill(form, SIGNOFF)), "pr-status does not read this form")
                self.assertTrue(self.signoff_ship_prep(fill(form, SIGNOFF)), "ship-prep does not read this form")
        for form in OFF:
            with self.subTest(form=form):
                self.assertFalse(self.signoff_pr_status(fill(form, SIGNOFF)), "pr-status reads this form as on")
                self.assertFalse(self.signoff_ship_prep(fill(form, SIGNOFF)), "ship-prep reads this form as on")

    def test_the_value_lines_take_the_same_prefixes(self):
        for form in (f for f in ON if "{k}:\n" not in f):
            with self.subTest(form=form):
                self.env.write_bytes((fill(form, ("reviewers", "@alice")) + "\n" + fill(form, ("labels", "needs-review"))
                                      + "\n" + fill(form, ("PR size", "400 lines"))).encode("utf-8"))
                policy = sp.review_policy()
                self.assertEqual([r.lower() for r in policy.get("reviewers", [])], ["alice"])
                self.assertEqual([l.lower() for l in policy.get("labels", [])], ["needs-review"])
                self.assertEqual(policy.get("size"), 400)
        for form in OFF:
            with self.subTest(form=form):
                self.env.write_bytes(fill(form, ("PR size", "400 lines")).encode("utf-8"))
                self.assertIsNone(sp.review_policy().get("size"), "ship-prep reads this form as a size")

    def replies(self, text):
        return ps.replies_mode(None, str(self.env), text)[0] == "draft"

    def preview(self, text):
        self.env.write_bytes(text.encode("utf-8"))
        return sp.preview_setting() == (str(self.env), "")

    def test_a_form_that_turns_one_setting_on_turns_the_other_on(self):
        for form in ON:
            with self.subTest(form=form):
                self.assertTrue(self.replies(fill(form, REPLIES)), "pr-status does not read this form")
                self.assertTrue(self.preview(fill(form, PREVIEW)), "ship-prep does not read this form")

    def test_a_form_that_leaves_one_setting_off_leaves_the_other_off(self):
        for form in OFF:
            with self.subTest(form=form):
                self.assertFalse(self.replies(fill(form, REPLIES)), "pr-status reads this form as on")
                self.assertFalse(self.preview(fill(form, PREVIEW)), "ship-prep reads this form as on")

    def test_each_script_reads_only_its_own_line(self):
        for form in ON:
            with self.subTest(form=form):
                self.assertFalse(self.replies(fill(form, PREVIEW)))
                self.assertFalse(self.preview(fill(form, REPLIES)))

    def test_both_lines_in_one_file_turn_both_on(self):
        text = "## Shipping\n- before the PR: preview\n- review replies: draft\n"
        self.assertTrue(self.replies(text))
        self.assertTrue(self.preview(text))


if __name__ == "__main__":
    unittest.main()
