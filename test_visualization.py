from copy import deepcopy
import json
from unittest.mock import patch
import unittest

from streamlit.testing.v1 import AppTest

from baseline import greedy_assignment
from data import get_scenario
from optimizer import optimal_assignment
from visualization import assignment_chart


class VisualizationTests(unittest.TestCase):
    def test_points_links_states_and_fixed_positions(self):
        scenario = get_scenario()
        original = deepcopy(scenario)
        layouts = []
        for method in (greedy_assignment, optimal_assignment):
            result = method(scenario)
            saved = deepcopy(result)
            spec = assignment_chart(scenario, result)
            links = spec["layer"][0]["data"]["values"]
            points = spec["layer"][1]["data"]["values"]
            self.assertEqual(len(points), 6)
            self.assertEqual({p["id"] for p in points if p["kind"] == "Zone"}, {"Z1", "Z2", "Z3", "Z4"})
            self.assertEqual({p["id"] for p in points if p["kind"] == "Team"}, {"E1", "E2"})
            self.assertEqual({(e["team"], e["zone"]) for e in links},
                             {(a["team_id"], a["zone_id"]) for a in result["assignments"]})
            self.assertEqual({p["id"] for p in points if p["status"] == "Pending"}, set(result["pending_zones"]))
            layouts.append([(p["kind"], p["id"], p["x"], p["y"]) for p in points])
            self.assertEqual(scenario, original)
            self.assertEqual(result, saved)
            self.assertNotIn('"url"', json.dumps(spec))
        self.assertEqual(layouts[0], layouts[1])

    def test_unavailable_team_and_priority_changes(self):
        scenario = get_scenario()
        scenario["teams"][1]["available"] = False
        scenario["zones"][3].update(priority=1, penalty=100)
        for method in (greedy_assignment, optimal_assignment):
            spec = assignment_chart(scenario, method(scenario))
            points = {p["id"]: p for p in spec["layer"][1]["data"]["values"]}
            self.assertEqual(points["E2"]["status"], "Unavailable")
            self.assertEqual(points["Z4"]["priority"], 1)
            self.assertEqual(points["Z4"]["penalty"], 100)
            self.assertTrue(all(link["team"] != "E2" for link in spec["layer"][0]["data"]["values"]))

    def test_no_available_teams_has_no_links(self):
        scenario = get_scenario()
        for team in scenario["teams"]:
            team["available"] = False
        spec = assignment_chart(scenario, optimal_assignment(scenario))
        self.assertEqual(spec["layer"][0]["data"]["values"], [])
        points = spec["layer"][1]["data"]["values"]
        self.assertEqual(sum(p["status"] == "Pending" for p in points), 4)

    def test_app_updates_selected_method_and_inputs(self):
        with patch("visualization.assignment_chart", wraps=assignment_chart) as chart:
            app = AppTest.from_file("app.py").run()
            scenario, result = chart.call_args.args
            self.assertEqual(result, greedy_assignment(scenario))
            app.radio[0].set_value("Optimized").run()
            scenario, result = chart.call_args.args
            self.assertEqual(result, optimal_assignment(scenario))
            self.assertEqual(result["total_cost"], 320)
            app.checkbox(key="available_E2").uncheck().run()
            app.selectbox(key="priority_Z4").select(1).run()
            scenario, result = chart.call_args.args
            self.assertFalse(scenario["teams"][1]["available"])
            self.assertEqual(scenario["zones"][3]["penalty"], 100)
            self.assertEqual(result, optimal_assignment(scenario))
            self.assertFalse(app.exception)
            captions = " ".join(c.value for c in app.caption)
            self.assertIn("not a geographic map", captions)
            self.assertIn("not roads or safe routes", captions)

    def test_chart_failure_preserves_tables_and_metrics(self):
        with patch("streamlit.vega_lite_chart", side_effect=RuntimeError("Chart unavailable")):
            app = AppTest.from_file("app.py").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.warning), 1)
        self.assertEqual(len(app.table), 4)
        self.assertEqual([m.value for m in app.metric[3:]], ["410", "320"])
