from html import escape

import streamlit as st

from baseline import greedy_assignment
from data import SCENARIOS, get_scenario
from explanation import explain_decisions
from optimizer import optimal_assignment
from visualization import assignment_chart, cost_chart


PRIORITY_LABELS = {1: "Low", 2: "Medium", 3: "High"}


def _safe(value):
    return escape(str(value))


def _section_heading(number, title):
    st.markdown(
        f'<div class="fo-section-heading"><h2>{_safe(title)}</h2></div>',
        unsafe_allow_html=True,
    )


def _show_zone_cards(scenario, result):
    assignments = {item["zone_id"]: item["team_id"] for item in result["assignments"]}
    pending = set(result["pending_zones"])
    cards = []
    for zone in sorted(scenario["zones"], key=lambda item: item["id"]):
        zone_id = _safe(zone["id"])
        priority = zone["priority"]
        served = zone["id"] not in pending
        status = "Served" if served else "Pending"
        assigned_team = assignments.get(zone["id"])
        assignment = (
            f"Assigned to {_safe(assigned_team)}" if assigned_team else "No team assigned"
        )
        cards.append(
            f"""
            <article class="fo-zone-card {'served' if served else 'pending'}">
              <div class="fo-card-top">
                <span class="fo-id">{zone_id}</span>
                <span class="fo-priority priority-{PRIORITY_LABELS[priority].lower()}">
                  {PRIORITY_LABELS[priority]} priority
                </span>
              </div>
              <div class="fo-zone-name">{_safe(zone['name'])}</div>
              <div class="fo-card-bottom">
                <span class="fo-status"><i aria-hidden="true"></i>{status}</span>
                <span class="fo-assignment">{assignment}</span>
              </div>
            </article>
            """
        .strip())
    st.markdown(f'<div class="fo-zone-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def _show_team_cards(scenario, result):
    assignments = {item["team_id"]: item["zone_id"] for item in result["assignments"]}
    cards = []
    for team in sorted(scenario["teams"], key=lambda item: item["id"]):
        available = team["available"]
        assigned_zone = assignments.get(team["id"])
        availability = "Available" if available else "Unavailable"
        utilization = "In use" if assigned_zone else "Idle"
        team_class = "available" if available else "unavailable"
        cards.append(
            f"""
            <article class="fo-team-card {team_class}">
              <div class="fo-team-icon" aria-hidden="true"></div>
              <div class="fo-team-main">
                <div class="fo-card-top">
                  <span class="fo-id">{_safe(team['id'])}</span>
                  <span class="fo-status-pill">{availability}</span>
                </div>
                <div class="fo-zone-name">{_safe(team['name'])}</div>
                <div class="fo-team-meta">
                  <span>Zone: <strong>{_safe(assigned_zone or 'Unassigned')}</strong></span>
                  <span>Utilization: <strong>{utilization}</strong></span>
                </div>
              </div>
            </article>
            """
        .strip())
    st.markdown(f'<div class="fo-team-list">{"".join(cards)}</div>', unsafe_allow_html=True)


def _primary_insight(scenario, reference, optimized):
    reference_cost = reference["total_cost"]
    optimized_cost = optimized["total_cost"]
    difference = reference_cost - optimized_cost
    reference_assignments = {
        item["team_id"]: item["zone_id"] for item in reference["assignments"]
    }
    optimized_assignments = {
        item["team_id"]: item["zone_id"] for item in optimized["assignments"]
    }

    if difference == 0:
        if reference_assignments == optimized_assignments:
            return (
                "Both approaches reach the same total synthetic cost and choose "
                "the same assignments for these inputs."
            )
        return (
            "The assignments differ, but both approaches reach the same total "
            "synthetic cost. There is no objective improvement in this scenario."
        )

    reference_zones = {zone: team for team, zone in reference_assignments.items()}
    optimized_zones = {zone: team for team, zone in optimized_assignments.items()}
    newly_served = optimized_zones.keys() - reference_zones.keys()
    cost_columns = {zone["id"]: index for index, zone in enumerate(scenario["zones"])}
    for zone_id in sorted(newly_served):
        column = cost_columns[zone_id]
        compatible = [
            team["id"]
            for index, team in enumerate(scenario["teams"])
            if team["available"] and scenario["costs"][index][column] is not None
        ]
        if len(compatible) == 1:
            team_id = compatible[0]
            old_zone = reference_assignments.get(team_id)
            if optimized_assignments.get(team_id) == zone_id and old_zone:
                return (
                    f"{team_id} is the only available team compatible with {zone_id}. "
                    f"Best allocation reserves {team_id} for {zone_id} instead of "
                    f"{old_zone}, lowering the total synthetic objective by "
                    f"{difference:g} units."
                )

    if difference > 0:
        return (
            "Considering the whole round changes the assignment and lowers the "
            f"total synthetic objective by {difference:g} units."
        )
    return (
        "Quick decisions has a lower total synthetic objective for these inputs "
        f"by {abs(difference):g} units."
    )


def show_decision(title, subtitle, result):
    with st.container(border=True, key="decision_best" if title == "Best allocation" else "decision_quick"):
        st.subheader(title)
        st.caption(subtitle)
        st.metric("Synthetic total cost", result["total_cost"])
        st.markdown(
            f"""
            <div class="fo-count-row">
              <div><strong>{len(result['assignments'])}</strong><span>Zones served</span></div>
              <div><strong>{len(result['pending_zones'])}</strong><span>Zones pending</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        assignments = sorted(
            result["assignments"], key=lambda item: (item["zone_id"], item["team_id"])
        )
        assignment_text = "  ·  ".join(
            f"{_safe(item['team_id'])} → {_safe(item['zone_id'])}"
            for item in assignments
        ) or "No teams assigned"
        pending_text = "  ·  ".join(_safe(zone) for zone in sorted(result["pending_zones"]))
        st.markdown(
            f"""
            <div class="fo-decision-assignments">
              <div><span class="fo-label">Assignments</span><strong>{assignment_text}</strong></div>
              <div><span class="fo-label">Pending zones</span><strong>{pending_text or 'None'}</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        assignment_cost = result["assignment_cost"]
        pending_penalty = result["pending_penalty"]
        total_cost = result["total_cost"]
        assignment_share = assignment_cost / total_cost * 100 if total_cost else 0
        pending_share = pending_penalty / total_cost * 100 if total_cost else 0
        st.markdown(
            f"""
            <div class="fo-cost-track" aria-label="Synthetic cost components">
              <span style="width:{assignment_share:.2f}%"></span>
              <span style="width:{pending_share:.2f}%"></span>
            </div>
            <div class="fo-cost-legend">
              <span><i class="fo-cost-key assignment"></i>Assignment <b>{assignment_cost:g}</b></span>
              <span><i class="fo-cost-key penalty"></i>Pending penalty <b>{pending_penalty:g}</b></span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def show_tables(title, result, scenario):
    st.markdown(f"**{title}**")
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
st.markdown(
    """
    <style>
      :root {
        color-scheme: dark;
        --fo-bg: #101b27;
        --fo-panel: #182a3a;
        --fo-panel-raised: #203547;
        --fo-border: #365065;
        --fo-text: #edf4f7;
        --fo-muted: #b4c5d2;
        --fo-cyan: #59c1bd;
        --fo-orange: #efb86a;
      }
      .stApp {
        background: var(--fo-bg); color: var(--fo-text);
        font-family: "DejaVu Sans", "Segoe UI", sans-serif;
      }
      [data-testid="stHeader"] { background: transparent; }
      section.main .block-container, [data-testid="stMainBlockContainer"] {
        max-width: 1320px; padding: 2.5rem 2.2rem 2.5rem;
      }
      h1, h2, h3 { color: var(--fo-text); letter-spacing: -.035em; }
      h1 { font-size: clamp(2.2rem, 3.4vw, 3rem) !important; margin-bottom: .1rem; }
      h2 { font-size: clamp(1.25rem, 1.8vw, 1.55rem) !important; margin-top: .2rem; }
      p, label, [data-testid="stCaptionContainer"] { color: var(--fo-muted); }
      [data-testid="stMetric"] {
        background: var(--fo-panel); border: 1px solid var(--fo-border);
        border-left: 3px solid #566e67; border-radius: 4px; padding: 12px 15px;
      }
      [data-testid="stMetricLabel"] { color: var(--fo-muted); }
      [data-testid="stMetricValue"] { color: var(--fo-text); }
      [data-testid="stMetricDelta"] { color: var(--fo-cyan); }
      [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--fo-panel); border-color: var(--fo-border);
        border-radius: 6px;
      }
      [data-testid="stExpander"] {
        background: var(--fo-panel); border: 1px solid var(--fo-border);
        border-radius: 5px;
      }
      [data-testid="stSelectbox"] label, [data-testid="stCheckbox"] label {
        color: var(--fo-text);
      }
      [data-testid="stRadio"] label { color: var(--fo-text); }
      hr { border-color: var(--fo-border); margin: 1.25rem 0; }
      [data-testid="stBaseButton-secondary"] {
        border-radius: 4px; border-color: var(--fo-border);
      }
      [data-baseweb="select"] > div, [data-baseweb="input"] > div {
        border-radius: 4px;
      }
      .fo-section-heading {
        display:flex; align-items:baseline; gap:.75rem; margin:.2rem 0 .45rem;
      }
      .fo-section-heading > span {
        color:var(--fo-orange); font:700 .72rem/1 "SFMono-Regular",Consolas,monospace;
        letter-spacing:.08em;
      }
      .fo-section-heading h2 {
        margin:0; color:var(--fo-text); font-size:1.45rem !important;
      }
      .fo-hero {
        display:flex; justify-content:space-between; align-items:center;
        gap:1rem; margin:.1rem 0 1rem; padding:.35rem 0 1.15rem;
        border-bottom:1px solid var(--fo-border);
      }
      .fo-eyebrow, .fo-label {
        color:var(--fo-cyan); font-size:.68rem; font-weight:700;
        letter-spacing:normal; text-transform:none;
      }
      .fo-subtitle { color:#c0ced8; font-size:1rem; margin:.25rem 0 .1rem; }
      .fo-synthetic {
        display:inline-flex; align-items:center; gap:.55rem; white-space:nowrap;
        color:#c6d0ca; border:1px solid var(--fo-border); border-radius:3px;
        padding:.5rem .7rem; font-size:.75rem; font-weight:600;
      }
      .fo-synthetic:before {
        content:""; width:.45rem; height:.45rem; background:var(--fo-orange);
        display:inline-block;
      }
      .fo-round {
        height:100%; min-height:82px; box-sizing:border-box;
        display:flex; align-items:center; gap:1rem;
        background:var(--fo-panel); border:1px solid var(--fo-border);
        border-radius:4px; padding:12px 16px;
      }
      .fo-round-icon {
        color:var(--fo-orange); font:600 1.1rem/1 "SFMono-Regular",Consolas,monospace;
        border:1px solid #594735; padding:.55rem;
      }
      .fo-round-copy { display:flex; flex:1; flex-direction:column; gap:.2rem; }
      .fo-round-copy span { color:var(--fo-muted); font-size:.82rem; }
      .fo-round-copy strong { color:var(--fo-text); font-size:1.32rem; }
      .fo-gap-note {
        background:#241e17; border:1px solid #594735; border-left:3px solid var(--fo-orange);
        border-radius:3px; color:#e7c89e; padding:.65rem .85rem;
        margin:.65rem 0 1.15rem; font-size:.9rem;
      }
      .fo-zone-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.55rem; }
      .fo-zone-card, .fo-team-card {
        background:#182a3a; border:1px solid var(--fo-border);
        border-radius:4px; padding:.85rem .9rem; min-width:0;
      }
      .fo-zone-card.served { border-left:3px solid var(--fo-cyan); }
      .fo-zone-card.pending { border-left:3px solid var(--fo-orange); }
      .fo-card-top { display:flex; align-items:baseline; gap:.5rem; flex-wrap:wrap; }
      .fo-id {
        color:var(--fo-text); font:700 1.13rem/1.2 "SFMono-Regular",Consolas,monospace;
        letter-spacing:-.04em;
      }
      .fo-priority {
        margin-left:auto; font:600 .61rem/1.2 "SFMono-Regular",Consolas,monospace;
        letter-spacing:.06em;
      }
      .priority-high { color:#e7b27e; }
      .priority-medium { color:#c5c6a0; }
      .priority-low { color:#9cbd9f; }
      .fo-zone-name { color:#c0ced8; margin:.45rem 0 .65rem; font-size:.84rem; }
      .fo-card-bottom {
        display:flex; justify-content:space-between; align-items:center;
        gap:.4rem; border-top:1px solid #365065; padding-top:.55rem;
      }
      .fo-status { color:var(--fo-text); font-weight:650; font-size:.78rem; }
      .fo-status i {
        display:inline-block; width:.42rem; height:.42rem; margin:0 .4rem .04rem 0;
        background:var(--fo-cyan); border-radius:50%;
      }
      .fo-zone-card.pending .fo-status i { background:var(--fo-orange); }
      .fo-assignment { color:var(--fo-muted); font-size:.72rem; text-align:right; }
      .fo-team-list { display:grid; grid-template-columns:1fr; gap:.55rem; }
      .fo-team-card { display:flex; gap:.7rem; align-items:flex-start; }
      .fo-team-card.unavailable { background:#142332; border-style:dashed; }
      .fo-team-icon {
        position:relative; flex:0 0 1.6rem; height:1.6rem; margin-top:.05rem;
        border:1px solid #547168; border-radius:3px;
      }
      .fo-team-icon:before, .fo-team-icon:after {
        content:""; position:absolute; background:var(--fo-cyan);
      }
      .fo-team-icon:before { width:.68rem; height:2px; left:.4rem; top:.45rem; }
      .fo-team-icon:after { width:.42rem; height:2px; left:.4rem; top:.78rem; }
      .fo-team-card.unavailable .fo-team-icon { border-color:#58615e; }
      .fo-team-card.unavailable .fo-team-icon:before,
      .fo-team-card.unavailable .fo-team-icon:after { background:#8d9892; }
      .fo-team-main { min-width:0; flex:1; }
      .fo-status-pill {
        margin-left:auto; color:#a6c7b5; font:600 .66rem/1.3 "SFMono-Regular",Consolas,monospace;
        text-transform:none; letter-spacing:.045em;
      }
      .unavailable .fo-status-pill { color:#a0a9a4; }
      .fo-team-meta { display:flex; justify-content:space-between; gap:.5rem; flex-wrap:wrap; }
      .fo-team-meta span { color:var(--fo-muted); font-size:.8rem; }
      .fo-team-meta strong { color:var(--fo-text); }
      .fo-count-row { display:flex; gap:.45rem; margin:.7rem 0; }
      .fo-count-row div {
        display:flex; align-items:baseline; gap:.45rem; flex:1;
        background:#132332; border:1px solid #365065;
        border-radius:3px; padding:.45rem .55rem;
      }
      .fo-count-row strong { color:var(--fo-text); font-size:1.1rem; }
      .fo-count-row span { color:var(--fo-muted); font-size:.8rem; }
      .fo-decision-assignments { display:grid; gap:.7rem; }
      .fo-decision-assignments div { display:grid; gap:.25rem; }
      .fo-decision-assignments strong {
        color:#edf4f7; font:600 .78rem/1.4 "SFMono-Regular",Consolas,monospace;
      }
      .fo-cost-track {
        display:flex; width:100%; height:.4rem; overflow:hidden;
        background:#365065; margin-top:.95rem;
      }
      .fo-cost-track span:first-child { background:var(--fo-cyan); }
      .fo-cost-track span:last-child { background:var(--fo-orange); }
      .fo-cost-legend {
        display:flex; justify-content:space-between; flex-wrap:wrap;
        gap:.45rem; margin-top:.45rem;
      }
      .fo-cost-legend span {
        display:flex; align-items:center; gap:.35rem;
        color:var(--fo-muted); font-size:.69rem;
      }
      .fo-cost-legend b { color:#edf4f7; font-weight:650; }
      .fo-cost-key { width:.42rem; height:.42rem; display:inline-block; }
      .fo-cost-key.assignment { background:var(--fo-cyan); }
      .fo-cost-key.penalty { background:var(--fo-orange); }
      .fo-insight {
        background:#182f3c; border:1px solid var(--fo-border);
        border-left:3px solid var(--fo-cyan); border-radius:4px;
        padding:.9rem 1rem; color:#edf4f7; line-height:1.55; font-size:.95rem;
      }
      .fo-comparison-note {
        margin:-.5rem 0 1rem; padding-left:.2rem;
        color:var(--fo-muted); font-size:.78rem;
      }
      .fo-comparison-note strong {
        color:var(--fo-orange); font-family:"SFMono-Regular",Consolas,monospace;
        font-weight:650;
      }
      .fo-section-kicker { color:var(--fo-muted); font-size:.86rem; margin-top:-.6rem; }
      .st-key-objective_summary [data-testid="stMetric"] {
        border-left-color:var(--fo-cyan); background:#173a43;
      }
      .st-key-objective_summary [data-testid="stMetricValue"] {
        color:var(--fo-cyan); font-size:clamp(2.5rem, 5vw, 3.4rem); font-weight:700;
      }
      .st-key-simulate_e2 button {
        background:var(--fo-cyan); border-color:var(--fo-cyan); font-weight:650;
      }
      .st-key-simulate_e2 button p { color:#101b27; }

      h1, h2, h3 { text-wrap:balance; scroll-margin-top:4rem; }
      .fo-subtitle, .fo-insight, [data-testid="stCaptionContainer"] p { max-width:78ch; }
      .fo-id, [data-testid="stMetricValue"], .fo-count-row strong { font-variant-numeric:tabular-nums; }
      .st-key-decision_best { border-top:3px solid var(--fo-cyan); }
      .st-key-decision_quick { border-top:3px solid var(--fo-border); }
      .fo-section-heading { margin:.3rem 0 .7rem; }
      .fo-comparison-note { margin:1rem 0 0; font-size:.95rem; max-width:55ch; }
      button, summary, [role="combobox"] { touch-action:manipulation; }
      button:focus-visible, a:focus-visible, input:focus-visible,
      summary:focus-visible, [role="combobox"]:focus-visible {
        outline:3px solid var(--fo-orange); outline-offset:3px;
      }
      @media (prefers-reduced-motion: reduce) { html { scroll-behavior:auto; } }
      @media (max-width: 850px) {
        section.main .block-container, [data-testid="stMainBlockContainer"] { padding:2.5rem 1rem 2.2rem; }
        .fo-zone-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
      }
      @media (max-width: 560px) {
        .fo-hero { flex-direction:column; gap:.25rem; }
        .fo-synthetic { align-self:flex-start; }
        .fo-zone-grid, .fo-team-list { grid-template-columns:1fr; }
        .fo-count-row { flex-direction:column; }
        .fo-count-row div { justify-content:space-between; }
        .fo-section-heading h2 { font-size:1.3rem !important; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="fo-hero">
      <div>
        <h1 translate="no">FloodOps Lite</h1>
        <div class="fo-subtitle">Compare two ways to assign limited response teams.</div>
      </div>
      <div class="fo-synthetic">Educational simulation · Synthetic data</div>
    </div>
    """,
    unsafe_allow_html=True,
)

setup_panel, situation_panel = st.columns([1.2, 1])
with setup_panel:
    _section_heading("SETUP", "Configure a scenario")
    try:
        scenario = get_scenario()
        scenario_name = st.selectbox("Scenario preset", SCENARIOS, key="scenario_name")
        if st.session_state.get("loaded_scenario") != scenario_name:
            if scenario_name != "Default scenario":
                scenario = get_scenario(scenario_name)
            for team in scenario["teams"]:
                st.session_state[f"available_{team['id']}"] = team["available"]
            for zone in scenario["zones"]:
                st.session_state[f"priority_{zone['id']}"] = zone["priority"]
            st.session_state["loaded_scenario"] = scenario_name
        st.caption("Choosing a preset resets its controls. Manual changes apply immediately to this session.")
        with st.expander("Adjust team availability and zone priorities"):
            st.caption("Availability changes which teams can be assigned. Priority changes the pending-zone penalty.")
            st.markdown("**Response teams**")
            for column, team in zip(st.columns(len(scenario["teams"])), scenario["teams"]):
                team["available"] = column.checkbox(
                    f"{team['id']} — {team['name']}", key=f"available_{team['id']}",
                )
            st.markdown("**Zone priority**")
            st.caption("Low = 1 · Medium = 2 · High = 3. Pending penalty = 100 × priority.")
            for column, zone in zip(st.columns(len(scenario["zones"])), scenario["zones"]):
                zone["priority"] = column.selectbox(
                    f"{zone['id']} — {zone['name']}", [1, 2, 3], key=f"priority_{zone['id']}",
                    format_func=lambda value: f"{PRIORITY_LABELS[value]} ({value})",
                )
                zone["penalty"] = 100 * zone["priority"]
            st.caption("Both methods recalculate automatically after each change.")
        reference = greedy_assignment(scenario)
        optimized = optimal_assignment(scenario)
    except ValueError:
        st.error("Invalid scenario. Check priorities, availability and assignment costs.")
        st.stop()

with situation_panel:
    _section_heading("01", "The situation")
    zones_column, teams_column = st.columns(2)
    zones_column.metric("Zones needing attention", len(scenario["zones"]), border=True)
    teams_column.metric(
        "Response teams available", sum(t["available"] for t in scenario["teams"]), border=True
    )
    st.caption("One round: each team can serve at most one zone.")
    available_count = sum(team["available"] for team in scenario["teams"])
    if len(scenario["zones"]) > available_count:
        st.markdown(
            f'<div class="fo-gap-note">⚠ {len(scenario["zones"])} zones need attention, '
            f'but only {available_count} response teams are available. At least '
            f'{len(scenario["zones"]) - available_count} zone(s) must remain pending this round.</div>',
            unsafe_allow_html=True,
        )

st.divider()
_section_heading("03", "Compare the strategies")
st.caption("Synthetic objective only: assignment effort plus penalties for zones left pending. Lower is better.")
reference_cost = reference["total_cost"]
optimized_cost = optimized["total_cost"]
reduction = (reference_cost - optimized_cost) / reference_cost * 100 if reference_cost else None
absolute_difference = reference_cost - optimized_cost
reduction_label = f"{reduction:.2f}%" if reduction is not None else "N/A"
delta_label = (
    (
        f"Best allocation: {absolute_difference:g} synthetic units lower"
        if absolute_difference > 0
        else f"Quick decisions: {abs(absolute_difference):g} synthetic units lower"
    )
    if absolute_difference != 0
    else "No objective difference"
)
with st.container(key="objective_summary"):
    score, summary = st.columns([1, 2])
    score.metric("Model cost reduction", reduction_label)
    with summary:
        st.markdown(
            f'<div class="fo-comparison-note"><strong>{_safe(delta_label)}</strong> · '
            "not money or measured impact.</div>",
            unsafe_allow_html=True,
        )
left, right = st.columns(2)
with left:
    show_decision("Quick decisions", "Greedy reference · priority-first local choices", reference)
with right:
    show_decision("Best allocation", "Global optimization · considers the whole round", optimized)
from priority_indicator import show_unserved_priority

show_unserved_priority(scenario, reference, optimized)

if reference_cost == optimized_cost:
    st.info("Both strategies have the same total synthetic cost for this scenario.")
if reference_cost == 0:
    st.caption("Percentage reduction is undefined when the reference cost is zero.")

_section_heading("04", "Why does the allocation change?")
st.markdown(
    f'<div class="fo-insight" role="status" aria-live="polite" aria-atomic="true">{_safe(_primary_insight(scenario, reference, optimized))}</div>',
    unsafe_allow_html=True,
)


from scenario_lab import show_scenario_lab

show_scenario_lab(scenario)

st.divider()
_section_heading("05", "Assignment board")
method = st.radio(
    "View allocation",
    ["Greedy reference", "Optimized"],
    horizontal=True,
    format_func=lambda value: "Quick decisions" if value == "Greedy reference" else "Best allocation",
)
selected = reference if method == "Greedy reference" else optimized

st.caption(
    "A schematic assignment board, not a geographic map. Solid links show team-to-zone "
    "assignments, not roads or safe routes. No real locations are represented."
)
try:
    st.vega_lite_chart(assignment_chart(scenario, selected), width="stretch", theme=None)
except (ValueError, RuntimeError):
    st.warning("The illustrative view is unavailable. Use the tables in Technical details.")
st.markdown(
    '<div class="fo-section-kicker">Teams are on the left; zones are on the right. '
    'Unavailable teams and pending zones remain visible without relying on color alone.</div>',
    unsafe_allow_html=True,
)

with st.expander("Zone and team details"):
    zones_display, teams_display = st.columns([1.3, 1])
    with zones_display:
        st.markdown("**Flood-affected zones**")
        _show_zone_cards(scenario, selected)
    with teams_display:
        st.markdown("**Response teams**")
        _show_team_cards(scenario, selected)


with st.expander("Technical details"):
    st.subheader("Decision explanation")
    for line in explain_decisions(scenario, reference, optimized):
        st.markdown(f"- {_safe(line)}")
    st.subheader("Cost breakdown")
    st.caption("Assignment cost + pending penalty = total cost.")
    try:
        st.vega_lite_chart(cost_chart(reference, optimized), width="stretch", theme=None)
    except (ValueError, RuntimeError):
        st.caption("Cost chart unavailable. The metrics and comparison tables remain available.")
    left, right = st.columns(2)
    with left:
        show_tables("Greedy reference", reference, scenario)
    with right:
        show_tables("Optimized", optimized, scenario)
    st.caption(
        "Optimized minus reference, in synthetic units: "
        f"assignment cost {optimized['assignment_cost'] - reference['assignment_cost']:+g}; "
        f"pending penalties {optimized['pending_penalty'] - reference['pending_penalty']:+g}; "
        f"total {optimized_cost - reference_cost:+g}."
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
        "or measured impact. Different assignments may share the same optimal cost. "
        "All zones, teams and costs are synthetic and must not be used for emergency decisions."
    )
