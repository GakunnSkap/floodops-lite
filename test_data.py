import unittest

from data import get_scenario, validate_scenario


class ScenarioTests(unittest.TestCase):
    def test_initial_scenario(self):
        scenario = get_scenario()
        self.assertTrue(scenario["simulated"])
        self.assertEqual(len(scenario["zones"]), 4)
        self.assertEqual(len(scenario["teams"]), 2)
        self.assertEqual([len(row) for row in scenario["costs"]], [4, 4])
        self.assertEqual(sum(c is None for row in scenario["costs"] for c in row), 2)
        for key in ("zones", "teams"):
            ids = [record["id"] for record in scenario[key]]
            self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            [zone["penalty"] for zone in scenario["zones"]], [300, 200, 100, 300]
        )

    def test_loads_are_independent(self):
        first = get_scenario()
        first["zones"][0]["priority"] = 1
        first["teams"][0]["available"] = False
        first["costs"][0][0] = 99
        second = get_scenario()
        self.assertEqual(second["zones"][0]["priority"], 3)
        self.assertTrue(second["teams"][0]["available"])
        self.assertEqual(second["costs"][0][0], 8)

    def test_rejects_invalid_costs(self):
        for cost in (-1, float("nan"), float("inf"), 10**400, "8", True):
            with self.subTest(cost=cost):
                scenario = get_scenario()
                scenario["costs"][0][0] = cost
                with self.assertRaises(ValueError):
                    validate_scenario(scenario)

    def test_rejects_invalid_records(self):
        cases = [
            ("zones", "id", "Z2"),
            ("teams", "id", "E2"),
            ("zones", "priority", 0),
            ("zones", "priority", True),
            ("zones", "penalty", 0),
            ("zones", "penalty", float("nan")),
            ("zones", "name", " "),
            ("teams", "name", None),
            ("teams", "available", 1),
        ]
        for group, field, value in cases:
            with self.subTest(group=group, field=field, value=value):
                scenario = get_scenario()
                scenario[group][0][field] = value
                with self.assertRaises(ValueError):
                    validate_scenario(scenario)

    def test_rejects_wrong_dimensions_and_missing_simulation_label(self):
        for field, value in (
            ("costs", [[1, 2, 3, 4]]),
            ("costs", [[1], [2]]),
            ("simulated", False),
            ("simulated", 1),
            ("zones", []),
        ):
            with self.subTest(field=field, value=value):
                scenario = get_scenario()
                scenario[field] = value
                with self.assertRaises(ValueError):
                    validate_scenario(scenario)

    def test_names_do_not_need_a_simulation_keyword(self):
        scenario = get_scenario()
        scenario["zones"][0]["name"] = "Zona A"
        scenario["teams"][0]["name"] = "Equipo 1"
        validate_scenario(scenario)
        del scenario["simulated"]
        with self.assertRaises(ValueError):
            validate_scenario(scenario)

    def test_unavailable_teams_and_incompatible_pairs_are_valid_data(self):
        scenario = get_scenario()
        for team in scenario["teams"]:
            team["available"] = False
        scenario["costs"] = [[None] * 4 for _ in scenario["teams"]]
        scenario["costs"][0][0] = 0
        validate_scenario(scenario)
