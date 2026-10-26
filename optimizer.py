"""Asignación óptima con penalizaciones explícitas para zonas pendientes."""

from math import inf

from scipy.optimize import linear_sum_assignment

from data import validate_scenario


def optimal_assignment(scenario):
    validate_scenario(scenario)
    zones = scenario["zones"]
    teams = scenario["teams"]
    costs = scenario["costs"]
    available = sorted(
        (i for i, team in enumerate(teams) if team["available"]),
        key=lambda i: teams[i]["id"],
    )
    zone_order = sorted(range(len(zones)), key=lambda j: zones[j]["id"])
    matrix = [
        [costs[i][j] if costs[i][j] is not None else inf for i in available]
        + [zones[j]["penalty"]] * len(zones)
        for j in zone_order
    ]
    rows, columns = linear_sum_assignment(matrix)
    assignments = []
    pending_zones = []
    assignment_cost = 0
    pending_penalty = 0
    for row, column in zip(rows, columns):
        j = zone_order[row]
        if column < len(available):
            i = available[column]
            assignments.append({"team_id": teams[i]["id"], "zone_id": zones[j]["id"]})
            assignment_cost += costs[i][j]
        else:
            pending_zones.append(zones[j]["id"])
            pending_penalty += zones[j]["penalty"]
    return {
        "assignments": assignments,
        "pending_zones": pending_zones,
        "assignment_cost": assignment_cost,
        "pending_penalty": pending_penalty,
        "total_cost": assignment_cost + pending_penalty,
    }
