from pathlib import Path
import unittest

from experiments.reproduce import reproduce


class ExperimentTests(unittest.TestCase):
    def test_fault_matrix_and_clean_control(self):
        report = reproduce(Path(__file__).resolve().parents[1] / "examples/corpus.json")
        self.assertEqual(report["summary"], {
            "clean_cases": 1, "fault_cases": 18, "baseline_detected": 3,
            "gate_detected": 18, "gate_false_positives": 0,
        })
        self.assertEqual(len({case["case"] for case in report["cases"]}), 19)
        self.assertTrue(report["cases"][0]["baseline_pass"])
        for case in report["cases"]:
            self.assertEqual(case["gate_pass"], case["expected_pass"], case["case"])


if __name__ == "__main__":
    unittest.main()
