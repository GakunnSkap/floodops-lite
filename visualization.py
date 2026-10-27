"""Charts for synthetic costs and illustrative, non-geographic assignments."""


def cost_chart(reference, optimized):
    segments = []
    labels = []
    for method, result in (("Greedy reference", reference), ("Optimized", optimized)):
        assignment = result["assignment_cost"]
        penalty = result["pending_penalty"]
        total = result["total_cost"]
        segments.extend([
            {"method": method, "component": "Assignment cost", "cost": assignment,
             "start": 0, "end": assignment},
            {"method": method, "component": "Pending penalty", "cost": penalty,
             "start": assignment, "end": total},
        ])
        labels.append({"method": method, "label": f"{assignment:g} + {penalty:g} = {total:g}"})
    return {
        "description": "Synthetic assignment costs and pending penalties for Greedy reference and Optimized. See the comparison tables for exact values.",
        "height": 230,
        "background": "#182a3a",
        "padding": {"left": 12, "right": 12, "top": 12, "bottom": 12},
        "config": {
            "view": {"stroke": None},
            "axis": {
                "labelColor": "#c0ced8", "titleColor": "#c0ced8",
                "domainColor": "#59788d", "tickColor": "#59788d",
                "gridColor": "#365065",
            },
            "legend": {"labelColor": "#edf4f7"},
        },
        "encoding": {"y": {"field": "method", "type": "nominal",
                            "sort": ["Greedy reference", "Optimized"],
                            "axis": {"title": None, "labelLimit": 120}}},
        "layer": [
            {
                "data": {"values": segments},
                "mark": {"type": "bar", "size": 24},
                "encoding": {
                    "x": {"field": "start", "type": "quantitative",
                          "scale": {"domain": [0, max(reference["total_cost"], optimized["total_cost"], 1)]},
                          "axis": {"title": "Synthetic cost", "tickCount": 3}},
                    "x2": {"field": "end"},
                    "color": {"field": "component", "type": "nominal",
                              "scale": {"domain": ["Assignment cost", "Pending penalty"],
                                        "range": ["#59c1bd", "#efb86a"]},
                              "legend": {"title": None, "orient": "bottom", "columns": 1}},
                    "tooltip": [{"field": "method", "title": "Method"},
                                {"field": "component", "title": "Component"},
                                {"field": "cost", "title": "Synthetic cost"}],
                },
            },
            {
                "data": {"values": labels},
                "mark": {"type": "text", "align": "left", "dy": -23,
                         "color": "#edf4f7", "fontSize": 12},
                "encoding": {"x": {"value": 0}, "text": {"field": "label"}},
            },
        ],
    }


def assignment_chart(scenario, result):
    points = []
    assigned_teams = {a["team_id"] for a in result["assignments"]}
    pending = set(result["pending_zones"])
    for kind, records, x in (("Team", scenario["teams"], 0), ("Zone", scenario["zones"], 1)):
        half_height = min(0.085, 0.35 / (len(records) + 1))
        for index, record in enumerate(sorted(records, key=lambda r: r["id"])):
            if kind == "Zone":
                status = "Pending" if record["id"] in pending else "Served"
            else:
                status = "Unavailable" if not record["available"] else (
                    "Assigned" if record["id"] in assigned_teams else "Available"
                )
            points.append({
                "id": record["id"], "name": record["name"], "kind": kind,
                "x": x, "y": 1 - (index + 1) / (len(records) + 1),
                "x0": x - 0.16, "x1": x + 0.16,
                "y0": 1 - (index + 1) / (len(records) + 1) - half_height,
                "y1": 1 - (index + 1) / (len(records) + 1) + half_height,
                "status_y": 1 - (index + 1) / (len(records) + 1) - 0.035,
                "status": status, "priority": record.get("priority"),
                "penalty": record.get("penalty"),
            })
    positions = {(p["kind"], p["id"]): p for p in points}
    links = []
    for assignment in result["assignments"]:
        team = positions["Team", assignment["team_id"]]
        zone = positions["Zone", assignment["zone_id"]]
        links.append({
            "team": team["id"], "zone": zone["id"],
            "x": team["x"], "y": team["y"], "x2": zone["x"], "y2": zone["y"],
            "label": f"{team['id']} → {zone['id']}",
            "label_y": (team["y"] + zone["y"]) / 2,
        })
    return {
        "description": "Illustrative assignment board. " + "; ".join(
            f"{a['team_id']} assigned to {a['zone_id']}" for a in result["assignments"]
        ) + ". Pending zones: " + (", ".join(sorted(result["pending_zones"])) or "none") + ". Not geographic locations or routes.",
        "height": 400,
        "background": "#132332",
        "padding": {"left": 12, "right": 12, "top": 20, "bottom": 12},
        "config": {"legend": {"labelColor": "#c0ced8"}, "view": {"stroke": None}},
        "encoding": {
            "x": {"field": "x", "type": "quantitative", "axis": None,
                  "scale": {"domain": [-0.35, 1.35]}},
            "y": {"field": "y", "type": "quantitative", "axis": None,
                  "scale": {"domain": [0, 1.12]}},
        },
        "layer": [
            {
                "data": {"values": links},
                "mark": {"type": "rule", "color": "#59c1bd", "strokeWidth": 2.5, "opacity": 0.82},
                "encoding": {
                    "x2": {"field": "x2"}, "y2": {"field": "y2"},
                    "tooltip": [{"field": "team", "title": "Team"},
                                {"field": "zone", "title": "Assigned zone"}],
                },
            },
            {
                "data": {"values": points},
                "mark": {
                    "type": "rect", "cornerRadius": 12,
                    "stroke": "#59788d", "strokeWidth": 1.2, "opacity": 1,
                },
                "encoding": {
                    "x": {"field": "x0", "type": "quantitative"},
                    "x2": {"field": "x1"},
                    "y": {"field": "y0", "type": "quantitative"},
                    "y2": {"field": "y1"},
                    "color": {
                        "field": "status", "type": "nominal",
                        "scale": {
                            "domain": ["Served", "Pending", "Assigned", "Available", "Unavailable"],
                            "range": ["#164449", "#4c3925", "#204354", "#223c4d", "#2e3a46"],
                        },
                        "legend": None,
                    },
                    "tooltip": [{"field": f, "type": "nominal"}
                                for f in ("id", "name", "kind", "status", "priority", "penalty")],
                },
            },
            {
                "data": {"values": points},
                "mark": {"type": "text", "fontSize": 15, "fontWeight": 700, "color": "#edf4f7"},
                "encoding": {
                    "text": {"field": "id", "type": "nominal"},
                    "y": {"field": "y", "type": "quantitative"},
                },
            },
            {
                "data": {"values": points},
                "mark": {"type": "text", "fontSize": 10, "color": "#c0ced8"},
                "encoding": {
                    "text": {"field": "status", "type": "nominal"},
                    "y": {"field": "status_y", "type": "quantitative"},
                },
            },
            {
                "data": {"values": [
                    {"x": 0, "y": 1.04, "label": "Teams"},
                    {"x": 1, "y": 1.04, "label": "Zones"},
                ]},
                "mark": {"type": "text", "fontSize": 11, "fontWeight": 700, "color": "#b4c5d2"},
                "encoding": {
                    "x": {"field": "x", "type": "quantitative"},
                    "y": {"field": "y", "type": "quantitative"},
                    "text": {"field": "label"},
                },
            },
            {
                "data": {"values": links},
                "mark": {"type": "text", "dy": -12, "fontSize": 11,
                         "fontWeight": 600, "color": "#edf4f7"},
                "encoding": {
                    "x": {"datum": 0.5},
                    "y": {"field": "label_y", "type": "quantitative"},
                    "text": {"field": "label"},
                },
            },
        ],
    }
