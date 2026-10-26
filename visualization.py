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
        "height": 230,
        "background": "#f4f5f7",
        "padding": {"left": 12, "right": 12, "top": 12, "bottom": 12},
        "config": {
            "view": {"stroke": None},
            "axis": {"labelColor": "#334155", "titleColor": "#334155"},
            "legend": {"labelColor": "#334155"},
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
                                        "range": ["#367da2", "#c58b36"]},
                              "legend": {"title": None, "orient": "bottom", "columns": 1}},
                    "tooltip": [{"field": "method", "title": "Method"},
                                {"field": "component", "title": "Component"},
                                {"field": "cost", "title": "Synthetic cost"}],
                },
            },
            {
                "data": {"values": labels},
                "mark": {"type": "text", "align": "left", "dy": -23,
                         "color": "#334155", "fontSize": 12},
                "encoding": {"x": {"value": 0}, "text": {"field": "label"}},
            },
        ],
    }


def assignment_chart(scenario, result):
    points = []
    assigned_teams = {a["team_id"] for a in result["assignments"]}
    pending = set(result["pending_zones"])
    for kind, records, x in (("Team", scenario["teams"], 0), ("Zone", scenario["zones"], 1)):
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
        })
    return {
        "height": 340,
        "background": "#f4f5f7",
        "config": {"legend": {"labelColor": "#334155"}, "view": {"stroke": None}},
        "encoding": {
            "x": {"field": "x", "type": "quantitative", "axis": None,
                  "scale": {"domain": [-0.2, 1.2]}},
            "y": {"field": "y", "type": "quantitative", "axis": None,
                  "scale": {"domain": [0, 1]}},
        },
        "layer": [
            {
                "data": {"values": links},
                "mark": {"type": "rule", "color": "#567c9d", "strokeDash": [6, 4]},
                "encoding": {
                    "x2": {"field": "x2"}, "y2": {"field": "y2"},
                    "tooltip": [{"field": "team", "title": "Team"},
                                {"field": "zone", "title": "Assigned zone"}],
                },
            },
            {
                "data": {"values": points},
                "mark": {"type": "point", "filled": True, "size": 220, "opacity": 1},
                "encoding": {
                    "color": {
                        "field": "status", "type": "nominal",
                        "scale": {
                            "domain": ["Served", "Pending", "Assigned", "Available", "Unavailable"],
                            "range": ["#367da2", "#c58b36", "#367da2", "#49856a", "#888888"],
                        },
                        "legend": {"title": None, "orient": "bottom"},
                    },
                    "shape": {"field": "kind", "type": "nominal",
                              "scale": {"domain": ["Team", "Zone"], "range": ["square", "circle"]},
                              "legend": None},
                    "tooltip": [{"field": f, "type": "nominal"}
                                for f in ("id", "name", "kind", "status", "priority", "penalty")],
                },
            },
            {
                "data": {"values": points},
                "mark": {"type": "text", "dy": -20, "fontSize": 14, "color": "#334155"},
                "encoding": {"text": {"field": "id", "type": "nominal"}},
            },
        ],
    }
