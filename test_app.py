from copy import deepcopy
from unittest.mock import patch
import unittest

from streamlit.testing.v1 import AppTest

from baseline import greedy_assignment
from data import get_scenario
from optimizer import optimal_assignment


class AppTests(unittest.TestCase):
    def check_display(self, app, scenario):
        self.assertFalse(app.exception)
        reference = greedy_assignment(scenario)
        optimized = optimal_assignment(scenario)
        self.assertEqual([m.value for m in app.metric[:2]], ["4", str(sum(t["available"] for t in scenario["teams"]))])
        self.assertEqual([m.value for m in app.metric[3:]], [str(reference["total_cost"]), str(optimized["total_cost"])])
        reduction = (reference["total_cost"] - optimized["total_cost"]) / reference["total_cost"] * 100
        self.assertEqual(app.metric[2].value, f"{reduction:.2f}%")
        expected_tables = []
        for result in (reference, optimized):
            self.assertIn(
                f"Assignment cost: {result['assignment_cost']} · "
                f"Pending penalties: {result['pending_penalty']}",
                [caption.value for caption in app.caption],
            )
            if result["assignments"]:
                expected_tables.append(([a["zone_id"] for a in result["assignments"]], [a["team_id"] for a in result["assignments"]]))
            if result["pending_zones"]:
                expected_tables.append((result["pending_zones"], None))
        self.assertEqual(len(app.table), len(expected_tables))
        for table, (zones, teams) in zip(app.table, expected_tables):
            self.assertEqual(table.value["Zone"].tolist(), zones)
            if teams is not None:
                self.assertEqual(table.value["Team"].tolist(), teams)
        return reference, optimized

    def test_initial_values_and_pending_zones(self):
        app = AppTest.from_file("app.py").run()
        self.check_display(app, get_scenario())
        self.assertEqual(app.metric[2].value, "21.95%")

    def test_team_availability_recalculates(self):
        app = AppTest.from_file("app.py").run()
        app.checkbox(key="available_E2").uncheck().run()
        scenario = get_scenario()
        scenario["teams"][1]["available"] = False
        reference, optimized = self.check_display(app, scenario)
        self.assertEqual(reference["total_cost"], 608)
        self.assertEqual(optimized["total_cost"], 608)
        self.assertTrue(app.info)

    def test_priority_updates_penalty_and_results(self):
        app = AppTest.from_file("app.py").run()
        app.selectbox(key="priority_Z4").select(1).run()
        scenario = get_scenario()
        scenario["zones"][3].update(priority=1, penalty=100)
        self.check_display(app, scenario)

    def test_no_available_teams(self):
        app = AppTest.from_file("app.py").run()
        app.checkbox(key="available_E1").uncheck()
        app.checkbox(key="available_E2").uncheck().run()
        scenario = get_scenario()
        for team in scenario["teams"]:
            team["available"] = False
        self.check_display(app, scenario)
        self.assertEqual([m.value for m in app.metric[3:]], ["900", "900"])

    def test_source_scenario_is_not_changed(self):
        original = deepcopy(get_scenario())
        app = AppTest.from_file("app.py").run()
        app.checkbox(key="available_E1").uncheck().run()
        app.selectbox(key="priority_Z1").select(1).run()
        self.assertFalse(app.exception)
        self.assertEqual(get_scenario(), original)

    def test_invalid_scenario_has_readable_error(self):
        scenario = get_scenario()
        scenario["costs"][0][0] = -1
        with patch("data.get_scenario", return_value=scenario):
            app = AppTest.from_file("app.py").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.error), 1)
        self.assertIn("Invalid scenario", app.error[0].value)

    def test_zero_reference_cost_has_no_division_by_zero(self):
        scenario = get_scenario()
        scenario["costs"] = [[0] * 4 for _ in range(4)]
        scenario["teams"] = [
            {"id": f"E{i}", "name": f"Equipo {i}", "available": True}
            for i in range(4)
        ]
        with patch("data.get_scenario", side_effect=lambda: deepcopy(scenario)):
            app = AppTest.from_file("app.py").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[2].value, "N/A")
        self.assertEqual([m.value for m in app.metric[3:]], ["0", "0"])
        self.assertTrue(app.info)
