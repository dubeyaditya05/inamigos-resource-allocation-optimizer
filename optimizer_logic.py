from __future__ import annotations

import math
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp


@dataclass(frozen=True)
class PlanningHorizon:
    label: str
    days: int


OBJECTIVES = [
    "Maximum reach",
    "Balanced programme",
    "Education focus",
    "Community support focus",
    "Environment focus",
]


def horizon_days(label: str, ops: dict, budget: float) -> PlanningHorizon:
    if label != "Auto":
        days = {
            "1 Day": 1,
            "1 Week": int(ops["working_days_per_week"]),
            "1 Month": int(ops["working_days_per_week"] * ops["weeks_per_month"]),
            "3 Months": int(ops["working_days_per_week"] * ops["weeks_per_month"] * 3),
        }[label]
        return PlanningHorizon(label, days)

    if budget <= 0 or budget <= ops["auto_day_budget_threshold"]:
        return PlanningHorizon("1 Day", 1)
    if budget <= ops["auto_week_budget_threshold"]:
        return PlanningHorizon("1 Week", int(ops["working_days_per_week"]))
    if budget <= ops["auto_month_budget_threshold"]:
        return PlanningHorizon(
            "1 Month", int(ops["working_days_per_week"] * ops["weeks_per_month"])
        )
    return PlanningHorizon(
        "3 Months",
        int(ops["working_days_per_week"] * ops["weeks_per_month"] * 3),
    )


def validate_config(cfg: dict) -> None:
    rates = cfg["rates"]
    ops = cfg["operations"]
    required_rates = [
        "Meal for 1 person", "Pencil", "Pen", "Notebook", "Stationery Kit",
        "School Bag", "Book", "Sapling", "Water Bottle", "Hygiene Kit",
        "School Cleaning Materials",
    ]
    if any(key not in rates for key in required_rates):
        raise ValueError("All required rates must be present.")
    if any(float(rates[key]) <= 0 for key in required_rates):
        raise ValueError("All rates must be greater than zero.")

    positive = [
        "hours_per_working_day", "working_days_per_week", "weeks_per_month",
        "learning_session_hours", "learning_volunteers_per_team",
        "learning_teams_per_session", "learning_children_per_session",
        "stationery_recipients_per_education_cycle", "cleaning_volunteer_hours",
        "plantation_volunteer_hours", "plantation_saplings_per_activity",
        "distribution_duration_hours", "distribution_items_per_volunteer_per_hour",
        "max_education_cycles_per_day", "max_cleaning_drives_per_day",
        "max_plantation_activities_per_day", "max_distribution_events_per_day",
        "education_max_per_week", "cleaning_max_per_week", "plantation_max_per_week",
        "distribution_max_per_week", "education_min_gap_days", "cleaning_min_gap_days",
        "plantation_min_gap_days", "distribution_min_gap_days",
        "auto_day_budget_threshold", "auto_week_budget_threshold", "auto_month_budget_threshold",
    ]
    if any(float(ops[key]) <= 0 for key in positive):
        raise ValueError("All operating values must be greater than zero.")
    if int(ops["learning_volunteers_per_team"]) * int(ops["learning_teams_per_session"]) < 1:
        raise ValueError("Education team size must be positive.")
    if int(ops["learning_children_per_session"]) != int(ops["stationery_recipients_per_education_cycle"]):
        raise ValueError("Education capacity and stationery recipients must match.")
    if not (0 < float(ops["balanced_max_category_budget_share"]) <= 1):
        raise ValueError("Balanced budget share must be between 0 and 1.")
    if int(ops["balanced_min_categories_for_long_horizon"]) < 1:
        raise ValueError("Balanced minimum categories must be positive.")
    if int(ops["auto_day_budget_threshold"]) > int(ops["auto_week_budget_threshold"]):
        raise ValueError("Auto day threshold must not exceed auto week threshold.")
    if int(ops["auto_week_budget_threshold"]) > int(ops["auto_month_budget_threshold"]):
        raise ValueError("Auto week threshold must not exceed auto month threshold.")


def build_programme_interventions(cfg: dict, volunteers: int, distribution_item: str) -> pd.DataFrame:
    rates = cfg["rates"]
    ops = cfg["operations"]
    weights = cfg.get("priority_weights", {})

    children = int(ops["learning_children_per_session"])
    team_size = int(ops["learning_volunteers_per_team"])
    teams = int(ops["learning_teams_per_session"])
    session_hours = float(ops["learning_session_hours"])

    rows = [
        {
            "project": "Project Bachpanshala",
            "intervention": "Education Cycle",
            "category": "Education",
            "unit_description": f"1 learning session for {children} children + stationery support for the same {children} children",
            "cost_per_unit": children * float(rates["Stationery Kit"]),
            "volunteer_hours_per_unit": team_size * teams * session_hours,
            "elapsed_hours_per_unit": session_hours,
            "beneficiaries_per_unit": children,
            "priority_weight": float(weights.get("Education Cycle", 1.35)),
            "max_per_day": int(ops["max_education_cycles_per_day"]),
            "max_per_week": int(ops["education_max_per_week"]),
            "min_gap_days": int(ops["education_min_gap_days"]),
            "min_volunteers": team_size * teams,
            "split_allowed": False,
            "kind": "fixed",
        },
        {
            "project": "Project Prakriti",
            "intervention": "School Cleaning Drive",
            "category": "Community",
            "unit_description": "1 school/community cleaning drive",
            "cost_per_unit": float(rates["School Cleaning Materials"]),
            "volunteer_hours_per_unit": float(ops["cleaning_volunteer_hours"]),
            "elapsed_hours_per_unit": float(ops["cleaning_volunteer_hours"]) / max(1, int(volunteers)),
            "beneficiaries_per_unit": 0,
            "priority_weight": float(weights.get("School Cleaning Drive", 1.0)),
            "max_per_day": int(ops["max_cleaning_drives_per_day"]),
            "max_per_week": int(ops["cleaning_max_per_week"]),
            "min_gap_days": int(ops["cleaning_min_gap_days"]),
            "min_volunteers": 1,
            "split_allowed": True,
            "kind": "workload",
        },
        {
            "project": "Project Prakriti",
            "intervention": "Plantation Activity",
            "category": "Environment",
            "unit_description": f"1 plantation activity with {int(ops['plantation_saplings_per_activity'])} saplings",
            "cost_per_unit": float(rates["Sapling"]) * int(ops["plantation_saplings_per_activity"]),
            "volunteer_hours_per_unit": float(ops["plantation_volunteer_hours"]),
            "elapsed_hours_per_unit": float(ops["plantation_volunteer_hours"]) / max(1, int(volunteers)),
            "beneficiaries_per_unit": 0,
            "priority_weight": float(weights.get("Plantation Activity", 1.05)),
            "max_per_day": int(ops["max_plantation_activities_per_day"]),
            "max_per_week": int(ops["plantation_max_per_week"]),
            "min_gap_days": int(ops["plantation_min_gap_days"]),
            "min_volunteers": 1,
            "split_allowed": True,
            "kind": "workload",
        },
    ]

    if volunteers > 0:
        items = math.floor(
            volunteers
            * float(ops["distribution_duration_hours"])
            * float(ops["distribution_items_per_volunteer_per_hour"])
        )
        if items > 0:
            rows.append(
                {
                    "project": "Project Seva",
                    "intervention": "Distribution Event",
                    "category": "Community",
                    "unit_description": f"1 distribution event of {items} × {distribution_item}",
                    "cost_per_unit": items * float(rates[distribution_item]),
                    "volunteer_hours_per_unit": volunteers * float(ops["distribution_duration_hours"]),
                    "elapsed_hours_per_unit": float(ops["distribution_duration_hours"]),
                    "beneficiaries_per_unit": items,
                    "priority_weight": float(weights.get("Distribution Event", 1.1)),
                    "max_per_day": int(ops["max_distribution_events_per_day"]),
                    "max_per_week": int(ops["distribution_max_per_week"]),
                    "min_gap_days": int(ops["distribution_min_gap_days"]),
                    "min_volunteers": 1,
                    "split_allowed": False,
                    "kind": "fixed",
                }
            )

    return pd.DataFrame(rows)


def _objective_values(df: pd.DataFrame, objective: str) -> np.ndarray:
    reach = df["beneficiaries_per_unit"].to_numpy(float)
    priority = df["priority_weight"].to_numpy(float)
    category = df["category"]
    if objective == "Maximum reach":
        return reach + 0.1 * priority
    if objective == "Balanced programme":
        return reach * priority + 10
    target = {
        "Education focus": "Education",
        "Community support focus": "Community",
        "Environment focus": "Environment",
    }[objective]
    return np.where(category.eq(target), reach * 4 + 100, reach * 0.25)


def _max_units_for_horizon(row: pd.Series, days: int, ops: dict, volunteers: int, hours_per_day: float) -> int:
    weeks = math.ceil(days / int(ops["working_days_per_week"]))
    cadence_cap = int(row["max_per_week"]) * weeks
    day_cap = int(row["max_per_day"]) * days
    cap = min(cadence_cap, day_cap)
    if not bool(row["split_allowed"]):
        if volunteers < int(row["min_volunteers"]):
            return 0
        if float(row["elapsed_hours_per_unit"]) > hours_per_day + 1e-9:
            return 0
        cap = min(cap, int(volunteers // int(row["min_volunteers"])) * days * int(row["max_per_day"]))
    return max(0, cap)


def _category_caps(df: pd.DataFrame, budget: float, objective: str, ops: dict):
    rows, lbs, ubs = [], [], []
    if objective != "Balanced programme":
        return rows, lbs, ubs
    share = float(ops["balanced_max_category_budget_share"])
    for category in df["category"].drop_duplicates():
        row = np.zeros(len(df) * 2)
        for i, cat in enumerate(df["category"]):
            if cat == category:
                row[i] = float(df.loc[i, "cost_per_unit"])
        highest = max(float(df.loc[df["category"] == category, "cost_per_unit"].max()), 0.0)
        rows.append(row)
        lbs.append(-np.inf)
        ubs.append(max(highest, budget * share))
    return rows, lbs, ubs


def schedule_interventions(
    allocation: pd.DataFrame,
    volunteers: int,
    hours_per_day: float,
    horizon: PlanningHorizon,
    ops: dict,
) -> pd.DataFrame:
    columns = [
        "Day", "Week", "Intervention", "Units Started", "Volunteer Hours",
        "Elapsed Hours", "Allocated Budget", "Planned Capacity",
    ]
    if allocation is None or allocation.empty or volunteers <= 0 or hours_per_day <= 0:
        return pd.DataFrame(columns=columns)

    daily_capacity = volunteers * hours_per_day
    used = [0.0] * horizon.days
    weekly_starts: dict[tuple[int, str], int] = {}
    daily_starts: dict[tuple[int, str], int] = {}
    last_start: dict[str, int] = {}
    meta = allocation.set_index("intervention")
    tasks: list[tuple[str, int]] = []
    for _, row in allocation.iterrows():
        for unit in range(int(row["units"])):
            tasks.append((row["intervention"], unit))

    # Place fixed sessions first, then workload activities.
    tasks.sort(key=lambda x: (bool(meta.loc[x[0], "split_allowed"]), x[0], x[1]))
    rows = []

    def week(day_index: int) -> int:
        return day_index // int(ops["working_days_per_week"])

    def start_days(name: str, min_gap: int, max_per_week: int, max_per_day: int):
        for d in range(horizon.days):
            if weekly_starts.get((week(d), name), 0) >= max_per_week:
                continue
            same_day = daily_starts.get((d, name), 0)
            if same_day >= max_per_day:
                continue
            if name in last_start and d != last_start[name] and d - last_start[name] < min_gap:
                continue
            yield d

    for name, unit in tasks:
        row = meta.loc[name]
        unit_hours = float(row["volunteer_hours_per_unit"])
        unit_budget = float(row["cost_per_unit"])
        unit_capacity = float(row["beneficiaries_per_unit"])
        max_per_day = int(row["max_per_day"])
        max_per_week = int(row["max_per_week"])
        min_gap = int(row["min_gap_days"])

        if not bool(row["split_allowed"]):
            possible = []
            for d in start_days(name, min_gap, max_per_week, max_per_day):
                if possible and max_per_day <= 0:
                    continue
                if used[d] + unit_hours <= daily_capacity + 1e-9:
                    possible.append(d)
            if not possible:
                return pd.DataFrame(columns=columns)
            target = round(unit * max(0, horizon.days - 1) / max(1, int(meta.loc[name, "units"]) - 1))
            d = min(possible, key=lambda x: (abs(x - target), used[x]))
            used[d] += unit_hours
            weekly_starts[(week(d), name)] = weekly_starts.get((week(d), name), 0) + 1
            daily_starts[(d, name)] = daily_starts.get((d, name), 0) + 1
            last_start[name] = d
            rows.append({
                "Day": f"Day {d + 1}",
                "Week": f"Week {week(d) + 1}",
                "Intervention": name,
                "Units Started": 1,
                "Volunteer Hours": unit_hours,
                "Elapsed Hours": float(row["elapsed_hours_per_unit"]),
                "Allocated Budget": unit_budget,
                "Planned Capacity": unit_capacity,
            })
            continue

        remaining = unit_hours
        started = False
        candidate_days = list(start_days(name, min_gap, max_per_week, max_per_day))
        if not candidate_days:
            return pd.DataFrame(columns=columns)
        start = min(candidate_days, key=lambda d: (used[d], d))
        for d in range(start, horizon.days):
            available = daily_capacity - used[d]
            if available <= 1e-9:
                continue
            work = min(remaining, available)
            if work <= 1e-9:
                continue
            elapsed = work / volunteers
            used[d] += work
            rows.append({
                "Day": f"Day {d + 1}",
                "Week": f"Week {week(d) + 1}",
                "Intervention": name,
                "Units Started": 1 if not started else 0,
                "Volunteer Hours": work,
                "Elapsed Hours": elapsed,
                "Allocated Budget": unit_budget if not started else 0.0,
                "Planned Capacity": unit_capacity if not started else 0.0,
            })
            started = True
            remaining -= work
            if remaining <= 1e-9:
                weekly_starts[(week(start), name)] = weekly_starts.get((week(start), name), 0) + 1
                daily_starts[(start, name)] = daily_starts.get((start, name), 0) + 1
                last_start[name] = start
                break
        if remaining > 1e-9:
            return pd.DataFrame(columns=columns)

    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result
    result["_day_sort"] = result["Day"].str.extract(r"(\d+)")[0].astype(int)
    result = result.sort_values(["_day_sort", "Intervention", "Units Started"], kind="stable").drop(columns="_day_sort").reset_index(drop=True)
    return result


def optimize_programme(
    df: pd.DataFrame,
    budget: float,
    volunteers: int,
    hours_per_day: float,
    horizon_days_count: int,
    objective: str,
    ops: dict,
):
    if df.empty:
        return None, "No interventions are available."
    if objective not in OBJECTIVES:
        return None, "Unknown planning objective."
    if budget < 0 or volunteers < 0 or hours_per_day <= 0 or horizon_days_count < 1:
        return None, "Planning inputs are invalid."

    n = len(df)
    values = _objective_values(df, objective)
    max_units = np.array([
        _max_units_for_horizon(row, horizon_days_count, ops, volunteers, hours_per_day)
        for _, row in df.iterrows()
    ], dtype=int)
    if max_units.sum() == 0:
        return None, "No complete intervention fits the current volunteer capacity and planning horizon."

    # x_i = complete intervention units; y_i = whether the intervention is selected.
    c = np.r_[-values, np.full(n, -5.0 if objective == "Balanced programme" else 0.0)]
    rows, lower, upper = [], [], []

    cost = np.zeros(2 * n); cost[:n] = df["cost_per_unit"].to_numpy(float)
    hours = np.zeros(2 * n); hours[:n] = df["volunteer_hours_per_unit"].to_numpy(float)
    rows += [cost, hours]; lower += [-np.inf, -np.inf]; upper += [budget, volunteers * hours_per_day * horizon_days_count]

    for i, _ in df.iterrows():
        link = np.zeros(2 * n); link[i] = 1; link[n + i] = -max_units[i]
        active = np.zeros(2 * n); active[i] = 1; active[n + i] = -1
        rows += [link, active]; lower += [-np.inf, 0]; upper += [0, np.inf]

    cat_rows, cat_lbs, cat_ubs = _category_caps(df, budget, objective, ops)
    rows += cat_rows; lower += cat_lbs; upper += cat_ubs

    # Long balanced plans should contain multiple categories when feasible.
    if objective == "Balanced programme" and horizon_days_count >= int(ops["balanced_long_horizon_days"]):
        categories = list(df["category"].drop_duplicates())
        feasible_categories = []
        daily_capacity = volunteers * hours_per_day
        for category in categories:
            candidates = df[df["category"] == category]
            if any(
                float(r.cost_per_unit) <= budget
                and int(r.min_volunteers) <= volunteers
                and (bool(r.split_allowed) or float(r.elapsed_hours_per_unit) <= hours_per_day)
                for _, r in candidates.iterrows()
            ):
                feasible_categories.append(category)
        target = min(int(ops["balanced_min_categories_for_long_horizon"]), len(feasible_categories))
        if target > 1:
            activation = np.zeros((len(feasible_categories), 2 * n))
            for j, category in enumerate(feasible_categories):
                for i, cat in enumerate(df["category"]):
                    if cat == category:
                        activation[j, n + i] = 1
            rows.append(activation.sum(axis=0)); lower.append(target); upper.append(np.inf)

    result = milp(
        c=c,
        integrality=np.ones(2 * n),
        bounds=Bounds(np.zeros(2 * n), np.r_[max_units.astype(float), np.ones(n)]),
        constraints=LinearConstraint(np.vstack(rows), np.array(lower), np.array(upper)),
        options={"time_limit": 8},
    )
    if not result.success:
        return None, str(result.message)

    out = df.copy()
    out["units"] = np.rint(result.x[:n]).astype(int)
    out["allocated_budget"] = out["units"] * out["cost_per_unit"]
    out["volunteer_hours"] = out["units"] * out["volunteer_hours_per_unit"]
    out["planned_beneficiaries"] = out["units"] * out["beneficiaries_per_unit"]
    if int(out["units"].sum()) == 0:
        return None, "No complete intervention fits the current budget, volunteer capacity and planning horizon."

    # Align the aggregate solution with the actual day-by-day cadence rules.
    for _ in range(int(out["units"].sum()) + 1):
        active = out[out["units"] > 0].copy()
        if active.empty:
            return out, None
        schedule = schedule_interventions(
            active, volunteers, hours_per_day,
            PlanningHorizon("", horizon_days_count), ops,
        )
        required = active.set_index("intervention")["units"].astype(int).to_dict()
        placed = schedule.groupby("Intervention")["Units Started"].sum().to_dict() if not schedule.empty else {}
        if placed == required:
            return out, None

        candidates = []
        for i in out.index[out["units"] > 0]:
            name = out.loc[i, "intervention"]
            category = out.loc[i, "category"]
            if objective == "Balanced programme" and horizon_days_count >= int(ops["balanced_long_horizon_days"]):
                if int((out["category"] == category).sum()) > 1 and int(out.loc[i, "units"]) == 1:
                    continue
            candidates.append((float(values[i]), i))
        if not candidates:
            return None, "The selected plan cannot be scheduled within the configured cadence and working-day limits."
        _, remove_i = min(candidates)
        out.loc[remove_i, "units"] -= 1
        out["allocated_budget"] = out["units"] * out["cost_per_unit"]
        out["volunteer_hours"] = out["units"] * out["volunteer_hours_per_unit"]
        out["planned_beneficiaries"] = out["units"] * out["beneficiaries_per_unit"]

    return None, "The selected plan could not be scheduled."


def quick_impact(rates: dict, item: str, budget: float) -> tuple[int, float]:
    budget = max(0.0, float(budget))
    price = float(rates[item])
    units = math.floor(budget / price) if price > 0 else 0
    return units, budget - units * price


PROJECT_CATALOG = [
    {
        "Project": "Project Seva",
        "Focus": "Food and clothing support",
        "Verified activities": "Food distribution; clothing distribution",
        "Planning basis": "Budgeted distribution model",
    },
    {
        "Project": "Project Bachpanshala",
        "Focus": "Education and child development",
        "Verified activities": "Learning sessions; school supplies; workshops/camps; mentorship; awareness",
        "Planning basis": "Budgeted education-cycle model; other activities volunteer-led until field rules are configured",
    },
    {
        "Project": "Project Jeev",
        "Focus": "Animal welfare",
        "Verified activities": "Feeding; rescue/protection; medical care; safe shelter; animal-rights awareness",
        "Planning basis": "Volunteer-led template; no invented field costs",
    },
    {
        "Project": "Project Udaan",
        "Focus": "Women empowerment",
        "Verified activities": "Awareness campaigns; skill-development workshops; entrepreneurial support; SHG collaboration; menstrual-hygiene awareness",
        "Planning basis": "Volunteer-led template; no invented field costs",
    },
    {
        "Project": "Project Prakriti",
        "Focus": "Environmental conservation",
        "Verified activities": "Tree plantation; clean-up campaigns; conservation workshops; water-conservation activities",
        "Planning basis": "Budgeted plantation/clean-up models; other activities volunteer-led until field rules are configured",
    },
    {
        "Project": "Project Vikas",
        "Focus": "Employability and skill development",
        "Verified activities": "Internships; webinars/seminars; resume building; interview preparation; career/skill programmes",
        "Planning basis": "Volunteer-led template; no invented field costs",
    },
]

def project_catalog() -> pd.DataFrame:
    return pd.DataFrame(PROJECT_CATALOG)


def volunteer_only_options(cfg: dict, volunteers: int, hours_per_day: float) -> pd.DataFrame:
    columns = ["Project", "Activity", "Volunteers", "Duration", "Potential Output", "Requirement"]
    if volunteers <= 0 or hours_per_day <= 0:
        return pd.DataFrame(columns=columns)
    ops = cfg["operations"]
    v = max(1, int(volunteers))
    rows = [
        {"Project": "Project Seva", "Activity": "Food/clothing distribution support", "Volunteers": min(v, 2), "Duration": "Field-defined", "Potential Output": "Distribution support", "Requirement": "Approved supplies and field coordination"},
        {"Project": "Project Bachpanshala", "Activity": "Volunteer-led learning or mentoring support", "Volunteers": min(v, int(ops["learning_volunteers_per_team"])), "Duration": f"{float(ops['learning_session_hours']):.1f} hours", "Potential Output": "Learning/mentoring support", "Requirement": "Venue, learning materials and child-safeguarding process"},
        {"Project": "Project Jeev", "Activity": "Animal feeding/welfare support", "Volunteers": min(v, 2), "Duration": "Field-defined", "Potential Output": "Feeding, rescue-support or welfare activity", "Requirement": "Field team, supplies and animal-care protocol"},
        {"Project": "Project Udaan", "Activity": "Women-focused awareness or skill-support activity", "Volunteers": min(v, 3), "Duration": "Field-defined", "Potential Output": "Awareness/skill-development support", "Requirement": "Defined session scope and local community/SHG coordination"},
        {"Project": "Project Prakriti", "Activity": "Plantation/clean-up/conservation support", "Volunteers": v, "Duration": f"{float(ops['cleaning_volunteer_hours']) / v:.2f} hours for a cleaning workload", "Potential Output": "Environmental field activity", "Requirement": "Site permission and materials/saplings as applicable"},
        {"Project": "Project Vikas", "Activity": "Career, internship or employability support", "Volunteers": min(v, 3), "Duration": "Field-defined", "Potential Output": "Mentoring/career-support activity", "Requirement": "Relevant mentor expertise and defined programme scope"},
    ]
    return pd.DataFrame(rows, columns=columns)

