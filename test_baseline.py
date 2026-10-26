from copy import deepcopy
import unittest

from baseline import greedy_assignment
from data import get_scenario


class BaselineTests(unittest.TestCase):
    def check_result(self, scenario):
        original = deepcopy(scenario)
        result = greedy_assignment(scenario)
        self.assertEqual(scenario, original)
        self.assertEqual(result, greedy_assignment(scenario))
        teams = {team["id"]: i for i, team in enumerate(scenario["teams"])}
        zones = {zone["id"]: j for j, zone in enumerate(scenario["zones"])}
        assigned_teams = [a["team_id"] for a in result["assignments"]]
        assigned_zones = [a["zone_id"] for a in result["assignments"]]
        self.assertEqual(len(assigned_teams), len(set(assigned_teams)))
        self.assertEqual(len(assigned_zones), len(set(assigned_zones)))
        pending = result["pending_zones"]
        self.assertEqual(len(pending), len(set(pending)))
        self.assertFalse(set(assigned_zones) & set(pending))
        self.assertEqual(set(assigned_zones) | set(pending), set(zones))
        cost = 0
        for assignment in result["assignments"]:
            i = teams[assignment["team_id"]]
            j = zones[assignment["zone_id"]]
            self.assertTrue(scenario["teams"][i]["available"])
            self.assertIsNotNone(scenario["costs"][i][j])
            cost += scenario["costs"][i][j]
        penalty = sum(scenario["zones"][zones[z]]["penalty"] for z in pending)
        self.assertEqual(result["assignment_cost"], cost)
        self.assertEqual(result["pending_penalty"], penalty)
        self.assertEqual(result["total_cost"], cost + penalty)
        return result

    def test_initial_scenario_with_more_zones_than_teams(self):
        result = self.check_result(get_scenario())
        self.assertEqual(result, {
            "assignments": [
                {"team_id": "E2", "zone_id": "Z1"},
                {"team_id": "E1", "zone_id": "Z2"},
            ],
            "pending_zones": ["Z4", "Z3"],
            "assignment_cost": 10,
            "pending_penalty": 400,
            "total_cost": 410,
        })

    def test_no_available_teams(self):
        scenario = get_scenario()
        for team in scenario["teams"]:
            team["available"] = False
        result = self.check_result(scenario)
        self.assertEqual(result["assignments"], [])
        self.assertEqual(result["total_cost"], 900)

    def test_no_compatible_teams(self):
        scenario = get_scenario()
        scenario["costs"] = [[None] * 4, [None] * 4]
        result = self.check_result(scenario)
        self.assertEqual(result["assignments"], [])
        self.assertEqual(result["pending_penalty"], 900)

    def test_incompatible_zone_does_not_consume_a_team(self):
        scenario = get_scenario()
        scenario["costs"] = [[None, 4, 2, None], [None, 5, None, 12]]
        result = self.check_result(scenario)
        self.assertEqual(result["assignments"], [
            {"team_id": "E2", "zone_id": "Z4"},
            {"team_id": "E1", "zone_id": "Z2"},
        ])

    def test_ties_use_identifiers_even_when_input_order_changes(self):
        scenario = get_scenario()
        scenario["costs"] = [[4] * 4, [4] * 4]
        result = self.check_result(scenario)
        self.assertEqual(result["assignments"], [
            {"team_id": "E1", "zone_id": "Z1"},
            {"team_id": "E2", "zone_id": "Z4"},
        ])
        scenario["teams"].reverse()
        scenario["costs"].reverse()
        scenario["zones"].reverse()
        for row in scenario["costs"]:
            row.reverse()
        self.assertEqual(self.check_result(scenario), result)

    def test_unavailable_cheaper_team_is_not_selected(self):
        scenario = get_scenario()
        scenario["teams"][1]["available"] = False
        result = self.check_result(scenario)
        self.assertEqual(result["assignments"], [{"team_id": "E1", "zone_id": "Z1"}])

    def test_greedy_does_not_skip_an_admissible_expensive_assignment(self):
        scenario = get_scenario()
        scenario["costs"] = [[1000] * 4, [1000] * 4]
        result = self.check_result(scenario)
        self.assertEqual(len(result["assignments"]), 2)
        self.assertEqual(result["assignment_cost"], 2000)

    def test_invalid_scenario_is_rejected(self):
        scenario = get_scenario()
        scenario["costs"][0][0] = -1
        with self.assertRaises(ValueError):
            greedy_assignment(scenario)
