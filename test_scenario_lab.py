from copy import deepcopy
import unittest

from streamlit.testing.v1 import AppTest

from data import SCENARIOS, get_scenario
from optimizer import optimal_assignment
from scenario_lab import simulate_e2_unavailable


class ScenarioLabTests(unittest.TestCase):
    def test_default(self):
        result = simulate_e2_unavailable(get_scenario())
        self.assertEqual(result["current"]["total_cost"], 320)
        self.assertEqual(result["what_if"]["total_cost"], 608)
        self.assertEqual(result["cost_increase"], 288)
        self.assertEqual(len(result["current"]["assignments"]), 2)
        self.assertEqual(len(result["what_if"]["assignments"]), 1)

    def test_availability_combinations(self):
        for e1, e2 in ((True, True), (True, False), (False, True), (False, False)):
            with self.subTest(e1=e1, e2=e2):
                scenario = get_scenario()
                scenario["teams"][0]["available"] = e1
                scenario["teams"][1]["available"] = e2
                original = deepcopy(scenario)
                result = simulate_e2_unavailable(scenario)
                alternative = deepcopy(scenario)
                alternative["teams"][1]["available"] = False
                self.assertEqual(result["current"], optimal_assignment(scenario))
                self.assertEqual(result["what_if"], optimal_assignment(alternative))
                self.assertGreaterEqual(result["cost_increase"], 0)
                if not e2:
                    self.assertEqual(result["current"], result["what_if"])
                    self.assertEqual(result["cost_increase"], 0)
                self.assertEqual(scenario, original)

    def test_priorities_presets_and_independent_results(self):
        for name in SCENARIOS:
            scenario = get_scenario(name)
            scenario["zones"][0].update(priority=1, penalty=100)
            original = deepcopy(scenario)
            result = simulate_e2_unavailable(scenario)
            alternative = deepcopy(scenario)
            alternative["teams"][1]["available"] = False
            self.assertEqual(result["what_if"], optimal_assignment(alternative))
            self.assertEqual(result["current"], optimal_assignment(scenario))
            result["what_if"]["pending_zones"].append("test-only")
            self.assertEqual(scenario, original)
            self.assertNotIn("test-only", result["current"]["pending_zones"])

    def test_button_and_recalculation_preserve_controls(self):
        app = AppTest.from_file("app.py").run()
        self.assertEqual(len(app.metric), 5)
        controls = ([c.value for c in app.checkbox], [c.value for c in app.selectbox])
        app.button(key="simulate_e2").click().run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric[-3:]], ["320", "608", "+288"])
        self.assertEqual(controls, ([c.value for c in app.checkbox], [c.value for c in app.selectbox]))
        for name in ("Priority shift", "Limited resources", "Default scenario"):
            app.selectbox(key="scenario_name").select(name).run()
            self.assertFalse(app.exception)
            if name == "Limited resources":
                self.assertEqual(len(app.metric), 5)
                self.assertIn("E2 is already unavailable", " ".join(i.value for i in app.info))
            else:
                result = simulate_e2_unavailable(get_scenario(name))
                self.assertEqual([m.value for m in app.metric[-3:]],
                                 [str(result["current"]["total_cost"]), str(result["what_if"]["total_cost"]), f"{result['cost_increase']:+g}"])
        app.checkbox(key="available_E1").uncheck().run()
        scenario = get_scenario()
        scenario["teams"][0]["available"] = False
        app.selectbox(key="priority_Z4").select(1).run()
        scenario["zones"][3].update(priority=1, penalty=100)
        expected = simulate_e2_unavailable(scenario)
        self.assertEqual(app.metric[-2].value, str(expected["what_if"]["total_cost"]))
        app.checkbox(key="available_E2").uncheck().run()
        self.assertEqual(len(app.metric), 5)
        self.assertIn("E2 is already unavailable", " ".join(i.value for i in app.info))
        self.assertFalse(app.exception)

    def test_zero_increase_when_e2_is_not_used(self):
        scenario = get_scenario()
        scenario["costs"][1] = [None] * 4
        result = simulate_e2_unavailable(scenario)
        self.assertEqual(result["cost_increase"], 0)
