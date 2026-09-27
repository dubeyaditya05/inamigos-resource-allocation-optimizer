from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from optimizer_logic import (
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


def load_config() -> dict:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    validate_config(cfg)
    return cfg


st.set_page_config(
    page_title="InAmigos Resource Allocation Optimizer",
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] { background:#f7f8fa; }
    [data-testid="stSidebar"] { background:#ffffff; border-right:1px solid #e4e7eb; }
    .main-title { font-size:2.05rem; font-weight:760; letter-spacing:-0.02em; }
    .subtitle { color:#626770; font-size:.97rem; margin-bottom:1rem; }
    .section-title { font-size:1.27rem; font-weight:720; margin:.9rem 0 .65rem; }
    .card { background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:16px 18px; }
    .brand-pill { display:inline-block; padding:5px 10px; border-radius:999px; background:#e8f8f1; color:#087443; border:1px solid #c8ebd9; font-weight:650; font-size:.78rem; }
    .footer { margin-top:2rem; text-align:center; color:#7a7f87; font-size:.78rem; }
    @media (max-width: 800px) {
      .main-title { font-size:1.55rem; }
      .subtitle { font-size:.9rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "cfg" not in st.session_state:
    st.session_state.cfg = load_config()

cfg = st.session_state.cfg
rates = cfg["rates"]
ops = cfg["operations"]
distribution_items = [item for item in cfg.get("distribution_items", []) if item in rates]
distribution_items = cfg.get("distribution_items", list(rates.keys()))

labels = {
    "English": {
        "title": "Resource Allocation Optimizer",
        "subtitle": "Plan meaningful interventions using budget, volunteer capacity and operational rules.",
        "language": "Language",
        "planning": "Planning",
        "budget": "Available Budget (₹)",
        "volunteers": "Available Volunteers",
        "hours": "Working Hours per Day",
        "horizon": "Planning Horizon",
        "objective": "Planning Objective",
        "distribution_item": "Distribution Item",
        "run": "Run Allocation",
        "quick": "Quick Impact",
        "settings": "Settings",
        "schedule": "Programme Schedule",
        "communication": "Programme Communication",
        "export": "Export",
        "portfolio": "Intervention Portfolio",
        "budget_used": "Budget Used",
        "budget_remaining": "Budget Remaining",
        "hours_used": "Volunteer Hours Used",
        "capacity": "Planned Beneficiary Capacity",
        "interventions": "Active Interventions",
    },
    "Hindi": {
        "title": "संसाधन आवंटन ऑप्टिमाइज़र",
        "subtitle": "बजट, स्वयंसेवक क्षमता और संचालन नियमों के आधार पर सार्थक हस्तक्षेपों की योजना बनाएं।",
        "language": "भाषा",
        "planning": "योजना",
        "budget": "उपलब्ध बजट (₹)",
        "volunteers": "उपलब्ध स्वयंसेवक",
        "hours": "प्रति दिन कार्य घंटे",
        "horizon": "योजना अवधि",
        "objective": "योजना उद्देश्य",
        "distribution_item": "वितरण सामग्री",
        "run": "आवंटन चलाएं",
        "quick": "त्वरित प्रभाव",
        "settings": "सेटिंग्स",
        "schedule": "कार्यक्रम समय-सारणी",
        "communication": "कार्यक्रम संचार",
        "export": "निर्यात",
        "portfolio": "हस्तक्षेप पोर्टफोलियो",
        "budget_used": "उपयोग किया गया बजट",
        "budget_remaining": "शेष बजट",
        "hours_used": "उपयोग किए गए स्वयंसेवक घंटे",
        "capacity": "लाभार्थी क्षमता",
        "interventions": "सक्रिय हस्तक्षेप",
    },
    "Hinglish": {
        "title": "Resource Allocation Optimizer",
        "subtitle": "Budget, volunteer capacity aur operational rules ke basis par meaningful interventions plan karein.",
        "language": "Language",
        "planning": "Planning",
        "budget": "Available Budget (₹)",
        "volunteers": "Available Volunteers",
        "hours": "Working Hours per Day",
        "horizon": "Planning Horizon",
        "objective": "Planning Objective",
        "distribution_item": "Distribution Item",
        "run": "Run Allocation",
        "quick": "Quick Impact",
        "settings": "Settings",
        "schedule": "Programme Schedule",
        "communication": "Programme Communication",
        "export": "Export",
        "portfolio": "Intervention Portfolio",
        "budget_used": "Budget Used",
        "budget_remaining": "Budget Remaining",
        "hours_used": "Volunteer Hours Used",
        "capacity": "Planned Beneficiary Capacity",
        "interventions": "Active Interventions",
    },
}

lang = st.sidebar.selectbox(labels["English"]["language"], list(labels.keys()), index=list(labels.keys()).index(st.session_state.get("lang", "English")))
st.session_state.lang = lang
T = labels[lang]

st.sidebar.image(str(LOGO_PATH), width=135)
st.sidebar.markdown(f"### {T['planning']}")
budget = st.sidebar.number_input(T["budget"], min_value=0.0, value=500000.0, step=5000.0)
volunteers = st.sidebar.number_input(T["volunteers"], min_value=0, value=10, step=1)
hours_per_day = st.sidebar.number_input(T["hours"], min_value=0.0, value=float(ops["hours_per_working_day"]), step=0.5)
horizon_label = st.sidebar.selectbox(T["horizon"], ["Auto", "1 Day", "1 Week", "1 Month", "3 Months"], index=0)
objective = st.sidebar.selectbox(
    T["objective"],
    ["Maximum reach", "Balanced programme", "Maximum programme priority", "Education focus", "Community support focus", "Environment focus"],
)
distribution_index = distribution_items.index("Stationery Kit") if "Stationery Kit" in distribution_items else 0
distribution_item = st.sidebar.selectbox(T["distribution_item"], distribution_items, index=distribution_index)

# Header
h1, h2, h3 = st.columns([0.75, 5.6, 1.1])
with h1:
    st.image(str(LOGO_PATH), width=78)
with h2:
    st.markdown(f'<div class="main-title">{T["title"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">{T["subtitle"]}</div>', unsafe_allow_html=True)
with h3:
    st.markdown('<div class="brand-pill">InAmigos</div>', unsafe_allow_html=True)

plan_tab, quick_tab, settings_tab = st.tabs([T["planning"], T["quick"], T["settings"]])

with settings_tab:
    st.markdown(f'<div class="section-title">{T["settings"]}</div>', unsafe_allow_html=True)
    st.caption("Update the planning rates, operating rules and programme assumptions used by the calculator.")
    st.markdown("#### Cost Rates")
    rate_cols = st.columns(2)
    for i, key in enumerate(list(rates.keys())):
        with rate_cols[i % 2]:
            rates[key] = st.number_input(key, min_value=0.0, value=float(rates[key]), step=1.0, key=f"rate_{key}")
    st.markdown("#### Operating Rules")
    op_cols = st.columns(2)
    integer_ops = {
        "working_days_per_week", "weeks_per_month", "learning_volunteers_per_team",
        "learning_teams_per_session", "learning_children_per_session",
        "stationery_recipients_per_education_cycle", "max_education_cycles_per_day",
        "max_cleaning_drives_per_day", "max_plantation_activities_per_day",
        "max_distribution_events_per_day", "balanced_min_categories_for_long_horizon",
        "plantation_saplings_per_activity",
    }
    for i, key in enumerate(list(ops.keys())):
        with op_cols[i % 2]:
            if key in integer_ops:
                current = int(ops[key])
                ops[key] = st.number_input(key, min_value=0, value=current, step=1, key=f"op_{key}")
            else:
                current = float(ops[key])
                ops[key] = st.number_input(key, min_value=0.0, value=current, step=0.5 if "hours" in key.lower() else 1.0, key=f"op_{key}")
    st.download_button(
        "Download settings",
        json.dumps(cfg, indent=2).encode("utf-8"),
        file_name="inamigos_optimizer_settings.json",
        mime="application/json",
        use_container_width=True,
    )
    uploaded = st.file_uploader("Load settings", type=["json"])
    if uploaded:
        try:
            new_cfg = json.loads(uploaded.read().decode("utf-8"))
            validate_config(new_cfg)
            st.session_state.cfg = new_cfg
            st.rerun()
        except Exception as exc:
            st.error(f"Settings could not be loaded: {exc}")

with quick_tab:
    st.markdown(f'<div class="section-title">{T["quick"]}</div>', unsafe_allow_html=True)
    quick_budget = st.number_input("Budget to evaluate (₹)", min_value=0.0, value=500.0, step=50.0, key="quick_budget")
    quick_item = st.selectbox("Item", distribution_items, index=distribution_items.index("Meal for 1 person"), key="quick_item")
    q_units, q_remaining = quick_impact(rates, quick_item, quick_budget)
    st.metric("Complete units possible", f"{q_units:,}")
    st.metric("Remaining budget", f"₹{q_remaining:,.0f}")
    st.markdown(
        f'<div class="card">₹{quick_budget:,.0f} at the current <b>{quick_item}</b> rate can provide <b>{q_units:,}</b> complete units, with <b>₹{q_remaining:,.0f}</b> remaining.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("#### Volunteer-led options when cash budget is zero")
    if quick_budget == 0:
        z = volunteer_only_options(cfg, int(volunteers), float(hours_per_day))
        if z.empty:
            st.info("Enter at least one available volunteer and working hours to explore volunteer-led options.")
        else:
            st.dataframe(z, use_container_width=True, hide_index=True)
    else:
        st.caption("Quick Impact is intended for small, direct-support calculations. Larger budgets are handled through the programme planner.")

with plan_tab:
    horizon = horizon_days(horizon_label, ops, budget)
    st.markdown(f'<div class="section-title">{T["portfolio"]}</div>', unsafe_allow_html=True)
    interventions = build_programme_interventions(cfg, int(volunteers), distribution_item)
    view = interventions[["intervention", "category", "unit_description", "cost_per_unit", "volunteer_hours_per_unit", "beneficiaries_per_unit"]].copy()
    view.columns = ["Intervention", "Category", "Unit", "Cost / Unit", "Volunteer Hours / Unit", "Capacity / Unit"]
    st.dataframe(
        view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Cost / Unit": st.column_config.NumberColumn(format="₹%,.0f"),
            "Volunteer Hours / Unit": st.column_config.NumberColumn(format="%.2f"),
            "Capacity / Unit": st.column_config.NumberColumn(format="%.0f"),
        },
    )
    st.caption(f"Planning horizon: {horizon.label} • {horizon.days} working day(s) • Distribution item: {distribution_item}")

    run = st.button(T["run"], type="primary", use_container_width=True)
    if run:
        if budget == 0:
            st.markdown("### Volunteer-led planning")
            z = volunteer_only_options(cfg, int(volunteers), float(hours_per_day))
            if z.empty:
                st.warning("No volunteer capacity is available for the selected settings.")
            else:
                st.dataframe(z, use_container_width=True, hide_index=True)
                st.info("Cash-funded programme units are not selected at ₹0. The options above are activities that can be explored when existing resources, permissions and materials are available.")
        elif volunteers == 0 or hours_per_day == 0:
            st.warning("No working capacity is available. Add volunteers and working hours to build a programme plan.")
        else:
            alloc, error = optimize_programme(interventions, float(budget), int(volunteers), float(hours_per_day), horizon.days, objective)
            if alloc is None:
                st.error(f"No feasible programme plan was found. {error}")
            else:
                active = alloc[alloc["units"] > 0].copy()
                if active.empty:
                    st.info("No complete paid intervention fits the selected budget and resource constraints.")
                    if budget > 0:
                        quick_rows = []
                        for item_name in distribution_items:
                            q_u, q_r = quick_impact(rates, item_name, float(budget))
                            if q_u > 0:
                                quick_rows.append({"Option": item_name, "Complete Units": q_u, "Budget Used": q_u * float(rates[item_name]), "Remaining": q_r})
                        if quick_rows:
                            st.markdown("#### Available Direct-Support Options")
                            st.dataframe(pd.DataFrame(quick_rows).sort_values("Remaining").head(8), use_container_width=True, hide_index=True)
                    st.stop()
                used_budget = float(active["allocated_budget"].sum())
                used_hours = float(active["volunteer_hours"].sum())
                cap = float(active["planned_beneficiaries"].sum())
                k1,k2,k3,k4 = st.columns(4)
                k1.metric(T["budget_used"], f"₹{used_budget:,.0f}")
                k2.metric(T["budget_remaining"], f"₹{max(0,budget-used_budget):,.0f}")
                k3.metric(T["hours_used"], f"{used_hours:,.2f}")
                k4.metric(T["capacity"], f"{cap:,.0f}")

                display = active[["intervention","category","unit_description","units","allocated_budget","volunteer_hours","planned_beneficiaries"]].copy()
                display.columns = ["Intervention","Category","Unit","Complete Units","Allocated Budget","Volunteer Hours","Planned Capacity"]
                st.dataframe(display, use_container_width=True, hide_index=True, column_config={"Allocated Budget": st.column_config.NumberColumn(format="₹%,.0f"), "Volunteer Hours": st.column_config.NumberColumn(format="%.2f"), "Planned Capacity": st.column_config.NumberColumn(format="%.0f")})

                remaining_for_topup = max(0.0, float(budget - used_budget))
                if remaining_for_topup > 0:
                    st.markdown("#### Remaining Budget Options")
                    quick_rows = []
                    for item_name in ["Meal for 1 person", "Pencil", "Notebook", "Stationery Kit", "Book", "Water Bottle", "Hygiene Kit", "School Bag"]:
                        q_u, q_r = quick_impact(rates, item_name, remaining_for_topup)
                        if q_u > 0:
                            quick_rows.append({
                                "Option": item_name,
                                "Complete Units": q_u,
                                "Budget Used": q_u * float(rates[item_name]),
                                "Remaining": q_r,
                            })
                    if quick_rows:
                        topup = pd.DataFrame(quick_rows).sort_values("Remaining").head(5)
                        st.dataframe(topup, use_container_width=True, hide_index=True, column_config={"Budget Used": st.column_config.NumberColumn(format="₹%,.0f"), "Remaining": st.column_config.NumberColumn(format="₹%,.0f")})

                st.markdown(f'<div class="section-title">{T["schedule"]}</div>', unsafe_allow_html=True)
                schedule = schedule_interventions(active, int(volunteers), float(hours_per_day), horizon)
                if schedule.empty:
                    st.warning("The allocation could not be placed into the selected working-day schedule.")
                else:
                    st.dataframe(schedule, use_container_width=True, hide_index=True, column_config={"Allocated Budget": st.column_config.NumberColumn(format="₹%,.0f"), "Volunteer Hours": st.column_config.NumberColumn(format="%.2f"), "Planned Capacity": st.column_config.NumberColumn(format="%.0f")})

                    # Weekly / monthly summary for longer horizons
                    if horizon.days > 5:
                        s = schedule.copy()
                        s["day_number"] = s["Day"].str.extract(r"(\d+)").astype(int)
                        s["Week"] = ((s["day_number"] - 1) // int(ops["working_days_per_week"]) + 1).astype(int)
                        weekly = s.groupby("Week").agg(
                            Activities=("Intervention", "count"),
                            UnitsStarted=("Units Started", "sum"),
                            Budget=("Allocated Budget", "sum"),
                            VolunteerHours=("Volunteer Hours", "sum"),
                            PlannedCapacity=("Planned Capacity", "sum"),
                        ).reset_index()
                        st.markdown("#### Period Summary")
                        st.dataframe(weekly, use_container_width=True, hide_index=True, column_config={"Budget": st.column_config.NumberColumn(format="₹%,.0f"), "VolunteerHours": st.column_config.NumberColumn(format="%.2f"), "PlannedCapacity": st.column_config.NumberColumn(format="%.0f")})

                st.markdown("#### Communication Timeline")
                if horizon.days == 1:
                    content_timeline = pd.DataFrame([
                        {"Period": "Day 1", "Content focus": "Activity launch / field documentation", "Suggested output": "1 short video or photo update + clear CTA"},
                        {"Period": "After activity", "Content focus": "Result / evidence", "Suggested output": "Impact update with verified activity figures"},
                    ])
                elif horizon.days == int(ops["working_days_per_week"]):
                    content_timeline = pd.DataFrame([
                        {"Period": "Week 1", "Content focus": "Programme launch", "Suggested output": "Why the activity matters + what the plan will deliver"},
                        {"Period": "During week", "Content focus": "Field update", "Suggested output": "Real activity footage + volunteer/beneficiary context"},
                        {"Period": "End of week", "Content focus": "Weekly result", "Suggested output": "Verified outputs + next-step CTA"},
                    ])
                else:
                    total_weeks = max(1, horizon.days // int(ops["working_days_per_week"]))
                    rows = [{"Period": "Week 1", "Content focus": "Programme launch", "Suggested output": "Programme objective + planned activities + participation CTA"}]
                    for w in range(2, total_weeks + 1):
                        if w % 4 == 0:
                            focus = "Monthly progress / evidence"
                            output = "Monthly impact summary with verified outputs and field evidence"
                        else:
                            focus = "Field activity update"
                            output = "Short field story showing the activity, people involved and next step"
                        rows.append({"Period": f"Week {w}", "Content focus": focus, "Suggested output": output})
                    content_timeline = pd.DataFrame(rows)
                st.dataframe(content_timeline, use_container_width=True, hide_index=True)

                st.markdown(f'<div class="section-title">{T["communication"]}</div>', unsafe_allow_html=True)
                chosen = st.selectbox("Select an intervention", active["intervention"].tolist())
                rr = active[active["intervention"] == chosen].iloc[0]
                amount = float(rr["allocated_budget"])
                units = int(rr["units"])
                capacity = int(rr["planned_beneficiaries"])
                if chosen == "Education Cycle":
                    hook_options = [
                        f"What can a planned ₹{amount:,.0f} education programme support?",
                        f"{capacity} learners. Structured sessions. One measurable programme plan.",
                        "From learning sessions to learning outcomes: start with a clear plan.",
                    ]
                    caption = f"{hook_options[0]}\n\nThe current programme plan includes {units} complete Education Cycle unit(s), covering approximately {capacity} learner places and matching stationery support to the same learner cohort.\n\nThe programme can be documented through attendance, activity records and learning assessments.\n\nCTA: Support the approved programme, volunteer or follow the impact updates."
                elif chosen == "Distribution Event":
                    hook_options = [
                        f"What can one planned distribution day accomplish?",
                        "From preparation to distribution: every item has a purpose.",
                        "A small distribution window can turn organised resources into direct support.",
                    ]
                    caption = f"{hook_options[0]}\n\nThe current plan schedules {units} distribution event(s) for {distribution_item}, with a combined planned capacity of {capacity:,} items/people.\n\nEach event is planned around volunteer capacity, working time and the current item rate.\n\nCTA: Volunteer, support the approved programme or follow the next field update."
                elif chosen == "School Cleaning Drive":
                    hook_options = [
                        "A cleaner learning environment starts with organised action.",
                        "One school. One team. One focused cleanup drive.",
                        "Small operational work can support a better learning environment.",
                    ]
                    caption = f"{hook_options[0]}\n\nThe programme plan includes {units} school cleaning drive(s), using the configured material requirement and volunteer capacity.\n\nThe activity should be documented with permission, volunteer records and before/after evidence where appropriate.\n\nCTA: Join the volunteer team or support the approved activity."
                else:
                    hook_options = [
                        "A greener community begins with planned local action.",
                        f"{int(ops['plantation_saplings_per_activity'])} saplings per activity. A clear plan for every session.",
                        "From saplings to stewardship: plan the activity, document the work, measure survival.",
                    ]
                    caption = f"{hook_options[0]}\n\nThe current programme plan includes {units} plantation activity unit(s), representing {capacity:,} saplings under the configured activity size.\n\nFollow-up should include planting records and, where possible, later survival checks.\n\nCTA: Volunteer, support the approved programme or follow the field updates."
                selected_hook = st.selectbox("Hook", hook_options)
                c1,c2=st.columns(2)
                with c1:
                    st.text_area("Social caption", caption.replace(hook_options[0], selected_hook), height=300)
                with c2:
                    professional = f"{chosen} | Programme Update\n\nCurrent planning scenario: ₹{amount:,.0f} allocated across {units} complete unit(s), using approximately {float(rr['volunteer_hours']):,.2f} volunteer hours.\n\nPlanned capacity: {capacity:,}.\n\nThe final implementation should use approved costs, permissions, safeguarding controls and reporting indicators."
                    st.text_area("Professional / CSR update", professional, height=300)

                st.markdown(f'<div class="section-title">{T["export"]}</div>', unsafe_allow_html=True)
                csv = display.to_csv(index=False).encode("utf-8")
                st.download_button("Download allocation CSV", csv, file_name="inamigos_resource_allocation.csv", mime="text/csv", use_container_width=True)

st.markdown('<div class="footer">InAmigos Foundation • Resource Allocation Optimizer</div>', unsafe_allow_html=True)
