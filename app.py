import streamlit as st

from baseline import greedy_assignment
from data import SCENARIOS, get_scenario
from optimizer import optimal_assignment
from visualization import assignment_chart


def show_result(title, result, scenario):
    st.subheader(title)
    st.metric("Total cost", result["total_cost"])
    st.write(
        f"{len(result['assignments'])} served · "
        f"{len(result['pending_zones'])} pending"
    )
    st.caption(
        f"Assignment cost: {result['assignment_cost']} · "
        f"Pending penalties: {result['pending_penalty']}"
    )
    zones = {zone["id"]: zone for zone in scenario["zones"]}
    teams = {team["id"]: i for i, team in enumerate(scenario["teams"])}
    zone_positions = {zone["id"]: j for j, zone in enumerate(scenario["zones"])}
    if result["assignments"]:
        st.table([
            {"Team": a["team_id"], "Zone": a["zone_id"],
             "Cost": scenario["costs"][teams[a["team_id"]]][zone_positions[a["zone_id"]]]}
            for a in result["assignments"]
        ])
    else:
        st.write("No teams assigned.")
    st.write("Pending zones")
    if result["pending_zones"]:
        st.table([
            {"Zone": z, "Name": zones[z]["name"], "Penalty": zones[z]["penalty"]}
            for z in result["pending_zones"]
        ])
    else:
        st.write("No pending zones.")


st.set_page_config(page_title="FloodOps Lite", layout="wide")
st.title("FloodOps Lite")
st.write(
    "Compare response-team assignments under limited resources "
    "in an educational flood scenario for Guayaquil, Ecuador."
)
st.caption(
    "Simulated zones, teams and costs. No operational data or emergency guidance."
)

try:
    scenario = get_scenario()
    with st.sidebar:
        st.header("Scenario")
        st.caption("Changes apply to this session; source data stays unchanged.")
        scenario_name = st.selectbox("Demo scenario", SCENARIOS, key="scenario_name")
        if st.session_state.get("loaded_scenario") != scenario_name:
            if scenario_name != "Default scenario":
                scenario = get_scenario(scenario_name)
            for team in scenario["teams"]:
                st.session_state[f"available_{team['id']}"] = team["available"]
            for zone in scenario["zones"]:
                st.session_state[f"priority_{zone['id']}"] = zone["priority"]
            st.session_state["loaded_scenario"] = scenario_name
        st.caption("Selecting a preset resets the controls below. You can then edit them.")
        st.subheader("Team availability")
        for team in scenario["teams"]:
            team["available"] = st.checkbox(
                f"{team['id']} — {team['name']}",
                key=f"available_{team['id']}",
            )
        st.subheader("Zone priority")
        st.caption("1 = low · 2 = medium · 3 = high. Pending penalty = 100 × priority.")
        for zone in scenario["zones"]:
            zone["priority"] = st.selectbox(
                f"{zone['id']} — {zone['name']}", [1, 2, 3],
                key=f"priority_{zone['id']}",
            )
            zone["penalty"] = 100 * zone["priority"]
        st.caption("Both methods recalculate automatically after each change.")
    reference = greedy_assignment(scenario)
    optimized = optimal_assignment(scenario)
except ValueError:
    st.error("Invalid scenario. Check priorities, availability and assignment costs.")
    st.stop()

st.subheader("Summary")
zones_column, teams_column, reduction_column = st.columns(3)
zones_column.metric("Zones", len(scenario["zones"]))
teams_column.metric("Available teams", sum(t["available"] for t in scenario["teams"]))
reference_cost = reference["total_cost"]
optimized_cost = optimized["total_cost"]
reduction = (reference_cost - optimized_cost) / reference_cost * 100 if reference_cost else None
reduction_column.metric("Objective reduction", f"{reduction:.2f}%" if reduction is not None else "N/A")
if reference_cost == optimized_cost:
    st.info("Both methods have the same total cost for this scenario.")
if reference_cost == 0:
    st.caption("Percentage reduction is undefined when the reference cost is zero.")

st.subheader("Comparison")
left, right = st.columns(2)
with left:
    show_result("Greedy reference", reference, scenario)
with right:
    show_result("Optimized", optimized, scenario)

reference_pairs = {a["team_id"]: a["zone_id"] for a in reference["assignments"]}
optimized_pairs = {a["team_id"]: a["zone_id"] for a in optimized["assignments"]}
changes = [
    f"{team}: {reference_pairs.get(team, 'unused')} → {optimized_pairs.get(team, 'unused')}"
    for team in sorted(reference_pairs.keys() | optimized_pairs.keys())
    if reference_pairs.get(team) != optimized_pairs.get(team)
]
st.write("Assignment changes: " + "; ".join(changes) if changes else "Both methods choose the same assignments.")
st.caption(
    "Optimized minus reference, in synthetic units: "
    f"assignment cost {optimized['assignment_cost'] - reference['assignment_cost']:+g}; "
    f"pending penalties {optimized['pending_penalty'] - reference['pending_penalty']:+g}; "
    f"total {optimized_cost - reference_cost:+g}."
)

st.subheader("Illustrative assignment view")
st.caption(
    "Schematic layout, not a geographic map. Positions are illustrative, not real "
    "locations in Guayaquil. Dashed links show assignments, not roads or safe routes."
)
method = st.radio("Method", ["Greedy reference", "Optimized"], horizontal=True)
selected = reference if method == "Greedy reference" else optimized
try:
    st.vega_lite_chart(assignment_chart(scenario, selected), width="stretch", theme=None)
except (ValueError, RuntimeError):
    st.warning("The illustrative view is unavailable. Use the comparison tables above.")
st.caption(
    "Squares = teams · Circles = simulated zones. Hover for details. "
    "The same positions are used for both methods. No map tiles or external data "
    "services are required; the tables above remain available if the chart cannot load."
)

st.subheader("How to read the results")
st.write(
    "Total cost = assignment costs + penalties for pending zones. "
    "The reference visits higher-penalty zones first and picks the cheapest free "
    "compatible team. The optimizer minimizes the total across all valid assignments, "
    "including leaving teams unused."
)
st.caption(
    "One round: at most one zone per available team and one team per zone; "
    "incompatible pairs are forbidden. Priority is a preference through penalties, "
    "not guaranteed service. Costs are synthetic units, not response times, money "
    "or measured impact. Different assignments may share the same optimal cost."
)
