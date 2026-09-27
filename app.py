from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from optimizer_logic import (
    OBJECTIVES,
    build_programme_interventions,
    horizon_days,
    optimize_programme,
    quick_impact,
    schedule_interventions,
    validate_config,
    volunteer_only_options,
)

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
LOGO_PATH = ROOT / "inamigos_logo.png"


def money(value: float) -> str:
    return f"₹{value:,.0f}"


def load_config(path: Path = CONFIG_PATH) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    validate_config(cfg)
    return cfg


def build_content(intervention: str, row: pd.Series, distribution_item: str) -> tuple[list[str], str, str]:
    units = int(row["units"])
    capacity = int(row["planned_beneficiaries"])
    budget = float(row["allocated_budget"])
    if intervention == "Education Cycle":
        hooks = [
            f"What can a planned {money(budget)} education programme make possible?",
            "One classroom. One structured programme. A measurable learning journey.",
            f"A focused education plan for {capacity} learner places.",
        ]
        body = (
            f"The current programme plan includes {units} complete Education Cycle unit(s), "
            f"covering {capacity:,} learner places with matching stationery support for the same cohort. "
            "The programme can be documented through attendance, learning assessments and activity records."
        )
        professional = (
            f"Education planning update: {units} complete cycle(s) are scheduled in the current scenario, "
            f"with an allocated budget of {money(budget)} and planned capacity of {capacity:,} learner places. "
            "Programme costs, permissions and final implementation details should be confirmed before execution."
        )
    elif intervention == "Distribution Event":
        hooks = [
            f"What can a planned {money(budget)} community distribution programme deliver?",
            f"A clear distribution plan can turn volunteer time into {capacity:,} item-level support opportunities.",
            f"{capacity:,} planned {distribution_item} units in the current scenario.",
        ]
        body = (
            f"The current programme plan includes {units} distribution event(s) for {distribution_item}, "
            f"with {capacity:,} planned item units. The schedule uses the available volunteer capacity and configured distribution rate."
        )
        professional = (
            f"Community distribution planning update: {units} event(s) are included in the scenario, "
            f"representing {capacity:,} planned {distribution_item} units and an allocated budget of {money(budget)}."
        )
    elif intervention == "School Cleaning Drive":
        hooks = [
            "One school. One team. One focused clean-up effort.",
            "A small operational intervention can create a visible community improvement.",
            "From volunteer hours to a completed community activity.",
        ]
        body = (
            f"The current programme plan includes {units} cleaning drive(s) with {money(budget)} allocated for materials. "
            "Volunteer effort is scheduled around available capacity and working hours."
        )
        professional = (
            f"Community activity planning update: {units} cleaning drive(s) are included with {money(budget)} allocated "
            "for the configured material requirement and volunteer time scheduled around available capacity."
        )
    else:
        hooks = [
            f"{units * 10:,} saplings. A planned environmental action built around volunteer capacity.",
            "Planting is only the beginning; a good plan also schedules the work and follow-up.",
            "Turning volunteer capacity into a structured plantation programme.",
        ]
        body = (
            f"The current plan includes {units} plantation activity unit(s), representing {capacity or units * 10:,} saplings "
            f"under the configured activity size, with {money(budget)} allocated for saplings."
        )
        professional = (
            f"Environment planning update: {units} plantation activity unit(s) are included in the current scenario, "
            f"with {money(budget)} allocated for saplings and volunteer work scheduled across the selected planning horizon."
        )
    return hooks, body, professional


st.set_page_config(
    page_title="InAmigos Resource Allocation Optimizer",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root { color-scheme: light !important; }
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMainBlockContainer"] {
        background: #f5f8f7 !important;
        color: #17212b !important;
    }
    [data-testid="stHeader"] { background: #ffffff !important; border-bottom: 1px solid #dbe5e1 !important; }
    [data-testid="stSidebar"] { background: #ffffff !important; }
    .block-container { max-width: 1400px; padding-top: 1.5rem; }
    .brand-card {
        background: #ffffff; border: 1px solid #d7e3df; border-radius: 12px;
        padding: 13px 16px; min-height: 54px;
    }
    .title { font-size: 2rem; font-weight: 760; line-height: 1.1; color: #17212b; }
    .subtitle { color: #667784; margin-top: 5px; }
    .section { font-size: 1.18rem; font-weight: 760; margin: 18px 0 9px; color: #17212b; }
    .pill {
        display: inline-block; padding: 7px 14px; border-radius: 999px;
        color: #008f6b !important; border: 1px solid #cce8df; background: #eaf7f2;
        font-size: .82rem; font-weight: 750;
    }
    .small { color: #667784; font-size: .82rem; }
    .stButton > button, .stFormSubmitButton > button,
    [data-testid="stDownloadButton"] > button {
        background: #00a878 !important; color: #ffffff !important;
        border: 1px solid #00a878 !important; border-radius: 9px !important;
        font-weight: 750 !important; min-height: 44px;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover,
    [data-testid="stDownloadButton"] > button:hover { background: #008f6b !important; border-color: #008f6b !important; }
    [data-testid="stNumberInput"] input, [data-testid="stTextInput"] input,
    [data-testid="stSelectbox"] > div, [data-testid="stTextArea"] textarea,
    [data-testid="stFileUploaderDropzone"] {
        background: #ffffff !important; color: #17212b !important; border-color: #d7e3df !important;
    }
    [data-testid="stMetric"] { background: #ffffff; border: 1px solid #d7e3df; border-radius: 12px; padding: 12px; }
    [data-testid="stDataFrame"] { background: #ffffff !important; border: 1px solid #d7e3df; border-radius: 10px; }
    .success-card { background:#eaf7f2; border:1px solid #cce8df; color:#007d5f; border-radius:12px; padding:14px 16px; }
    .calendar-row {
        background:#ffffff; border:1px solid #d7e3df; border-radius:10px;
        padding:11px 14px; margin:7px 0;
    }
    .calendar-week { font-weight:750; }
    @media (max-width: 800px) {
        .title { font-size: 1.45rem; } .subtitle { font-size: .88rem; } .section { font-size: 1.05rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "cfg" not in st.session_state:
    st.session_state.cfg = load_config()
if "plan" not in st.session_state:
    st.session_state.plan = None

cfg = st.session_state.cfg
rates = cfg["rates"]
ops = cfg["operations"]
distribution_items = cfg["distribution_items"]

header = st.columns([1, 7, 1])
with header[0]:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=78)
    else:
        st.markdown('<div class="pill">IAF</div>', unsafe_allow_html=True)
with header[1]:
    st.markdown('<div class="title">Resource Allocation Optimizer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Plan meaningful interventions using budget, volunteer capacity and operational rules.</div>',
        unsafe_allow_html=True,
    )
with header[2]:
    st.markdown('<div class="pill">InAmigos</div>', unsafe_allow_html=True)

planner_tab, quick_tab, settings_tab = st.tabs(["Programme Planning", "Quick Impact", "Settings"])

with planner_tab:
    st.markdown('<div class="section">Planning Inputs</div>', unsafe_allow_html=True)
    input_cols = st.columns(5)
    with input_cols[0]:
        budget = st.number_input("Available Budget (₹)", min_value=0.0, value=500000.0, step=5000.0, key="budget")
    with input_cols[1]:
        volunteers = st.number_input("Available Volunteers", min_value=0, value=10, step=1, key="volunteers")
    with input_cols[2]:
        hours_per_day = st.number_input("Working Hours / Day", min_value=0.5, value=float(ops["hours_per_working_day"]), step=0.5, key="hours_per_day")
    with input_cols[3]:
        horizon_label = st.selectbox("Planning Horizon", ["Auto", "1 Day", "1 Week", "1 Month", "3 Months"], key="horizon")
    with input_cols[4]:
        objective = st.selectbox("Planning Objective", OBJECTIVES, index=1, key="objective")

    input2 = st.columns([1, 3])
    with input2[0]:
        distribution_item = st.selectbox("Distribution Item", distribution_items, index=min(distribution_items.index("Stationery Kit"), len(distribution_items)-1), key="distribution_item")
    with input2[1]:
        st.markdown(
            f'<div class="brand-card"><b>Current delivery model</b><br><span class="small">Education: 30 children + matching stationery &nbsp;•&nbsp; Distribution: {ops["distribution_items_per_volunteer_per_hour"]:.0f} items / volunteer / hour &nbsp;•&nbsp; Working day: {hours_per_day:.1f} hours</span></div>',
            unsafe_allow_html=True,
        )

    horizon = horizon_days(horizon_label, ops, float(budget))
    interventions = build_programme_interventions(cfg, int(volunteers), distribution_item)
    st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
    if st.button("Run Allocation", type="primary", use_container_width=True):
        result = {"budget": float(budget), "volunteers": int(volunteers), "hours_per_day": float(hours_per_day), "horizon": horizon, "objective": objective, "distribution_item": distribution_item, "allocation": None, "schedule": pd.DataFrame(), "error": None}
        if budget == 0:
            result["schedule"] = volunteer_only_options(cfg, int(volunteers), float(hours_per_day))
        elif volunteers <= 0:
            result["error"] = "No volunteer capacity is available for programme delivery. Add volunteers to build a field programme."
        else:
            allocation, error = optimize_programme(interventions, float(budget), int(volunteers), float(hours_per_day), horizon.days, objective, ops)
            if allocation is not None and int(allocation["units"].sum()) == 0:
                allocation, error = None, "No complete intervention fits the current budget, volunteer capacity and planning horizon."
            result["allocation"], result["error"] = allocation, error
            if allocation is not None:
                active = allocation[allocation.units > 0].copy()
                result["schedule"] = schedule_interventions(active, int(volunteers), float(hours_per_day), horizon, ops)
        st.session_state.plan = result

    plan = st.session_state.plan
    if plan is None:
        st.markdown('<div class="brand-card">Set the planning inputs and run an allocation to build a practical programme and calendar.</div>', unsafe_allow_html=True)
    elif plan["allocation"] is None:
        if plan["budget"] == 0:
            st.markdown('<div class="section">Volunteer-Led Options</div>', unsafe_allow_html=True)
            if plan["schedule"].empty:
                st.info("Add at least one volunteer to explore no-budget opportunities.")
            else:
                st.dataframe(plan["schedule"], use_container_width=True, hide_index=True)
        else:
            st.error(plan["error"] or "No complete intervention fits the selected resources.")
            options = []
            for item in distribution_items:
                units, remaining = quick_impact(rates, item, plan["budget"])
                if units > 0:
                    options.append({"Item": item, "Complete Units": units, "Budget Used": plan["budget"] - remaining, "Remaining": remaining})
            if options:
                st.markdown('<div class="section">Direct-Support Alternatives</div>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(options).sort_values(["Remaining", "Complete Units"], ascending=[True, False]), use_container_width=True, hide_index=True, column_config={"Budget Used": st.column_config.NumberColumn(format="₹%,.0f"), "Remaining": st.column_config.NumberColumn(format="₹%,.0f")})
    else:
        active = plan["allocation"][plan["allocation"].units > 0].copy()
        used_budget = float(active.allocated_budget.sum())
        used_hours = float(active.volunteer_hours.sum())
        capacity = float(active.planned_beneficiaries.sum())
        schedule = plan["schedule"].copy()
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Budget Used", money(used_budget))
        k2.metric("Budget Remaining", money(max(0, plan["budget"] - used_budget)))
        k3.metric("Volunteer Hours", f"{used_hours:,.0f}")
        k4.metric("Planned Direct Capacity", f"{capacity:,.0f}")
        k5.metric("Active Interventions", f"{len(active)}")

        st.markdown('<div class="section">Recommended Programme</div>', unsafe_allow_html=True)
        schedule_by_name = {}
        if not schedule.empty:
            for name, g in schedule.groupby("Intervention"):
                starts = int(g["Units Started"].sum())
                schedule_by_name[name] = f"{starts} / week" if starts else "Scheduled"
        table = active[["intervention", "category", "units", "allocated_budget", "volunteer_hours", "planned_beneficiaries", "max_per_week"]].copy()
        table["schedule"] = table.apply(lambda r: schedule_by_name.get(r["intervention"], f"{int(r['max_per_week'])} / week"), axis=1)
        table = table[["intervention", "category", "units", "allocated_budget", "volunteer_hours", "planned_beneficiaries", "schedule"]]
        table.columns = ["Intervention", "Category", "Complete Units", "Budget", "Volunteer Hours", "Capacity", "Schedule"]
        st.dataframe(table, use_container_width=True, hide_index=True, column_config={"Budget": st.column_config.NumberColumn(format="₹%,.0f"), "Volunteer Hours": st.column_config.NumberColumn(format="%.0f"), "Capacity": st.column_config.NumberColumn(format="%.0f")})

        if plan["budget"] > used_budget + 0.01:
            st.markdown(f'<div class="success-card">{money(plan["budget"] - used_budget)} remains unallocated under the current programme cadence and delivery capacity. The system does not force partial or impractical activities.</div>', unsafe_allow_html=True)

        if not schedule.empty:
            # Always use numeric day/week ordering; never lexicographic ordering such as Week 11 before Week 2.
            schedule["_day_number"] = schedule["Day"].str.extract(r"(\d+)")[0].astype(int)
            schedule["_week_number"] = schedule["Week"].str.extract(r"(\d+)")[0].astype(int)
            schedule = schedule.sort_values(["_day_number", "_week_number", "Intervention"]).reset_index(drop=True)

            st.markdown(f'<div class="section">Programme Calendar — {plan["horizon"].days // int(ops["working_days_per_week"])} Weeks</div>', unsafe_allow_html=True)
            weeks = []
            for week_no, group in schedule.groupby("_week_number", sort=True):
                names = " • ".join(dict.fromkeys(group.sort_values("_day_number")["Intervention"].tolist()))
                focus = "Launch & field setup" if week_no == 1 else ("Progress & impact update" if week_no % 4 == 0 else "Field documentation")
                weeks.append({"Week": f"Week {week_no}", "Activities": names, "Focus": focus})
            for item in weeks:
                st.markdown(f'<div class="calendar-row"><span class="calendar-week">{item["Week"]}</span>&nbsp;&nbsp;&nbsp; {item["Activities"]}<span style="float:right;color:#667784">{item["Focus"]}</span></div>', unsafe_allow_html=True)

            with st.expander("View detailed schedule"):
                detail = schedule.drop(columns=["_day_number", "_week_number"])
                st.dataframe(detail, use_container_width=True, hide_index=True, column_config={"Allocated Budget": st.column_config.NumberColumn(format="₹%,.0f"), "Volunteer Hours": st.column_config.NumberColumn(format="%.0f"), "Elapsed Hours": st.column_config.NumberColumn(format="%.2f"), "Planned Capacity": st.column_config.NumberColumn(format="%.0f")})

        st.markdown('<div class="section">Programme Communication</div>', unsafe_allow_html=True)
        selected = st.selectbox("Select an intervention", active["intervention"].tolist(), key="content_intervention")
        row = active[active["intervention"] == selected].iloc[0]
        hooks, body, professional = build_content(selected, row, plan["distribution_item"])
        hook = st.selectbox("Hook", hooks, key="content_hook")
        c1, c2 = st.columns(2)
        with c1:
            st.text_area("Social Caption", f"{hook}\n\n{body}\n\nCTA: Follow the programme, volunteer or support the approved intervention.", height=220)
        with c2:
            st.text_area("Professional / CSR Update", professional, height=220)

        st.download_button("Download Allocation CSV", table.to_csv(index=False).encode("utf-8"), "inamigos_resource_allocation.csv", "text/csv", use_container_width=True)

with quick_tab:
    st.markdown('<div class="section">Quick Impact</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        quick_budget = st.number_input("Budget to Evaluate (₹)", min_value=0.0, value=500.0, step=50.0, key="quick_budget")
    with c2:
        quick_item = st.selectbox("Item", distribution_items, index=min(distribution_items.index("Meal for 1 person"), len(distribution_items)-1), key="quick_item")
    units, remaining = quick_impact(rates, quick_item, quick_budget)
    a, b = st.columns(2)
    a.metric("Complete Units", f"{units:,}")
    b.metric("Remaining Budget", money(remaining))
    st.info(f"{money(quick_budget)} can provide {units:,} complete {quick_item} unit(s) at the current configured rate.")
    comparison = []
    for item in distribution_items:
        u, r = quick_impact(rates, item, quick_budget)
        comparison.append({"Item": item, "Complete Units": u, "Budget Used": quick_budget - r, "Remaining": r})
    st.dataframe(pd.DataFrame(comparison), use_container_width=True, hide_index=True, column_config={"Budget Used": st.column_config.NumberColumn(format="₹%,.0f"), "Remaining": st.column_config.NumberColumn(format="₹%,.0f")})
    if quick_budget == 0:
        st.markdown('<div class="section">No-Budget Volunteer Options</div>', unsafe_allow_html=True)
        st.dataframe(volunteer_only_options(cfg, int(volunteers), float(hours_per_day)), use_container_width=True, hide_index=True)

with settings_tab:
    st.markdown('<div class="section">Settings</div>', unsafe_allow_html=True)
    with st.form("settings_form"):
        st.markdown("#### Direct-Support Rates")
        rate_cols = st.columns(3)
        edited_rates = {}
        for idx, item in enumerate(rates):
            with rate_cols[idx % 3]:
                edited_rates[item] = st.number_input(item, min_value=0.01, value=float(rates[item]), step=1.0, key=f"rate_{item}")

        st.markdown("#### Operating Rules")
        op_cols = st.columns(3)
        editable_ops = [
            ("cleaning_volunteer_hours", "Cleaning volunteer-hours", 1.0),
            ("plantation_volunteer_hours", "Plantation volunteer-hours", 1.0),
            ("plantation_saplings_per_activity", "Saplings per plantation activity", 1.0),
            ("distribution_duration_hours", "Distribution duration (hours)", 0.5),
            ("distribution_items_per_volunteer_per_hour", "Distribution items / volunteer / hour", 1.0),
            ("learning_session_hours", "Learning session duration (hours)", 0.5),
            ("learning_volunteers_per_team", "Volunteers per learning team", 1.0),
            ("learning_teams_per_session", "Learning teams per session", 1.0),
            ("learning_children_per_session", "Children per learning cycle", 1.0),
            ("stationery_recipients_per_education_cycle", "Stationery recipients per education cycle", 1.0),
            ("hours_per_working_day", "Working hours per day", 0.5),
            ("education_max_per_week", "Education cycles / week", 1.0),
            ("cleaning_max_per_week", "Cleaning drives / week", 1.0),
            ("plantation_max_per_week", "Plantation activities / week", 1.0),
            ("distribution_max_per_week", "Distribution events / week", 1.0),
            ("education_min_gap_days", "Education minimum gap (days)", 1.0),
            ("cleaning_min_gap_days", "Cleaning minimum gap (days)", 1.0),
            ("plantation_min_gap_days", "Plantation minimum gap (days)", 1.0),
            ("distribution_min_gap_days", "Distribution minimum gap (days)", 1.0),
        ]
        edited_ops = dict(ops)
        for idx, (key, label, step) in enumerate(editable_ops):
            with op_cols[idx % 3]:
                edited_ops[key] = st.number_input(label, min_value=0.01, value=float(ops[key]), step=float(step), key=f"op_{key}")

        submitted = st.form_submit_button("Apply Settings", use_container_width=True)
        if submitted:
            new_cfg = {**cfg, "rates": edited_rates, "operations": edited_ops}
            try:
                validate_config(new_cfg)
                st.session_state.cfg = new_cfg
                st.session_state.plan = None
                st.success("Settings applied for the current session.")
            except ValueError as exc:
                st.error(str(exc))

    st.download_button("Download Settings", json.dumps(cfg, indent=2).encode("utf-8"), "inamigos_optimizer_settings.json", "application/json", use_container_width=True)
    incoming = st.file_uploader("Load Settings", type=["json"])
    if incoming is not None:
        try:
            incoming_cfg = json.loads(incoming.read().decode("utf-8"))
            validate_config(incoming_cfg)
            st.session_state.cfg = incoming_cfg
            st.session_state.plan = None
            st.success("Settings loaded successfully for the current session.")
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            st.error(f"Settings could not be loaded: {exc}")

st.markdown('<div class="small" style="text-align:center;margin-top:24px;">InAmigos Foundation • Resource Allocation Optimizer</div>', unsafe_allow_html=True)