import streamlit as st


def unserved_priority(scenario, result):
    priorities = {zone["id"]: zone["priority"] for zone in scenario["zones"]}
    return sum(priorities[zone] for zone in result["pending_zones"])


def show_unserved_priority(scenario, reference, optimized):
    quick = unserved_priority(scenario, reference)
    best = unserved_priority(scenario, optimized)
    with st.container(border=True):
        st.markdown("**Unserved priority**")
        st.caption("Priority points left pending. Lower is better.")
        left, right = st.columns(2)
        left.write(f"Quick decisions: **{quick} priority points unserved.**")
        right.write(f"Best allocation: **{best} priority points unserved.**")
        difference = quick - best
        if difference > 0:
            st.write(
                "Optimization leaves fewer high-priority needs unserved. "
                f"The sum is lower by {difference} priority {'point' if difference == 1 else 'points'}."
            )
        elif difference == 0:
            st.write("Both strategies leave the same sum of priority points unserved.")
        else:
            st.write(
                f"Best allocation leaves {-difference} more priority {'point' if difference == -1 else 'points'} unserved. "
                "It minimizes total cost, not this indicator alone."
            )
        st.caption(
            "Sum of priorities for pending zones, not the number of zones or measured harm. "
            "In this model, pending penalty = 100 × unserved priority."
        )
