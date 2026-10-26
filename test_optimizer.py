from copy import deepcopy
from itertools import product
from random import Random
import unittest

from baseline import greedy_assignment
from data import get_scenario
from optimizer import optimal_assignment


def exhaustive_cost(scenario):
    """Enumera decisiones por equipo sin usar la matriz ampliada ni SciPy."""
    zones = scenario["zones"]
    choices = [
        [None] + [j for j in range(len(zones)) if scenario["costs"][i][j] is not None]
        if team["available"] else [None]
        for i, team in enumerate(scenario["teams"])
    ]
    best = float("inf")
    for selection in product(*choices):
        assigned = [j for j in selection if j is not None]
        if len(assigned) != len(set(assigned)):
            continue
        cost = sum(scenario["costs"][i][j] for i, j in enumerate(selection) if j is not None)
        cost += sum(zone["penalty"] for j, zone in enumerate(zones) if j not in assigned)
        best = min(best, cost)
    return best


class OptimizerTests(unittest.TestCase):
    def check_result(self, scenario):
        original = deepcopy(scenario)
        result = optimal_assignment(scenario)
        self.assertEqual(scenario, original)
        self.assertEqual(result, optimal_assignment(scenario))
        teams = {team["id"]: i for i, team in enumerate(scenario["teams"])}
        zones = {zone["id"]: j for j, zone in enumerate(scenario["zones"])}
        assigned_teams = [a["team_id"] for a in result["assignments"]]
        assigned_zones = [a["zone_id"] for a in result["assignments"]]
        pending = result["pending_zones"]
        self.assertEqual(len(assigned_teams), len(set(assigned_teams)))
        self.assertEqual(len(assigned_zones), len(set(assigned_zones)))
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
        self.assertEqual(result["total_cost"], exhaustive_cost(scenario))
        self.assertLessEqual(result["total_cost"], greedy_assignment(scenario)["total_cost"])
        return result

    def test_initial_scenario_with_more_zones_than_teams(self):
        scenario = get_scenario()
        result = self.check_result(scenario)
        self.assertEqual(result, {
            "assignments": [
                {"team_id": "E1", "zone_id": "Z1"},
                {"team_id": "E2", "zone_id": "Z4"},
            ],
            "pending_zones": ["Z2", "Z3"],
            "assignment_cost": 20,
            "pending_penalty": 300,
            "total_cost": 320,
        })
        self.assertEqual(greedy_assignment(scenario)["total_cost"], 410)

    def test_no_available_teams(self):
        scenario = get_scenario()
        for team in scenario["teams"]:
            team["available"] = False
        result = self.check_result(scenario)
        self.assertEqual(result["assignments"], [])
        self.assertEqual(result["total_cost"], 900)

    def test_all_pairs_incompatible(self):
        scenario = get_scenario()
        scenario["costs"] = [[None] * 4, [None] * 4]
        self.assertEqual(self.check_result(scenario)["total_cost"], 900)

    def test_expensive_teams_can_remain_unused(self):
        scenario = get_scenario()
        scenario["costs"] = [[1000] * 4, [1000] * 4]
        result = self.check_result(scenario)
        self.assertEqual(result["assignments"], [])
        self.assertEqual(result["assignment_cost"], 0)
        self.assertEqual(result["total_cost"], 900)

    def test_unavailable_cheaper_team_is_excluded(self):
        scenario = get_scenario()
        scenario["teams"][1]["available"] = False
        result = self.check_result(scenario)
        self.assertEqual(result["assignments"], [{"team_id": "E1", "zone_id": "Z1"}])

    def test_equal_optima(self):
        scenario = get_scenario()
        scenario["costs"] = [[4] * 4, [4] * 4]
        result = self.check_result(scenario)
        self.assertEqual({a["zone_id"] for a in result["assignments"]}, {"Z1", "Z4"})
        self.assertEqual(result["total_cost"], 308)

    def test_equal_assignment_cost_and_penalty(self):
        scenario = get_scenario()
        scenario["costs"] = [[z["penalty"] for z in scenario["zones"]]] * 2
        self.assertEqual(self.check_result(scenario)["total_cost"], 900)

    def test_exhaustive_comparison_on_small_scenarios(self):
        random = Random(2026)
        for case in range(100):
            with self.subTest(case=case):
                zone_count = random.randint(1, 4)
                team_count = random.randint(1, 3)
                priorities = [random.randint(1, 3) for _ in range(zone_count)]
                scenario = {
                    "simulated": True,
                    "zones": [
                        {"id": f"Z{j}", "name": f"Zona {j}",
                         "priority": p, "penalty": 100 * p}
                        for j, p in enumerate(priorities)
                    ],
                    "teams": [
                        {"id": f"E{i}", "name": f"Equipo {i}",
                         "available": random.choice([True, False])}
                        for i in range(team_count)
                    ],
                    "costs": [
                        [random.choice([None, 0, 2.5, 10, 100, 200, 500])
                         for _ in range(zone_count)]
                        for _ in range(team_count)
                    ],
                }
                self.check_result(scenario)

    def test_invalid_scenario_is_rejected(self):
        scenario = get_scenario()
        scenario["costs"][0][0] = float("nan")
        with self.assertRaises(ValueError):
            optimal_assignment(scenario)
