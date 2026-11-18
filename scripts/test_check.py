import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check.py"


def load():
    spec = importlib.util.spec_from_file_location("check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContractFailures(unittest.TestCase):
    def setUp(self):
        self.check = load()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.check.ROOT = Path(self.tmp.name)
        (self.check.ROOT / "caller.md").write_text("Pass `Go-Line:` to the callee.\n", encoding="utf-8")
        (self.check.ROOT / "callee.md").write_text("Reads nothing.\n", encoding="utf-8")

    def run_contracts(self, *checks):
        self.check.CONTRACTS = [self.check.Contract("caller-callee", "callee parses the line caller prints", list(checks))]
        self.check.check_contracts()
        return self.check.errors

    def test_token_in_every_file_passes(self):
        self.assertEqual(self.run_contracts(("go-line:", ["caller.md"])), [])

    def test_token_case_does_not_matter(self):
        self.assertEqual(self.run_contracts(("Go-Line:", ["caller.md"])), [])

    def test_missing_token_names_the_contract_its_reason_and_both_sides(self):
        (error,) = self.run_contracts(("go-line:", ["caller.md", "callee.md"]))
        self.assertEqual(error, "callee.md: contract token 'go-line:' missing — caller-callee: "
                                "callee parses the line caller prints — update both sides: caller.md, callee.md")

    def test_a_token_note_follows_the_reason(self):
        (error,) = self.run_contracts(("go-line:", ["callee.md"], "the template line itself"))
        self.assertIn("caller-callee: callee parses the line caller prints (the template line itself) — update", error)

    def test_missing_file_carries_the_reason_too(self):
        (error,) = self.run_contracts(("go-line:", ["gone.md"]))
        self.assertEqual(error, "gone.md: contract file missing (token 'go-line:') — caller-callee: callee parses the line caller prints")

    def test_every_real_contract_has_a_name_and_a_reason(self):
        contracts = self.check.CONTRACTS
        names = [c.name for c in contracts]
        self.assertEqual(len(names), len(set(names)))
        for c in contracts:
            self.assertTrue(c.name and c.why and c.checks, c.name)

    def test_every_real_check_is_a_token_its_files_and_at_most_one_note(self):
        for c in self.check.CONTRACTS:
            for entry in c.checks:
                token, files, *note = entry
                self.assertTrue(isinstance(token, str) and token, (c.name, entry))
                self.assertTrue(isinstance(files, list) and files and all(isinstance(f, str) for f in files), (c.name, entry))
                self.assertTrue(len(note) <= 1 and all(isinstance(n, str) and n for n in note), (c.name, entry))


if __name__ == "__main__":
    unittest.main()
