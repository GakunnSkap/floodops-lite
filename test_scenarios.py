from copy import deepcopy
from unittest.mock import patch
import unittest

from streamlit.testing.v1 import AppTest

from baseline import greedy_assignment
from data import SCENARIOS, get_scenario
from optimizer import optimal_assignment
import test_app
from visualization import assignment_chart


class ScenarioPresetTests(unittest.TestCase):
    def test_presets_results_and_original_preserved(self):
        original = deepcopy(get_scenario())
        for name, expected in zip(SCENARIOS, [(410, 320), (608, 608), (210, 210)]):
            with self.subTest(name=name):
                scenario = get_scenario(name)
                self.assertTrue(scenario["simulated"])
                self.assertEqual(scenario["costs"], original["costs"])
                self.assertEqual(len(scenario["zones"]), 4)
                self.assertEqual(len(scenario["teams"]), 2)
                for method, cost in zip((greedy_assignment, optimal_assignment), expected):
                    result = method(scenario)
                    self.assertEqual(result["total_cost"], cost)
                    self.assertEqual(result, method(get_scenario(name)))
                self.assertEqual(scenario, get_scenario(name))
        self.assertEqual(get_scenario(), original)
        self.assertFalse(get_scenario("Limited resources")["teams"][1]["available"])
        self.assertEqual([z["priority"] for z in get_scenario("Priority shift")["zones"]], [3, 3, 1, 1])

    def test_unknown_preset_is_rejected(self):
        with self.assertRaises(ValueError):
            get_scenario("Unknown")

    def test_repeated_switches_sync_controls_tables_metrics_and_chart(self):
        with patch("visualization.assignment_chart", wraps=assignment_chart) as chart:
            app = AppTest.from_file("app.py").run()
            for name in ("Limited resources", "Priority shift", "Default scenario",
                         "Priority shift", "Limited resources", "Default scenario"):
                with self.subTest(name=name):
                    app.selectbox(key="scenario_name").select(name).run()
                    expected = get_scenario(name)
                    self.assertEqual([c.value for c in app.checkbox], [t["available"] for t in expected["teams"]])
                    self.assertEqual([app.selectbox(key=f"priority_{z['id']}").value for z in expected["zones"]], [z["priority"] for z in expected["zones"]])
                    test_app.AppTests().check_display(app, expected)
                    actual, result = chart.call_args.args
                    self.assertEqual(actual, expected)
                    self.assertEqual(result, greedy_assignment(expected))
                    app.radio[0].set_value("Optimized").run()
                    actual, result = chart.call_args.args
                    self.assertEqual(actual, expected)
                    self.assertEqual(result, optimal_assignment(expected))
                    app.radio[0].set_value("Greedy reference").run()
                    if name != "Default scenario":
                        self.assertTrue(app.info)

    def test_manual_changes_persist_until_preset_changes(self):
        app = AppTest.from_file("app.py").run()
        app.selectbox(key="scenario_name").select("Limited resources").run()
        app.checkbox(key="available_E2").check().run()
        app.selectbox(key="priority_Z4").select(1).run()
        app.radio[0].set_value("Optimized").run()
        expected = get_scenario()
        expected["zones"][3].update(priority=1, penalty=100)
        test_app.AppTests().check_display(app, expected)
        self.assertTrue(app.checkbox(key="available_E2").value)
        self.assertEqual(app.selectbox(key="priority_Z4").value, 1)
        app.selectbox(key="scenario_name").select("Priority shift").run()
        app.selectbox(key="scenario_name").select("Limited resources").run()
        self.assertFalse(app.checkbox(key="available_E2").value)
        self.assertEqual(app.selectbox(key="priority_Z4").value, 3)
        self.assertEqual(get_scenario()["zones"][3]["priority"], 3)

    def test_explanation_uses_actual_changes(self):
        app = AppTest.from_file("app.py").run()
        text = " ".join(m.value for m in app.markdown)
        self.assertIn("E1: Z2 → Z1", text)
        self.assertIn("E2: Z1 → Z4", text)
        captions = " ".join(c.value for c in app.caption)
        self.assertIn("assignment cost +10; pending penalties -100; total -90", captions)
        app.selectbox(key="scenario_name").select("Priority shift").run()
        self.assertIn("Both methods choose the same assignments.", " ".join(m.value for m in app.markdown))
