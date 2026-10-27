from copy import deepcopy

import streamlit as st

from optimizer import optimal_assignment


def simulate_e2_unavailable(scenario):
    alternative = deepcopy(scenario)
    team = next(t for t in alternative["teams"] if t["id"] == "E2")
    team["available"] = False
    current = optimal_assignment(scenario)
    what_if = optimal_assignment(alternative)
    return {
        "current": current,
        "what_if": what_if,
        "cost_increase": what_if["total_cost"] - current["total_cost"],
    }


def show_scenario_lab(scenario):
    st.divider()
    st.subheader("Scenario Lab")
    st.caption("What happens when a response team becomes unavailable?")
    if st.button("Simulate E2 unavailable", key="simulate_e2"):
        st.session_state["scenario_lab_active"] = True
    if not st.session_state.get("scenario_lab_active", False):
        st.caption("Try an alternative without changing the controls above.")
        return
    if not next(t for t in scenario["teams"] if t["id"] == "E2")["available"]:
        st.info("E2 is already unavailable in this scenario.")
        return

    comparison = simulate_e2_unavailable(scenario)
    current, what_if = comparison["current"], comparison["what_if"]
    with st.container(border=True):
        before, after, change = st.columns(3)
        before.metric("Current optimized cost", current["total_cost"])
        after.metric("What-if optimized cost", what_if["total_cost"])
        change.metric("Cost increase", f"{comparison['cost_increase']:+g}")
        st.caption("Synthetic cost units, not money. Main controls remain unchanged.")
        before, after = st.columns(2)
        for column, title, result in ((before, "Current", current), (after, "Without E2", what_if)):
            with column:
                st.markdown(f"**{title} · Zones served: {len(result['assignments'])}**")
                served = sorted(a["zone_id"] for a in result["assignments"])
                st.write("Served: " + (", ".join(served) or "None"))
                st.write("Pending: " + (", ".join(sorted(result["pending_zones"])) or "None"))
        if comparison["cost_increase"] > 0:
            st.write(
                f"Losing E2 increases the optimized cost from {current['total_cost']:g} "
                f"to {what_if['total_cost']:g}."
            )
            if len(what_if["assignments"]) < len(current["assignments"]):
                st.caption("The optimized allocation serves fewer zones with E2 unavailable.")
        else:
            st.write("Removing E2 leaves the optimized total cost unchanged for these inputs.")
        st.caption("This comparison recalculates when you change the scenario or controls.")
