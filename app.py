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
    project_catalog,
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


def load_config() -> dict:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    validate_config(cfg)
    return cfg


def communication_copy(intervention: str, row: pd.Series, distribution_item: str) -> tuple[list[str], str, str]:
    units = int(row["units"])
    budget = float(row["allocated_budget"])
    capacity = int(row["planned_beneficiaries"])
    hooks = {
        "Seva Meal Distribution": ["A planned meal distribution can turn a defined budget into direct community support.", "Food support works best when delivery is planned around real field capacity."],
        "Bachpanshala Learning Cycle": ["30 children. One structured learning cycle. A clear plan for delivery.", "Education support becomes stronger when learning and essential study material move together."],
        "Prakriti Plantation Activity": ["A planned plantation activity turns volunteer capacity into a measurable environmental action.", "Planting is only the first step; planning the activity makes the work deliverable."],
        "Prakriti School/Community Clean-up": ["A focused clean-up can turn volunteer hours into a visible community improvement.", "Small, scheduled field actions can create practical local impact."],
    }
    hook_list = hooks.get(intervention, [f"A structured {intervention.lower()} plan built around available resources."])
    body = (
        f"The current scenario includes {units} complete {intervention} unit(s), "
        f"with {money(budget)} allocated."
    )
    if capacity:
        body += f" Planned direct capacity is {capacity:,} {distribution_item.lower() if intervention == 'Seva Meal Distribution' else 'learner places'}."
    professional = f"Programme planning update: {units} complete unit(s) of {intervention} are included, with {money(budget)} allocated under the current resource scenario."
    return hook_list, body, professional


st.set_page_config(
    page_title="InAmigos Resource Allocation Optimizer",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "I",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root { --iaf-green:#00A878; --iaf-dark:#17332B; --iaf-muted:#667085; --iaf-border:#DCE6E2; }
    [data-testid="stToolbar"] { display:none !important; }
    [data-testid="stHeader"] { background:#FFFFFF !important; }
    .stApp { background:#FFFFFF !important; }
    [data-testid="stMainBlockContainer"] { max-width:1180px; padding-top:1.2rem; }
    .hero { border:1px solid var(--iaf-border); border-radius:18px; padding:20px 22px; background:#F7FAF9; }
    .hero-title { color:var(--iaf-dark); font-size:2rem; font-weight:800; line-height:1.1; }
    .hero-sub { color:var(--iaf-muted); margin-top:6px; }
    .section { color:var(--iaf-dark); font-size:1.18rem; font-weight:800; margin:24px 0 10px; }
    .info-card { border:1px solid var(--iaf-border); border-radius:14px; padding:15px 17px; background:#FFFFFF; height:100%; }
    .project-card { border:1px solid var(--iaf-border); border-radius:14px; padding:13px 15px; background:#FFFFFF; min-height:120px; }
    .project-name { color:var(--iaf-dark); font-weight:800; }
    .muted { color:var(--iaf-muted); font-size:.86rem; }
    .badge { display:inline-block; padding:4px 9px; border-radius:999px; background:#E7F7F1; color:#087653; font-size:.74rem; font-weight:700; }
    .stButton > button[kind="primary"], .stFormSubmitButton > button { background:#00A878 !important; color:white !important; border:1px solid #00A878 !important; font-weight:750 !important; border-radius:9px !important; min-height:44px; }
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover { background:#008F68 !important; border-color:#008F68 !important; }
    div[data-baseweb="tab-list"] button[aria-selected="true"] { color:#00A878 !important; }
    div[data-baseweb="tab-highlight"] { background:#00A878 !important; }
    @media(max-width:800px){ .hero-title{font-size:1.45rem;} [data-testid="stMainBlockContainer"]{padding-left:.7rem;padding-right:.7rem;} }
    </style>
    """,
    unsafe_allow_html=True,
)

if "cfg" not in st.session_state:
    st.session_state.cfg = load_config()
if "plan" not in st.session_state:
    st.session_state.plan = None

cfg = st.session_state.cfg
rates, ops = cfg["rates"], cfg["operations"]
distribution_items = cfg["distribution_items"]

hero = st.columns([1, 8])
with hero[0]:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=82)
with hero[1]:
    st.markdown('<div class="hero"><div class="hero-title">Resource Allocation Optimizer</div><div class="hero-sub">Plan practical NGO programmes using budget, volunteer capacity, working hours and delivery rules.</div></div>', unsafe_allow_html=True)

planner_tab, quick_tab, coverage_tab, settings_tab = st.tabs(["Programme Planning", "Quick Impact", "Project Coverage", "Settings"])

with planner_tab:
    st.markdown('<div class="section">Planning Inputs</div>', unsafe_allow_html=True)
    c = st.columns(5)
    with c[0]: budget = st.number_input("Available Budget (₹)", min_value=0.0, value=500000.0, step=5000.0, key="budget")
    with c[1]: volunteers = st.number_input("Available Volunteers", min_value=0, value=10, step=1, key="volunteers")
    with c[2]: hours = st.number_input("Working Hours / Day", min_value=0.5, value=float(ops["hours_per_working_day"]), step=0.5, key="hours")
    with c[3]: horizon_label = st.selectbox("Planning Horizon", ["Auto", "1 Day", "1 Week", "1 Month", "3 Months"], key="horizon")
    with c[4]: objective = st.selectbox("Planning Objective", OBJECTIVES, index=0, key="objective")

    c2 = st.columns([1, 1, 2])
    with c2[0]: distribution_item = st.selectbox("Seva Distribution Item", distribution_items, index=0, key="distribution_item")
    with c2[1]:
        st.markdown(f'<div class="info-card"><b>Delivery model</b><br><span class="muted">Education: {ops["learning_children_per_session"]} children • {ops["learning_volunteers_per_team"]} volunteers • {ops["learning_session_hours"]:.0f} hours<br>Distribution: {ops["distribution_items_per_volunteer_per_hour"]:.0f} items / volunteer / hour</span></div>', unsafe_allow_html=True)
    with c2[2]:
        st.markdown('<div class="info-card"><b>Planning scope</b><br><span class="muted">Budgeted routes cover Seva, Bachpanshala and Prakriti. Jeev, Udaan and Vikas remain visible as field-configured / volunteer-led programmes rather than being assigned invented costs.</span></div>', unsafe_allow_html=True)

    horizon = horizon_days(horizon_label, ops, float(budget))
    st.caption(f"Selected horizon: {horizon.label} • {horizon.days} planning days")

    st.markdown('<div class="section">Budgeted Intervention Portfolio</div>', unsafe_allow_html=True)
    interventions = build_programme_interventions(cfg, int(volunteers), distribution_item)
    portfolio = interventions[["project", "intervention", "category", "cost_per_unit", "volunteer_hours_per_unit", "beneficiaries_per_unit", "max_per_week", "min_gap_days"]].copy()
    portfolio.columns = ["Project", "Intervention", "Category", "Cost / Unit", "Volunteer Hours / Unit", "Capacity / Unit", "Max / Week", "Min Gap (Days)"]
    st.dataframe(portfolio, use_container_width=True, hide_index=True, column_config={"Cost / Unit":st.column_config.NumberColumn(format="₹%,.0f"),"Volunteer Hours / Unit":st.column_config.NumberColumn(format="%.2f"),"Capacity / Unit":st.column_config.NumberColumn(format="%.0f")})

    if st.button("Run Allocation", type="primary", use_container_width=True):
        result = {"budget":float(budget),"volunteers":int(volunteers),"hours":float(hours),"horizon":horizon,"objective":objective,"distribution_item":distribution_item,"allocation":None,"schedule":pd.DataFrame(),"error":None}
        if budget == 0:
            result["schedule"] = volunteer_only_options(cfg, int(volunteers), float(hours))
        elif volunteers <= 0:
            result["error"] = "Add at least one volunteer for programme delivery."
        else:
            allocation, error = optimize_programme(interventions, float(budget), int(volunteers), float(hours), horizon.days, objective, ops)
            result["allocation"], result["error"] = allocation, error
            if allocation is not None:
                result["schedule"] = schedule_interventions(allocation[allocation.units > 0].copy(), int(volunteers), float(hours), horizon, ops)
                scheduled_units = int(result["schedule"]["Units Started"].sum()) if not result["schedule"].empty else 0
                allocated_units = int(allocation["units"].sum())
                if scheduled_units != allocated_units:
                    result["allocation"] = None
                    result["schedule"] = pd.DataFrame()
                    result["error"] = "The selected allocation could not be fully scheduled within the available working capacity. Reduce the allocation or adjust the planning inputs."
        st.session_state.plan = result

    plan = st.session_state.plan
    if plan is None:
        st.markdown('<div class="info-card">Set the planning inputs and run an allocation to build a practical programme and calendar.</div>', unsafe_allow_html=True)
    elif plan["allocation"] is None:
        if plan["budget"] == 0:
            st.markdown('<div class="section">Volunteer-led routes</div>', unsafe_allow_html=True)
            st.dataframe(plan["schedule"], use_container_width=True, hide_index=True)
        else:
            st.error(plan["error"] or "No complete intervention fits the selected resources.")
    else:
        active = plan["allocation"].copy()
        used_budget = float(active.allocated_budget.sum())
        used_hours = float(active.volunteer_hours.sum())
        capacity = float(active.planned_beneficiaries.sum())
        k = st.columns(4)
        k[0].metric("Budget Used", money(used_budget))
        k[1].metric("Budget Remaining", money(max(0, plan["budget"] - used_budget)))
        k[2].metric("Volunteer Hours", f"{used_hours:,.2f}")
        k[3].metric("Planned Direct Capacity", f"{capacity:,.0f}")

        st.markdown('<div class="section">Recommended Programme</div>', unsafe_allow_html=True)
        table = active[["project","intervention","category","units","allocated_budget","volunteer_hours","planned_beneficiaries"]].copy()
        table.columns = ["Project","Intervention","Category","Complete Units","Budget","Volunteer Hours","Capacity"]
        st.dataframe(table, use_container_width=True, hide_index=True, column_config={"Budget":st.column_config.NumberColumn(format="₹%,.0f"),"Volunteer Hours":st.column_config.NumberColumn(format="%.2f"),"Capacity":st.column_config.NumberColumn(format="%.0f")})
        if plan["budget"] > used_budget + .01:
            st.info(f"{money(plan['budget']-used_budget)} remains unallocated because the current routes are limited by complete units, cadence and volunteer capacity. The optimizer does not invent partial interventions.")

        schedule = plan["schedule"].copy()
        if not schedule.empty:
            st.markdown(f'<div class="section">Programme Calendar — {horizon.days // 5 if horizon.days >= 5 else 1} Weeks</div>', unsafe_allow_html=True)
            weekly = schedule.groupby(["Week Number","Week"], sort=True).agg(Activities=("Intervention","nunique"), Units=("Units Started","sum"), Budget=("Allocated Budget","sum"), VolunteerHours=("Volunteer Hours","sum"), Capacity=("Planned Capacity","sum")).reset_index()
            st.dataframe(weekly, use_container_width=True, hide_index=True, column_config={"Budget":st.column_config.NumberColumn(format="₹%,.0f"),"VolunteerHours":st.column_config.NumberColumn(format="%.2f"),"Capacity":st.column_config.NumberColumn(format="%.0f")})
            with st.expander("View detailed schedule"):
                st.dataframe(schedule, use_container_width=True, hide_index=True, column_config={"Allocated Budget":st.column_config.NumberColumn(format="₹%,.0f"),"Volunteer Hours":st.column_config.NumberColumn(format="%.2f"),"Elapsed Hours":st.column_config.NumberColumn(format="%.2f"),"Planned Capacity":st.column_config.NumberColumn(format="%.0f")})

            st.markdown('<div class="section">Programme Communication</div>', unsafe_allow_html=True)
            selected = st.selectbox("Select an intervention", active["intervention"].tolist(), key="communication_intervention")
            row = active[active["intervention"] == selected].iloc[0]
            hooks, body, professional = communication_copy(selected, row, plan["distribution_item"])
            hook = st.selectbox("Hook", hooks, key="communication_hook")
            x, y = st.columns(2)
            with x: st.text_area("Social Caption", f"{hook}\n\n{body}\n\nCTA: Follow the programme, volunteer or support the approved intervention.", height=210)
            with y: st.text_area("Professional / CSR Update", professional, height=210)
            st.download_button("Download Allocation CSV", table.to_csv(index=False).encode("utf-8"), "inamigos_resource_allocation.csv", "text/csv", use_container_width=True)

with quick_tab:
    st.markdown('<div class="section">Quick Impact Calculator</div>', unsafe_allow_html=True)
    q1, q2 = st.columns(2)
    with q1: qb = st.number_input("Budget to Evaluate (₹)", min_value=0.0, value=500.0, step=50.0, key="quick_budget")
    with q2: qi = st.selectbox("Support Item", distribution_items, index=0, key="quick_item")
    units, remaining = quick_impact(rates, qi, qb)
    a,b = st.columns(2); a.metric("Complete Units", f"{units:,}"); b.metric("Remaining Budget", money(remaining))
    st.info(f"{money(qb)} can provide {units:,} complete {qi.lower()} unit(s) at the configured rate.")
    comparison=[]
    for item in distribution_items:
        u,r=quick_impact(rates,item,qb); comparison.append({"Item":item,"Complete Units":u,"Budget Used":qb-r,"Remaining":r})
    st.dataframe(pd.DataFrame(comparison), use_container_width=True, hide_index=True, column_config={"Budget Used":st.column_config.NumberColumn(format="₹%,.0f"),"Remaining":st.column_config.NumberColumn(format="₹%,.0f")})

with coverage_tab:
    st.markdown('<div class="section">InAmigos Programme Coverage</div>', unsafe_allow_html=True)
    st.caption("The programme catalogue follows the initiatives described on the public InAmigos Foundation website. Costs are only used in the optimizer where a configured rate or operating rule exists.")
    catalog = project_catalog()
    for start in range(0, len(catalog), 2):
        cols = st.columns(2)
        for j, (_, r) in enumerate(catalog.iloc[start:start+2].iterrows()):
            with cols[j]:
                st.markdown(f'<div class="project-card"><div class="project-name">{r.Project}</div><span class="badge">{r.Area}</span><p class="muted">{r["What the project covers"]}</p><b>{r["Planning route"]}</b></div>', unsafe_allow_html=True)
    st.markdown('<div class="section">Volunteer-led options</div>', unsafe_allow_html=True)
    st.dataframe(volunteer_only_options(cfg, int(volunteers), float(hours)), use_container_width=True, hide_index=True)

with settings_tab:
    st.markdown('<div class="section">Rates & Operating Rules</div>', unsafe_allow_html=True)
    with st.form("settings_form"):
        st.markdown("#### Direct-support rates")
        edited_rates={}
        cols=st.columns(3)
        for i,item in enumerate(rates):
            with cols[i%3]: edited_rates[item]=st.number_input(item,min_value=.01,value=float(rates[item]),step=1.0,key=f"rate_{item}")
        st.markdown("#### Operating rules")
        cols=st.columns(3)
        editable=[
            ("hours_per_working_day","Working hours / day",.5),("learning_session_hours","Learning session hours",.5),
            ("learning_volunteers_per_team","Volunteers per learning team",1.0),("learning_children_per_session","Children per learning cycle",1.0),
            ("stationery_recipients_per_education_cycle","Stationery recipients per cycle",1.0),("cleaning_volunteer_hours","Cleaning volunteer-hours",1.0),
            ("plantation_volunteer_hours","Plantation volunteer-hours",1.0),("plantation_saplings_per_activity","Saplings per plantation activity",1.0),
            ("distribution_duration_hours","Distribution duration hours",.5),("distribution_items_per_volunteer_per_hour","Distribution items / volunteer / hour",1.0),
        ]
        edited_ops=dict(ops)
        for i,(key,label,step) in enumerate(editable):
            with cols[i%3]: edited_ops[key]=st.number_input(label,min_value=.01,value=float(ops[key]),step=float(step),key=f"op_{key}")
        submitted=st.form_submit_button("Apply Settings",use_container_width=True)
        if submitted:
            new_cfg={**cfg,"rates":edited_rates,"operations":edited_ops}
            try:
                validate_config(new_cfg); st.session_state.cfg=new_cfg; st.session_state.plan=None; st.success("Settings applied for this session.")
            except ValueError as exc: st.error(str(exc))
    st.download_button("Download Settings",json.dumps(cfg,indent=2).encode(),"inamigos_optimizer_settings.json","application/json",use_container_width=True)
    incoming=st.file_uploader("Load Settings",type=["json"])
    if incoming:
        try:
            new_cfg=json.loads(incoming.read().decode()); validate_config(new_cfg); st.session_state.cfg=new_cfg; st.session_state.plan=None; st.success("Settings loaded successfully.")
        except Exception as exc: st.error(f"Settings could not be loaded: {exc}")

st.markdown('<div class="muted" style="text-align:center;margin:28px 0 8px;">InAmigos Foundation • Resource Allocation Optimizer</div>', unsafe_allow_html=True)
