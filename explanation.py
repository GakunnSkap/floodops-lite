def explain_decisions(scenario, reference, optimized):
    reference_pairs = {a["team_id"]: a["zone_id"] for a in reference["assignments"]}
    optimized_pairs = {a["team_id"]: a["zone_id"] for a in optimized["assignments"]}
    changes = [
        f"{team}: {reference_pairs.get(team, 'unused')} → {optimized_pairs.get(team, 'unused')}"
        for team in sorted(reference_pairs.keys() | optimized_pairs.keys())
        if reference_pairs.get(team) != optimized_pairs.get(team)
    ]
    lines = ["Assignment changes: " + "; ".join(changes) if changes
             else "Both methods choose the same assignments."]
    difference = reference["total_cost"] - optimized["total_cost"]
    if difference == 0:
        lines.append("Different assignments, equal objective: both alternatives have the same total cost."
                     if changes else "Equal assignments and equal total cost for the current inputs.")
    else:
        lines.append(f"Optimized total cost is {difference:g} synthetic units lower.")

    reference_zones = {zone: team for team, zone in reference_pairs.items()}
    optimized_zones = {zone: team for team, zone in optimized_pairs.items()}
    newly_served = sorted(optimized_zones.keys() - reference_zones.keys())
    newly_pending = sorted(reference_zones.keys() - optimized_zones.keys())
    if newly_served:
        lines.append("Pending → served: " + ", ".join(newly_served) + ".")
    if newly_pending:
        lines.append("Served → pending: " + ", ".join(newly_pending) + ".")
    for zone in sorted(reference_zones.keys() & optimized_zones.keys()):
        if reference_zones[zone] != optimized_zones[zone]:
            lines.append(f"{zone} changes team: {reference_zones[zone]} → {optimized_zones[zone]}.")
    for zone in newly_served:
        column = next(j for j, record in enumerate(scenario["zones"]) if record["id"] == zone)
        compatible = [team["id"] for i, team in enumerate(scenario["teams"])
                      if team["available"] and scenario["costs"][i][column] is not None]
        if len(compatible) == 1:
            team = compatible[0]
            if team in reference_pairs:
                lines.append(
                    f"{team} is the only available team compatible with {zone}. "
                    f"Greedy uses {team} for {reference_pairs[team]}, leaving no free "
                    f"compatible team for {zone}."
                )
    return lines
