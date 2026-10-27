from copy import deepcopy
import unittest

from streamlit.testing.v1 import AppTest

from baseline import greedy_assignment
from data import SCENARIOS, get_scenario
from optimizer import optimal_assignment
from priority_indicator import unserved_priority


class PriorityIndicatorTests(unittest.TestCase):
    def test_default_and_preset_ties(self):
        for name, expected in zip(SCENARIOS, ((4, 3), (6, 6), (2, 2))):
            scenario = get_scenario(name)
            original = deepcopy(scenario)
            scores = []
            for method in (greedy_assignment, optimal_assignment):
                result = method(scenario)
                score = unserved_priority(scenario, result)
                scores.append(score)
                self.assertEqual(score * 100, result["pending_penalty"])
            self.assertEqual(tuple(scores), expected)
            self.assertEqual(scenario, original)

    def test_priority_change_and_disabled_teams(self):
        scenario = get_scenario()
        scenario["zones"][2].update(priority=2, penalty=200)
        self.assertEqual(unserved_priority(scenario, greedy_assignment(scenario)), 5)
        self.assertEqual(unserved_priority(scenario, optimal_assignment(scenario)), 4)
        for available in ((True, False), (False, True), (False, False)):
            for team, state in zip(scenario["teams"], available):
                team["available"] = state
            for method in (greedy_assignment, optimal_assignment):
                result = method(scenario)
                expected = sum(z["priority"] for z in scenario["zones"] if z["id"] in result["pending_zones"])
                self.assertEqual(unserved_priority(scenario, result), expected)
        self.assertEqual(unserved_priority(scenario, optimal_assignment(scenario)), 10)

    def test_app_updates_and_tie_message(self):
        app = AppTest.from_file("app.py").run()
        for name in SCENARIOS:
            app.selectbox(key="scenario_name").select(name).run()
            scenario = get_scenario(name)
            text = " ".join(m.value for m in app.markdown)
            for title, method in (("Quick decisions", greedy_assignment), ("Best allocation", optimal_assignment)):
                score = unserved_priority(scenario, method(scenario))
                self.assertIn(f"{title}: **{score} priority points unserved.**", text)
            if name != "Default scenario":
                self.assertIn("same sum of priority points", text)
            self.assertFalse(app.exception)
        app.checkbox(key="available_E1").uncheck().run()
        app.checkbox(key="available_E2").uncheck().run()
        self.assertIn("**8 priority points unserved.**", " ".join(m.value for m in app.markdown))
        self.assertFalse(app.exception)

    def test_optimizer_can_trade_priority_for_assignment_cost(self):
        scenario = get_scenario()
        scenario["costs"] = [[1000] * 4 for _ in scenario["teams"]]
        quick = unserved_priority(scenario, greedy_assignment(scenario))
        best = unserved_priority(scenario, optimal_assignment(scenario))
        self.assertGreater(best, quick)
        from unittest.mock import patch
        with patch("data.get_scenario", side_effect=lambda: deepcopy(scenario)):
            app = AppTest.from_file("app.py").run()
        self.assertIn("not this indicator alone", " ".join(m.value for m in app.markdown))
        self.assertFalse(app.exception)
