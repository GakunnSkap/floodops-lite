from copy import deepcopy
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from baseline import greedy_assignment
from data import SCENARIOS, get_scenario
from optimizer import optimal_assignment
from visualization import cost_chart


class CostChartTests(unittest.TestCase):
    def check_components(self, spec, results):
        segments = spec["layer"][0]["data"]["values"]
        labels = spec["layer"][1]["data"]["values"]
        self.assertEqual(len(segments), 4)
        for method, result in zip(("Greedy reference", "Optimized"), results):
            parts = [part for part in segments if part["method"] == method]
            self.assertEqual([p["component"] for p in parts], ["Assignment cost", "Pending penalty"])
            self.assertEqual([p["cost"] for p in parts],
                             [result["assignment_cost"], result["pending_penalty"]])
            self.assertEqual(parts[0]["start"], 0)
            self.assertEqual(parts[0]["end"], parts[1]["start"])
            self.assertEqual(parts[1]["end"], result["total_cost"])
            self.assertEqual(sum(p["cost"] for p in parts), result["total_cost"])
            self.assertEqual([p["end"] - p["start"] for p in parts], [p["cost"] for p in parts])
            self.assertIn({"method": method, "label":
                           f"{result['assignment_cost']:g} + {result['pending_penalty']:g} = {result['total_cost']:g}"}, labels)

    def test_presets_components_totals_and_input_preserved(self):
        expected = ((10, 400, 20, 300), (8, 600, 8, 600), (10, 200, 10, 200))
        for name, values in zip(SCENARIOS, expected):
            with self.subTest(name=name):
                scenario = get_scenario(name)
                results = [greedy_assignment(scenario), optimal_assignment(scenario)]
                original = deepcopy(results)
                spec = cost_chart(*results)
                self.assertIsInstance(spec["padding"], dict)
                self.check_components(spec, results)
                self.assertEqual(tuple(v for r in results for v in (r["assignment_cost"], r["pending_penalty"])), values)
                self.assertEqual(results, original)

    def test_chart_updates_with_presets_and_manual_controls(self):
        with patch("visualization.cost_chart", wraps=cost_chart) as chart:
            app = AppTest.from_file("app.py").run()
            for name in (*SCENARIOS, "Default scenario"):
                app.selectbox(key="scenario_name").select(name).run()
                scenario = get_scenario(name)
                expected = (greedy_assignment(scenario), optimal_assignment(scenario))
                self.assertEqual(chart.call_args.args, expected)
                self.check_components(cost_chart(*chart.call_args.args), expected)
                self.assertEqual([m.value for m in app.metric[3:]], [str(r["total_cost"]) for r in expected])
                self.assertEqual(len(app.table), 4)
                self.assertFalse(app.exception)
            app.checkbox(key="available_E2").uncheck().run()
            scenario["teams"][1]["available"] = False
            self.assertEqual(chart.call_args.args, (greedy_assignment(scenario), optimal_assignment(scenario)))
            app.selectbox(key="priority_Z4").select(1).run()
            scenario["zones"][3].update(priority=1, penalty=100)
            expected = (greedy_assignment(scenario), optimal_assignment(scenario))
            self.assertEqual(chart.call_args.args, expected)
            self.check_components(cost_chart(*chart.call_args.args), expected)
            self.assertFalse(app.exception)

    def test_zero_cost_components_remain_visible_in_labels(self):
        result = {"assignment_cost": 0, "pending_penalty": 0, "total_cost": 0}
        spec = cost_chart(result, result)
        self.check_components(spec, (result, result))
        self.assertEqual(spec["layer"][0]["encoding"]["x"]["scale"]["domain"], [0, 1])
