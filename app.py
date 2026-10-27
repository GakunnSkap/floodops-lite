import streamlit as st

from baseline import greedy_assignment
from data import SCENARIOS, get_scenario
from explanation import explain_decisions
from optimizer import optimal_assignment
from visualization import assignment_chart, cost_chart


def show_result(title, result, scenario):
    st.markdown(f"**{title}**")
    st.caption("Priority-first heuristic" if title == "Greedy reference" else "Global cost minimum")
    st.metric("Total cost", result["total_cost"], border=True)
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
    st.markdown("**Pending zones**")
    if result["pending_zones"]:
        st.table([
            {"Zone": z, "Name": zones[z]["name"], "Penalty": zones[z]["penalty"]}
            for z in result["pending_zones"]
        ])
    else:
        st.write("No pending zones.")


st.set_page_config(page_title="FloodOps Lite", layout="wide")
st.caption("IEEE-HKN HACK2IMPACT 2026 · EDUCATIONAL PROTOTYPE")
st.title("FloodOps Lite")
st.write(
    "Compare response-team assignments under limited resources "
    "in an educational flood scenario for Guayaquil, Ecuador."
)
with st.container(border=True):
    st.markdown(
        "**Synthetic data only** · Simulated zones, teams and costs. "
        "No operational data or emergency guidance."
    )

try:
    scenario = get_scenario()
    with st.sidebar:
        st.header("Explore a scenario")
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
        st.divider()
        st.subheader("Team availability")
        for team in scenario["teams"]:
            team["available"] = st.checkbox(
                f"{team['id']} — {team['name']}",
                key=f"available_{team['id']}",
            )
        st.divider()
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
zones_column.metric("Zones", len(scenario["zones"]), border=True)
teams_column.metric("Available teams", sum(t["available"] for t in scenario["teams"]), border=True)
reference_cost = reference["total_cost"]
optimized_cost = optimized["total_cost"]
reduction = (reference_cost - optimized_cost) / reference_cost * 100 if reference_cost else None
reduction_column.metric("Objective reduction", f"{reduction:.2f}%" if reduction is not None else "N/A", border=True)
from priority_indicator import show_unserved_priority

show_unserved_priority(scenario, reference, optimized)

if reference_cost == optimized_cost:
    st.info("Both methods have the same total cost for this scenario.")
if reference_cost == 0:
    st.caption("Percentage reduction is undefined when the reference cost is zero.")

st.caption("All costs use synthetic units. Lower total cost is better.")
st.subheader("Cost breakdown")
st.caption("Assignment cost + pending penalty = total cost.")
try:
    st.vega_lite_chart(cost_chart(reference, optimized), width="stretch", theme=None)
except (ValueError, RuntimeError):
    st.caption("Cost chart unavailable. The metrics and comparison tables remain available.")
st.divider()
st.subheader("Comparison")
left, right = st.columns(2)
with left:
    with st.container(border=True):
        show_result("Greedy reference", reference, scenario)
with right:
    with st.container(border=True):
        show_result("Optimized", optimized, scenario)

st.subheader("Why do the assignments differ?")
with st.container(border=True):
    for line in explain_decisions(scenario, reference, optimized):
        st.write(line)
st.caption(
    "Optimized minus reference, in synthetic units: "
    f"assignment cost {optimized['assignment_cost'] - reference['assignment_cost']:+g}; "
    f"pending penalties {optimized['pending_penalty'] - reference['pending_penalty']:+g}; "
    f"total {optimized_cost - reference_cost:+g}."
)

st.divider()
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

st.divider()
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

from scenario_lab import show_scenario_lab

show_scenario_lab(scenario)
