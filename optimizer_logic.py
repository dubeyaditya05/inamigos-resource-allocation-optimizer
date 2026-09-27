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
    "Women & skills focus",
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
            "max_per_day": 1, "max_per_week": 2, "min_gap_days": 3, "min_volunteers": 1,
            "split_allowed": False, "kind": "fixed",
        },
        {
            "project": "Project Bachpanshala", "intervention": "Bachpanshala Learning Cycle", "category": "Education",
            "unit_description": f"1 learning session for {children} children + matching stationery support",
            "cost_per_unit": children * float(rates["Stationery Kit"]),
            "volunteer_hours_per_unit": education_team * session_hours,
            "elapsed_hours_per_unit": session_hours,
            "beneficiaries_per_unit": children, "priority_weight": float(weights.get("Project Bachpanshala", 1.35)),
            "max_per_day": 1, "max_per_week": 2, "min_gap_days": 3, "min_volunteers": education_team,
            "split_allowed": False, "kind": "fixed",
        },
        {
            "project": "Project Prakriti", "intervention": "Prakriti Plantation Activity", "category": "Environment",
            "unit_description": f"1 plantation activity with {int(ops['plantation_saplings_per_activity'])} saplings",
            "cost_per_unit": float(rates["Sapling"]) * int(ops["plantation_saplings_per_activity"]),
            "volunteer_hours_per_unit": float(ops["plantation_volunteer_hours"]),
            "elapsed_hours_per_unit": 0.0,
            "beneficiaries_per_unit": 0, "priority_weight": float(weights.get("Project Prakriti", 1.05)),
            "max_per_day": 1, "max_per_week": 1, "min_gap_days": 5, "min_volunteers": 1,
            "split_allowed": True, "kind": "workload",
        },
        {
            "project": "Project Prakriti", "intervention": "Prakriti School/Community Clean-up", "category": "Environment",
            "unit_description": "1 school/community clean-up activity",
            "cost_per_unit": float(rates["School Cleaning Materials"]),
            "volunteer_hours_per_unit": float(ops["cleaning_volunteer_hours"]),
            "elapsed_hours_per_unit": 0.0,
            "beneficiaries_per_unit": 0, "priority_weight": float(weights.get("Project Prakriti", 1.0)),
            "max_per_day": 1, "max_per_week": 1, "min_gap_days": 5, "min_volunteers": 1,
            "split_allowed": True, "kind": "workload",
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
    if objective == "Women & skills focus":
        return 10 if row["project"] in ("Project Udaan", "Project Vikas") else reach * 0.15 + priority
    return reach * priority + 100


def _max_units(row: pd.Series, days: int, volunteers: int, hours_per_day: float) -> int:
    weeks = math.ceil(days / 5)
    cap = min(int(row["max_per_week"]) * weeks, int(row["max_per_day"]) * days)
    if volunteers < int(row["min_volunteers"]):
        return 0
    if not bool(row["split_allowed"]) and float(row["elapsed_hours_per_unit"]) > hours_per_day + 1e-9:
        return 0
    if bool(row["split_allowed"]):
        total_hours = volunteers * hours_per_day * days
        return min(cap, math.floor(total_hours / max(float(row["volunteer_hours_per_unit"]), 1e-9)))
    parallel = max(1, volunteers // int(row["min_volunteers"]))
    return min(cap, parallel * days)


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

    # Balanced plans deliberately seed distinct categories before filling remaining capacity.
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

    ranked = work.assign(value=work["score"] / work["cost_per_unit"].replace(0, 1)).sort_values(["value", "score"], ascending=False)
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
    if active.empty:
        return pd.DataFrame(columns=columns)

    capacity_by_day = [float(volunteers * hours_per_day)] * horizon.days
    starts = []
    last_start = {}
    weekly_count = {}
    used_by_day = [0.0] * horizon.days
    # Stable project/intervention ordering keeps output deterministic.
    rows = active.sort_values(["project", "intervention"]).to_dict("records")
    for row in rows:
        units = int(row["units"])
        for unit_no in range(units):
            name = row["intervention"]
            min_gap = int(row["min_gap_days"])
            week_limit = int(row["max_per_week"])
            candidates = []
            for d in range(horizon.days):
                if last_start.get(name, -10_000) + min_gap > d:
                    continue
                w = d // 5 + 1
                if weekly_count.get((w, name), 0) >= week_limit:
                    continue
                if used_by_day[d] + float(row["volunteer_hours_per_unit"]) > capacity_by_day[d] + 1e-9 and not bool(row["split_allowed"]):
                    continue
                candidates.append(d)
            if not candidates:
                # For split workloads, place work on the earliest available day and let it span days.
                if bool(row["split_allowed"]):
                    remaining = float(row["volunteer_hours_per_unit"])
                    start = next((d for d in range(horizon.days) if last_start.get(name, -10_000) + min_gap <= d and weekly_count.get((d // 5 + 1, name), 0) < week_limit), None)
                    if start is None:
                        continue
                    d = start
                    started = False
                    while remaining > 1e-9 and d < horizon.days:
                        available = capacity_by_day[d] - used_by_day[d]
                        work = min(remaining, max(0.0, available))
                        if work > 1e-9:
                            used_by_day[d] += work
                            rows_out = {
                                "Day": f"Day {d + 1}", "Day Number": d + 1, "Week": f"Week {d // 5 + 1}", "Week Number": d // 5 + 1,
                                "Intervention": name, "Project": row["project"], "Units Started": 1 if not started else 0,
                                "Volunteer Hours": work, "Elapsed Hours": work / volunteers, "Allocated Budget": float(row["cost_per_unit"]) if not started else 0.0,
                                "Planned Capacity": float(row["beneficiaries_per_unit"]) if not started else 0.0,
                            }
                            starts.append(rows_out)
                            started = True
                            remaining -= work
                        d += 1
                    if remaining <= 1e-9:
                        last_start[name] = start
                        weekly_count[(start // 5 + 1, name)] = weekly_count.get((start // 5 + 1, name), 0) + 1
                    continue
                continue
            # Spread complete units across the horizon rather than stacking them at the beginning.
            target = int(round((unit_no + 1) * (horizon.days - 1) / max(1, units)))
            d = min(candidates, key=lambda x: (abs(x - target), used_by_day[x], x))
            used_by_day[d] += float(row["volunteer_hours_per_unit"])
            last_start[name] = d
            w = d // 5 + 1
            weekly_count[(w, name)] = weekly_count.get((w, name), 0) + 1
            starts.append({
                "Day": f"Day {d + 1}", "Day Number": d + 1, "Week": f"Week {w}", "Week Number": w,
                "Intervention": name, "Project": row["project"], "Units Started": 1,
                "Volunteer Hours": float(row["volunteer_hours_per_unit"]), "Elapsed Hours": float(row["elapsed_hours_per_unit"]),
                "Allocated Budget": float(row["cost_per_unit"]), "Planned Capacity": float(row["beneficiaries_per_unit"]),
            })

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
