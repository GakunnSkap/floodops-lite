from copy import deepcopy
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from baseline import greedy_assignment
from data import SCENARIOS, get_scenario
from explanation import explain_decisions
from optimizer import optimal_assignment


class ExplanationTests(unittest.TestCase):
    def test_default_explanation_matches_results_and_preserves_inputs(self):
        scenario = get_scenario()
        reference, optimized = greedy_assignment(scenario), optimal_assignment(scenario)
        original = deepcopy((scenario, reference, optimized))
        text = " ".join(explain_decisions(scenario, reference, optimized))
        for expected in ("E1: Z2 → Z1", "E2: Z1 → Z4", "90 synthetic units lower",
                         "Pending → served: Z4", "Served → pending: Z2",
                         "Z1 changes team: E2 → E1", "only available team compatible with Z4",
                         "Greedy uses E2 for Z1"):
            self.assertIn(expected, text)
        self.assertEqual((scenario, reference, optimized), original)

    def test_presets_and_manual_controls_match_displayed_assignments(self):
        app = AppTest.from_file("app.py").run()
        for name in (*SCENARIOS, "Default scenario"):
            app.selectbox(key="scenario_name").select(name).run()
            scenario = get_scenario(name)
            results = (greedy_assignment(scenario), optimal_assignment(scenario))
            text = " ".join(m.value for m in app.markdown)
            for line in explain_decisions(scenario, *results):
                self.assertIn(line, text)
            if name != "Default scenario":
                self.assertIn("Equal assignments and equal total cost", text)
                self.assertNotIn("only available team", text)
            self.assertEqual([t.value["Team"].tolist() for t in (app.table[0], app.table[2])],
                             [[a["team_id"] for a in r["assignments"]] for r in results])
            self.assertFalse(app.exception)
        for available, priority in ((False, 3), (False, 1), (True, 1), (True, 3)):
            app.checkbox(key="available_E2").set_value(available).run()
            app.selectbox(key="priority_Z4").select(priority).run()
            scenario["teams"][1]["available"] = available
            scenario["zones"][3].update(priority=priority, penalty=100 * priority)
            text = " ".join(m.value for m in app.markdown)
            for line in explain_decisions(scenario, greedy_assignment(scenario), optimal_assignment(scenario)):
                self.assertIn(line, text)
            self.assertFalse(app.exception)

    def test_equal_objective_with_different_valid_assignments(self):
        scenario = get_scenario()
        scenario["costs"] = [[0] * 4 for _ in range(2)]
        for zone in scenario["zones"]:
            zone.update(priority=1, penalty=100)
        reference = greedy_assignment(scenario)
        alternative = deepcopy(reference)
        for assignment in alternative["assignments"]:
            assignment["team_id"] = "E2" if assignment["team_id"] == "E1" else "E1"
        self.assertEqual(optimal_assignment(scenario)["total_cost"], alternative["total_cost"])
        text = " ".join(explain_decisions(scenario, reference, alternative))
        self.assertIn("Different assignments, equal objective", text)
        self.assertNotIn("lower", text)
        self.assertNotIn("only available team", text)
        with patch("data.get_scenario", side_effect=lambda: deepcopy(scenario)), \
             patch("optimizer.optimal_assignment", return_value=alternative):
            app = AppTest.from_file("app.py").run()
        self.assertFalse(app.exception)
        self.assertIn("Different assignments, equal objective", " ".join(m.value for m in app.markdown))
        self.assertEqual(app.table[2].value["Team"].tolist(),
                         [a["team_id"] for a in alternative["assignments"]])

    def test_no_unsupported_unique_compatibility_claim(self):
        scenario = get_scenario()
        scenario["costs"][0][3] = 25
        text = " ".join(explain_decisions(scenario, greedy_assignment(scenario), optimal_assignment(scenario)))
        self.assertNotIn("only available team", text)
        for team in scenario["teams"]:
            team["available"] = False
        text = " ".join(explain_decisions(scenario, greedy_assignment(scenario), optimal_assignment(scenario)))
        self.assertIn("Equal assignments and equal total cost", text)
        self.assertNotIn("Pending → served", text)
