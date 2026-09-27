from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd


OBJECTIVES = [
    "Balanced programme",
    "Maximum reach",
    "Education focus",
    "Community support focus",
    "Environment focus",
]


@dataclass(frozen=True)
class PlanningHorizon:
    label: str
    days: int


def horizon_days(label: str, ops: dict, budget: float) -> PlanningHorizon:
    if label != "Auto":
        mapping = {
            "1 Day": 1,
            "1 Week": int(ops["working_days_per_week"]),
            "1 Month": int(ops["working_days_per_week"] * ops["weeks_per_month"]),
            "3 Months": int(ops["working_days_per_week"] * ops["weeks_per_month"] * 3),
        }
        return PlanningHorizon(label, mapping[label])
    if budget <= ops["auto_day_budget_threshold"]:
        return PlanningHorizon("1 Day", 1)
    if budget <= ops["auto_week_budget_threshold"]:
        return PlanningHorizon("1 Week", int(ops["working_days_per_week"]))
    if budget <= ops["auto_month_budget_threshold"]:
        return PlanningHorizon("1 Month", int(ops["working_days_per_week"] * ops["weeks_per_month"]))
    return PlanningHorizon("3 Months", int(ops["working_days_per_week"] * ops["weeks_per_month"] * 3))


def validate_config(cfg: dict) -> None:
    rates = cfg["rates"]
    required = [
        "Meal for 1 person", "Pencil", "Pen", "Notebook", "Stationery Kit",
        "School Bag", "Book", "Sapling", "Water Bottle", "Hygiene Kit",
        "School Cleaning Materials",
    ]
    missing = [k for k in required if k not in rates]
    if missing:
        raise ValueError(f"Missing rates: {', '.join(missing)}")
    if any(float(rates[k]) <= 0 for k in required):
        raise ValueError("All configured rates must be greater than zero.")
    ops = cfg["operations"]
    for key in (
        "hours_per_working_day", "working_days_per_week", "weeks_per_month",
        "learning_session_hours", "learning_volunteers_per_team", "learning_children_per_session",
        "cleaning_volunteer_hours", "plantation_volunteer_hours", "plantation_saplings_per_activity",
        "distribution_duration_hours", "distribution_items_per_volunteer_per_hour",
    ):
        if float(ops[key]) <= 0:
            raise ValueError(f"{key} must be greater than zero.")
    if int(ops["learning_children_per_session"]) != int(ops["stationery_recipients_per_education_cycle"]):
        raise ValueError("Education capacity and stationery recipients must match.")
    if int(ops["learning_volunteers_per_team"]) < 1:
        raise ValueError("Education team size must be positive.")
    for key in ("auto_day_budget_threshold", "auto_week_budget_threshold", "auto_month_budget_threshold"):
        if float(ops[key]) < 0:
            raise ValueError(f"{key} cannot be negative.")
    if not (ops["auto_day_budget_threshold"] <= ops["auto_week_budget_threshold"] <= ops["auto_month_budget_threshold"]):
        raise ValueError("Automatic horizon thresholds must be in ascending order.")


def _base_rows(cfg: dict, volunteers: int, distribution_item: str) -> list[dict]:
    rates, ops, weights = cfg["rates"], cfg["operations"], cfg.get("priority_weights", {})
    children = int(ops["learning_children_per_session"])
    education_team = int(ops["learning_volunteers_per_team"])
    session_hours = float(ops["learning_session_hours"])
    distribution_items = math.floor(
        volunteers * float(ops["distribution_duration_hours"]) * float(ops["distribution_items_per_volunteer_per_hour"])
    )
    return [
        {
            "project": "Project Seva", "intervention": "Seva Meal Distribution", "category": "Community",
            "unit_description": f"1 field distribution event of {distribution_items} × {distribution_item}",
            "cost_per_unit": distribution_items * float(rates[distribution_item]),
            "volunteer_hours_per_unit": volunteers * float(ops["distribution_duration_hours"]),
            "elapsed_hours_per_unit": float(ops["distribution_duration_hours"]),
            "beneficiaries_per_unit": distribution_items, "priority_weight": float(weights.get("Project Seva", 1.1)),
            "min_volunteers": 1, "split_allowed": False, "kind": "fixed",
        },
        {
            "project": "Project Bachpanshala", "intervention": "Bachpanshala Learning Cycle", "category": "Education",
            "unit_description": f"1 learning session for {children} children + matching stationery support",
            "cost_per_unit": children * float(rates["Stationery Kit"]),
            "volunteer_hours_per_unit": education_team * session_hours,
            "elapsed_hours_per_unit": session_hours,
            "beneficiaries_per_unit": children, "priority_weight": float(weights.get("Project Bachpanshala", 1.35)),
            "min_volunteers": education_team, "split_allowed": False, "kind": "fixed",
        },
        {
            "project": "Project Prakriti", "intervention": "Prakriti Plantation Activity", "category": "Environment",
            "unit_description": f"1 plantation activity with {int(ops['plantation_saplings_per_activity'])} saplings",
            "cost_per_unit": float(rates["Sapling"]) * int(ops["plantation_saplings_per_activity"]),
            "volunteer_hours_per_unit": float(ops["plantation_volunteer_hours"]),
            "elapsed_hours_per_unit": None,
            "beneficiaries_per_unit": 0, "priority_weight": float(weights.get("Project Prakriti", 1.05)),
            "min_volunteers": 1, "split_allowed": True, "kind": "workload",
        },
        {
            "project": "Project Prakriti", "intervention": "Prakriti School/Community Clean-up", "category": "Environment",
            "unit_description": "1 school/community clean-up activity",
            "cost_per_unit": float(rates["School Cleaning Materials"]),
            "volunteer_hours_per_unit": float(ops["cleaning_volunteer_hours"]),
            "elapsed_hours_per_unit": None,
            "beneficiaries_per_unit": 0, "priority_weight": float(weights.get("Project Prakriti", 1.0)),
            "min_volunteers": 1, "split_allowed": True, "kind": "workload",
        },
    ]

def build_programme_interventions(cfg: dict, volunteers: int, distribution_item: str) -> pd.DataFrame:
    rows = _base_rows(cfg, volunteers, distribution_item)
    return pd.DataFrame(rows)


def project_catalog() -> pd.DataFrame:
    return pd.DataFrame([
        ["Project Seva", "Food & basic support", "Budgeted", "Food distribution and essential support."],
        ["Project Bachpanshala", "Child education", "Budgeted", "Learning sessions, school support and stationery."],
        ["Project Jeev", "Animal welfare", "Field-configured", "Animal rescue, protection and feeding activities."],
        ["Project Udaan", "Women empowerment", "Field-configured", "Skill development and financial-independence support."],
        ["Project Prakriti", "Environment", "Budgeted", "Plantation, clean-up and sustainability activities."],
        ["Project Vikas", "Skills & employability", "Volunteer-led", "Skill development and internship/employability programmes."],
    ], columns=["Project", "Area", "Planning route", "What the project covers"])


def _score(row: pd.Series, objective: str) -> float:
    reach = float(row["beneficiaries_per_unit"])
    priority = float(row["priority_weight"])
    category = row["category"]
    if objective == "Maximum reach":
        return reach * 1.2 + priority
    if objective == "Education focus":
        return (reach * 4 + 100) if category == "Education" else reach * 0.15 + priority
    if objective == "Community support focus":
        return (reach * 4 + 100) if category == "Community" else reach * 0.15 + priority
    if objective == "Environment focus":
        return (reach * 2 + 100) if category == "Environment" else reach * 0.15 + priority
    return reach * priority + 100


def _max_units(row: pd.Series, days: int, volunteers: int, hours_per_day: float) -> int:
    if volunteers < int(row["min_volunteers"]):
        return 0
    daily_capacity = volunteers * hours_per_day
    if not bool(row["split_allowed"]):
        if float(row["elapsed_hours_per_unit"]) > hours_per_day + 1e-9:
            return 0
        return math.floor((daily_capacity * days) / max(float(row["volunteer_hours_per_unit"]), 1e-9))
    total_hours = daily_capacity * days
    return math.floor(total_hours / max(float(row["volunteer_hours_per_unit"]), 1e-9))

def optimize_programme(df: pd.DataFrame, budget: float, volunteers: int, hours_per_day: float, horizon_days_count: int, objective: str, ops: dict):
    if df.empty:
        return None, "No budgeted interventions are available for this configuration."
    if objective not in OBJECTIVES:
        return None, "Unknown planning objective."
    if budget < 0 or volunteers < 0 or hours_per_day <= 0:
        return None, "Planning inputs are invalid."

    work = df.copy()
    work["max_units"] = work.apply(lambda r: _max_units(r, horizon_days_count, volunteers, hours_per_day), axis=1)
    work["score"] = work.apply(lambda r: _score(r, objective), axis=1)
    work = work[work["max_units"] > 0].copy()
    if work.empty:
        return None, "No complete intervention fits the available volunteer capacity and planning horizon."

    chosen = {i: 0 for i in work.index}
    remaining_budget = float(budget)
    remaining_hours = float(volunteers * hours_per_day * horizon_days_count)
    categories = []
    if objective == "Balanced programme" and horizon_days_count >= 10:
        for i, r in work.sort_values(["priority_weight", "score"], ascending=False).iterrows():
            if r["category"] not in categories and r["cost_per_unit"] <= remaining_budget and r["volunteer_hours_per_unit"] <= remaining_hours:
                chosen[i] = 1
                remaining_budget -= float(r["cost_per_unit"])
                remaining_hours -= float(r["volunteer_hours_per_unit"])
                categories.append(r["category"])
                if len(categories) >= min(3, work["category"].nunique()):
                    break

    value = work["score"] / work["cost_per_unit"].replace(0, 1)
    if objective == "Education focus":
        utility = work["category"].eq("Education").astype(float) * 1000 + value
    elif objective == "Community support focus":
        utility = work["category"].eq("Community").astype(float) * 1000 + value
    elif objective == "Environment focus":
        utility = work["category"].eq("Environment").astype(float) * 1000 + value
    elif objective == "Maximum reach":
        utility = work["beneficiaries_per_unit"] / work["cost_per_unit"].replace(0, 1)
    else:
        utility = value
    ranked = work.assign(utility=utility, value=value).sort_values(["utility", "score"], ascending=False)
    changed = True
    while changed:
        changed = False
        for i, r in ranked.iterrows():
            if chosen[i] >= int(r["max_units"]):
                continue
            if float(r["cost_per_unit"]) <= remaining_budget + 1e-9 and float(r["volunteer_hours_per_unit"]) <= remaining_hours + 1e-9:
                chosen[i] += 1
                remaining_budget -= float(r["cost_per_unit"])
                remaining_hours -= float(r["volunteer_hours_per_unit"])
                changed = True

    work["units"] = pd.Series(chosen).reindex(work.index).fillna(0).astype(int)
    work["allocated_budget"] = work["units"] * work["cost_per_unit"]
    work["volunteer_hours"] = work["units"] * work["volunteer_hours_per_unit"]
    work["planned_beneficiaries"] = work["units"] * work["beneficiaries_per_unit"]
    work = work[work["units"] > 0].copy()
    if work.empty:
        return None, "No complete intervention fits the selected budget and volunteer capacity."
    return work, None


def schedule_interventions(active: pd.DataFrame, volunteers: int, hours_per_day: float, horizon: PlanningHorizon, ops: dict) -> pd.DataFrame:
    columns = ["Day", "Day Number", "Week", "Week Number", "Intervention", "Project", "Units Started", "Volunteer Hours", "Elapsed Hours", "Allocated Budget", "Planned Capacity"]
    if active.empty or volunteers <= 0 or hours_per_day <= 0:
        return pd.DataFrame(columns=columns)

    daily_capacity = float(volunteers * hours_per_day)
    used_by_day = [0.0] * horizon.days
    starts = []
    # Schedule complete, non-splittable activities first. This prevents a long
    # workload activity from consuming every day before fixed sessions are placed.
    rows = active.sort_values(["project", "intervention"]).to_dict("records")
    fixed = [r for r in rows if not bool(r["split_allowed"])]
    split = [r for r in rows if bool(r["split_allowed"])]

    def add_fixed_unit(row, unit_no, day):
        work = float(row["volunteer_hours_per_unit"])
        used_by_day[day] += work
        starts.append({
            "Day": f"Day {day + 1}", "Day Number": day + 1, "Week": f"Week {day // 5 + 1}", "Week Number": day // 5 + 1,
            "Intervention": row["intervention"], "Project": row["project"], "Units Started": 1,
            "Volunteer Hours": work, "Elapsed Hours": float(row["elapsed_hours_per_unit"]),
            "Allocated Budget": float(row["cost_per_unit"]), "Planned Capacity": float(row["beneficiaries_per_unit"]),
        })

    for row in fixed:
        units = int(row["units"])
        for unit_no in range(units):
            candidates = [d for d in range(horizon.days) if used_by_day[d] + float(row["volunteer_hours_per_unit"]) <= daily_capacity + 1e-9]
            if not candidates:
                continue
            # Evenly distribute starts across the horizon while preferring lower-load days.
            target = int(round((unit_no + 1) * (horizon.days - 1) / max(1, units)))
            day = min(candidates, key=lambda d: (abs(d - target), used_by_day[d], d))
            add_fixed_unit(row, unit_no, day)

    # Then fill remaining capacity with split workloads. A unit may span days;
    # each row records the actual volunteer-hours and elapsed time for that day.
    for row in split:
        for unit_no in range(int(row["units"])):
            remaining = float(row["volunteer_hours_per_unit"])
            unit_rows = []
            for d in range(horizon.days):
                if remaining <= 1e-9:
                    break
                available = max(0.0, daily_capacity - used_by_day[d])
                if available <= 1e-9:
                    continue
                work = min(remaining, available)
                unit_rows.append({
                    "Day": f"Day {d + 1}", "Day Number": d + 1, "Week": f"Week {d // 5 + 1}", "Week Number": d // 5 + 1,
                    "Intervention": row["intervention"], "Project": row["project"], "Units Started": 1 if not unit_rows else 0,
                    "Volunteer Hours": work, "Elapsed Hours": work / volunteers,
                    "Allocated Budget": float(row["cost_per_unit"]) if not unit_rows else 0.0,
                    "Planned Capacity": float(row["beneficiaries_per_unit"]) if not unit_rows else 0.0,
                })
                remaining -= work
            if remaining <= 1e-9:
                for item in unit_rows:
                    used_by_day[item["Day Number"] - 1] += float(item["Volunteer Hours"])
                starts.extend(unit_rows)

    return pd.DataFrame(starts, columns=columns).sort_values(["Day Number", "Project", "Intervention"]).reset_index(drop=True) if starts else pd.DataFrame(columns=columns)

def quick_impact(rates: dict, item: str, budget: float) -> tuple[int, float]:
    price = float(rates[item])
    units = math.floor(max(0.0, float(budget)) / price)
    return units, float(budget) - units * price


def volunteer_only_options(cfg: dict, volunteers: int, hours_per_day: float) -> pd.DataFrame:
    if volunteers <= 0 or hours_per_day <= 0:
        return pd.DataFrame(columns=["Project", "Activity", "Volunteers", "Duration", "Potential Output", "Requirement"])
    ops = cfg["operations"]
    return pd.DataFrame([
        ["Project Bachpanshala", "Learning / reading support", min(volunteers, int(ops["learning_volunteers_per_team"])), f"{ops['learning_session_hours']:.1f} hours", "Structured learning support", "Existing venue and learning materials"],
        ["Project Jeev", "Animal welfare support / field coordination", min(volunteers, 2), "Field-defined", "Volunteer support for approved animal-welfare work", "Local partner / approved field activity"],
        ["Project Udaan", "Women skill-support / outreach", min(volunteers, 2), "Field-defined", "Volunteer support for approved women-empowerment work", "Partner group and defined activity"],
        ["Project Vikas", "Skill / internship support", min(volunteers, 2), "Field-defined", "Mentoring, research or programme support", "Approved programme scope"],
        ["Project Prakriti", "Community cleanliness support", volunteers, f"{ops['cleaning_volunteer_hours'] / volunteers:.2f} hours", "1 clean-up activity", "Cleaning materials and local permission"],
    ], columns=["Project", "Activity", "Volunteers", "Duration", "Potential Output", "Requirement"])
