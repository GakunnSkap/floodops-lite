"""Heurística voraz de referencia; no garantiza un costo total óptimo."""

from data import validate_scenario


def greedy_assignment(scenario):
    """Prioriza penalizaciones y elige el equipo compatible libre más barato."""
    validate_scenario(scenario)
    zones = scenario["zones"]
    teams = scenario["teams"]
    costs = scenario["costs"]
    free_teams = {i for i, team in enumerate(teams) if team["available"]}
    zone_order = sorted(
        range(len(zones)), key=lambda j: (-zones[j]["penalty"], zones[j]["id"])
    )
    assignments = []
    pending_zones = []
    assignment_cost = 0
    pending_penalty = 0

    for j in zone_order:
        candidates = [i for i in free_teams if costs[i][j] is not None]
        if not candidates:
            pending_zones.append(zones[j]["id"])
            pending_penalty += zones[j]["penalty"]
            continue
        i = min(candidates, key=lambda i: (costs[i][j], teams[i]["id"]))
        assignments.append({"team_id": teams[i]["id"], "zone_id": zones[j]["id"]})
        assignment_cost += costs[i][j]
        free_teams.remove(i)

    return {
        "assignments": assignments,
        "pending_zones": pending_zones,
        "assignment_cost": assignment_cost,
        "pending_penalty": pending_penalty,
        "total_cost": assignment_cost + pending_penalty,
    }
