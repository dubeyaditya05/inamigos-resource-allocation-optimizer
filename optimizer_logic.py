from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp


@dataclass
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

    if budget <= 0:
        return PlanningHorizon("1 Day", 1)
    if budget <= ops["auto_day_budget_threshold"]:
        return PlanningHorizon("1 Day", 1)
    if budget <= ops["auto_week_budget_threshold"]:
        return PlanningHorizon("1 Week", int(ops["working_days_per_week"]))
    if budget <= ops["auto_month_budget_threshold"]:
        return PlanningHorizon("1 Month", int(ops["working_days_per_week"] * ops["weeks_per_month"]))
    return PlanningHorizon("3 Months", int(ops["working_days_per_week"] * ops["weeks_per_month"] * 3))


def validate_config(cfg: dict) -> None:
    distribution_items = cfg.get("distribution_items", list(cfg["rates"].keys()))
    if not distribution_items or any(item not in cfg["rates"] for item in distribution_items):
        raise ValueError("Distribution items must map to configured rates.")

    required_rates = [
        "Meal for 1 person", "Pencil", "Pen", "Notebook", "Stationery Kit",
        "School Bag", "Book", "Sapling", "Water Bottle", "Hygiene Kit",
        "School Cleaning Materials"
    ]
    for key in required_rates:
        if key not in cfg["rates"]:
            raise ValueError(f"Missing rate: {key}")
        if float(cfg["rates"][key]) < 0:
            raise ValueError(f"Rate cannot be negative: {key}")

    numeric_ops = [
        "hours_per_working_day", "working_days_per_week", "weeks_per_month",
        "learning_session_hours", "learning_volunteers_per_team",
        "learning_teams_per_session", "learning_children_per_session",
        "stationery_recipients_per_education_cycle", "cleaning_volunteer_hours",
        "plantation_volunteer_hours", "plantation_saplings_per_activity",
        "distribution_duration_hours", "distribution_items_per_volunteer_per_hour",
        "max_education_cycles_per_day", "max_cleaning_drives_per_day",
        "max_plantation_activities_per_day", "max_distribution_events_per_day",
        "auto_day_budget_threshold", "auto_week_budget_threshold",
        "auto_month_budget_threshold", "balanced_max_category_budget_share",
        "balanced_min_categories_for_long_horizon", "balanced_long_horizon_days"
    ]
    for key in numeric_ops:
        if float(cfg["operations"][key]) < 0:
            raise ValueError(f"Operating value cannot be negative: {key}")

    if float(cfg["operations"]["hours_per_working_day"]) <= 0:
        raise ValueError("Working hours per day must be positive.")
    if int(cfg["operations"]["working_days_per_week"]) < 1:
        raise ValueError("Working days per week must be at least 1.")
    if float(cfg["operations"]["weeks_per_month"]) <= 0:
        raise ValueError("Weeks per month must be positive.")
    if float(cfg["operations"]["balanced_max_category_budget_share"]) <= 0 or float(cfg["operations"]["balanced_max_category_budget_share"]) > 1:
        raise ValueError("Balanced category budget share must be greater than 0 and at most 1.")

    if int(cfg["operations"]["learning_volunteers_per_team"]) < 1:
        raise ValueError("Learning team must have at least one volunteer.")
    if int(cfg["operations"]["learning_teams_per_session"]) < 1:
        raise ValueError("At least one learning team is required.")
    if int(cfg["operations"]["learning_children_per_session"]) < 1:
        raise ValueError("Learning session capacity must be positive.")
    if int(cfg["operations"]["stationery_recipients_per_education_cycle"]) != int(cfg["operations"]["learning_children_per_session"]):
        raise ValueError("Education cycle and stationery recipient counts must match.")
    if cfg["operations"]["auto_day_budget_threshold"] > cfg["operations"]["auto_week_budget_threshold"]:
        raise ValueError("Auto day threshold must not exceed auto week threshold.")
    if cfg["operations"]["auto_week_budget_threshold"] > cfg["operations"]["auto_month_budget_threshold"]:
        raise ValueError("Auto week threshold must not exceed auto month threshold.")


def build_programme_interventions(cfg: dict, volunteers: int, distribution_item: str) -> pd.DataFrame:
    rates = cfg["rates"]
    ops = cfg["operations"]
    weights = cfg.get("priority_weights", {})

    education_children = int(ops["learning_children_per_session"])
    stationery_children = int(ops["stationery_recipients_per_education_cycle"])
    education_cost = stationery_children * float(rates["Stationery Kit"])
    education_volunteer_hours = (
        int(ops["learning_volunteers_per_team"])
        * int(ops["learning_teams_per_session"])
        * float(ops["learning_session_hours"])
    )

    rows = [
        {
            "intervention": "Education Cycle",
            "category": "Education",
            "unit_description": f"1 learning session for {education_children} children + stationery support for the same {stationery_children} children",
            "cost_per_unit": education_cost,
            "volunteer_hours_per_unit": education_volunteer_hours,
            "beneficiaries_per_unit": education_children,
            "priority_weight": float(weights.get("Education Cycle", 1.0)),
            "max_per_day": int(ops["max_education_cycles_per_day"]),
            "kind": "programme",
            "split_allowed": False,
        },
        {
            "intervention": "School Cleaning Drive",
            "category": "Community",
            "unit_description": "1 cleaning drive using the configured material budget",
            "cost_per_unit": float(rates["School Cleaning Materials"]),
            "volunteer_hours_per_unit": float(ops["cleaning_volunteer_hours"]),
            "beneficiaries_per_unit": 0,
            "priority_weight": float(weights.get("School Cleaning Drive", 1.0)),
            "max_per_day": int(ops["max_cleaning_drives_per_day"]),
            "kind": "activity",
            "split_allowed": True,
        },
        {
            "intervention": "Plantation Activity",
            "category": "Environment",
            "unit_description": f"1 plantation activity with {int(ops['plantation_saplings_per_activity'])} saplings",
            "cost_per_unit": float(rates["Sapling"]) * int(ops["plantation_saplings_per_activity"]),
            "volunteer_hours_per_unit": float(ops["plantation_volunteer_hours"]),
            "beneficiaries_per_unit": 0,
            "priority_weight": float(weights.get("Plantation Activity", 1.0)),
            "max_per_day": int(ops["max_plantation_activities_per_day"]),
            "kind": "activity",
            "split_allowed": True,
        },
    ]

    if volunteers > 0:
        items_per_event = math.floor(
            volunteers
            * float(ops["distribution_duration_hours"])
            * float(ops["distribution_items_per_volunteer_per_hour"])
        )
        if items_per_event > 0:
            rows.append(
                {
                    "intervention": "Distribution Event",
                    "category": "Community",
                    "unit_description": f"1 distribution event of {items_per_event} × {distribution_item}",
                    "cost_per_unit": items_per_event * float(rates[distribution_item]),
                    "volunteer_hours_per_unit": volunteers * float(ops["distribution_duration_hours"]),
                    "beneficiaries_per_unit": items_per_event,
                    "priority_weight": float(weights.get("Distribution Event", 1.0)),
                    "max_per_day": int(ops["max_distribution_events_per_day"]),
                    "kind": "distribution",
                    "split_allowed": False,
                }
            )

    df = pd.DataFrame(rows)
    df.attrs["balanced_max_category_budget_share"] = float(ops.get("balanced_max_category_budget_share", 0.55))
    df.attrs["balanced_long_horizon_days"] = int(ops.get("balanced_long_horizon_days", 20))
    df.attrs["balanced_min_categories_for_long_horizon"] = int(ops.get("balanced_min_categories_for_long_horizon", 3))
    return df


def _category_bonus(df: pd.DataFrame, mode: str) -> np.ndarray:
    if mode == "Education focus":
        return np.where(df["category"].str.contains("Education", regex=False), 2.5, 1.0)
    if mode == "Community support focus":
        return np.where(df["category"].eq("Community"), 2.5, 1.0)
    if mode == "Environment focus":
        return np.where(df["category"].eq("Environment"), 2.5, 1.0)
    if mode == "Balanced programme":
        return df["priority_weight"].to_numpy(float)
    return np.ones(len(df), dtype=float)


def optimize_programme(
    df: pd.DataFrame,
    budget: float,
    volunteers: int,
    hours_per_day: float,
    horizon_days: int,
    objective: str,
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    if df.empty:
        return None, "No interventions are available."

    total_volunteer_capacity = volunteers * hours_per_day * horizon_days
    n = len(df)

    # Integer x_i = intervention units. Binary y_i = activated intervention.
    c = np.zeros(2 * n, dtype=float)
    bonus = _category_bonus(df, objective)

    if objective == "Maximum reach":
        c[:n] = -df["beneficiaries_per_unit"].to_numpy(float)
    elif objective in {"Education focus", "Community support focus", "Environment focus"}:
        target = {
            "Education focus": "Education",
            "Community support focus": "Community",
            "Environment focus": "Environment",
        }[objective]
        max_possible_reach = float((df["beneficiaries_per_unit"] * df["max_per_day"] * horizon_days).sum())
        focus_weight = max_possible_reach + 1.0
        focused_units = (df["category"].eq(target).to_numpy(float) * df["priority_weight"].to_numpy(float))
        c[:n] = -(focused_units * focus_weight + df["beneficiaries_per_unit"].to_numpy(float))
    elif objective == "Maximum programme priority":
        c[:n] = -(df["beneficiaries_per_unit"].to_numpy(float) * bonus)
    else:  # Balanced programme
        c[:n] = -(df["beneficiaries_per_unit"].to_numpy(float) * bonus)
        c[n:] = -0.5  # small reward for activating more intervention types

    rows = []
    lower = []
    upper = []

    cost_row = np.zeros(2 * n, dtype=float)
    cost_row[:n] = df["cost_per_unit"].to_numpy(float)
    rows.append(cost_row); lower.append(-np.inf); upper.append(budget)

    hours_row = np.zeros(2 * n, dtype=float)
    hours_row[:n] = df["volunteer_hours_per_unit"].to_numpy(float)
    rows.append(hours_row); lower.append(-np.inf); upper.append(total_volunteer_capacity)

    # Link x_i <= max_units(horizon)*y_i. Max is the operational daily cap × working days.
    for i in range(n):
        configured_daily_cap = int(df.loc[i, "max_per_day"])
        max_units = configured_daily_cap * horizon_days
        if not bool(df.loc[i, "split_allowed"]):
            daily_capacity = volunteers * hours_per_day
            unit_hours = float(df.loc[i, "volunteer_hours_per_unit"])
            feasible_per_day = int(daily_capacity // unit_hours) if unit_hours > 0 else configured_daily_cap
            max_units = min(max_units, feasible_per_day * horizon_days)
        row = np.zeros(2 * n, dtype=float)
        row[i] = 1
        row[n + i] = -max_units
        rows.append(row); lower.append(-np.inf); upper.append(0)
        # An activated intervention must contain at least one complete unit.
        row2 = np.zeros(2 * n, dtype=float)
        row2[i] = 1
        row2[n + i] = -1
        rows.append(row2); lower.append(0); upper.append(np.inf)

    # Balanced mode: limit concentration so a large budget is not swallowed by one category.
    if objective == "Balanced programme":
        categories = list(dict.fromkeys(df["category"].tolist()))
        max_share = float(df.attrs.get("balanced_max_category_budget_share", 0.55))
        for category in categories:
            row = np.zeros(2 * n, dtype=float)
            max_single_unit = 0.0
            for i, cat in enumerate(df["category"]):
                if cat == category:
                    row[i] = float(df.loc[i, "cost_per_unit"])
                    max_single_unit = max(max_single_unit, float(df.loc[i, "cost_per_unit"]))
            # Never make a complete intervention impossible merely because it costs more than the
            # concentration target. The cap becomes binding only once the budget can support it.
            category_cap = max(budget * max_share, max_single_unit)
            rows.append(row); lower.append(-np.inf); upper.append(category_cap)

        # For larger planning horizons, require at least one complete intervention in each
        # major category when the portfolio contains enough categories. This prevents a
        # large budget from becoming an oversized single-cause plan.
        long_horizon = int(df.attrs.get("balanced_long_horizon_days", 20))
        min_categories = int(df.attrs.get("balanced_min_categories_for_long_horizon", 3))
        if horizon_days >= long_horizon and len(categories) >= min_categories:
            for category in categories:
                row = np.zeros(2 * n, dtype=float)
                for i, cat in enumerate(df["category"]):
                    if cat == category:
                        row[n + i] = 1
                rows.append(row); lower.append(1); upper.append(np.inf)

    A = np.vstack(rows)
    constraints = LinearConstraint(A, np.array(lower), np.array(upper))
    bounds_lo = np.zeros(2 * n, dtype=float)
    bounds_hi = np.r_[
        df["max_per_day"].to_numpy(float) * horizon_days,
        np.ones(n, dtype=float),
    ]

    res = milp(
        c=c,
        integrality=np.ones(2 * n),
        bounds=Bounds(bounds_lo, bounds_hi),
        constraints=constraints,
        options={"time_limit": 8},
    )

    if not res.success:
        return None, str(res.message)

    out = df.copy()
    out["units"] = np.rint(res.x[:n]).astype(int)
    out["allocated_budget"] = out["units"] * out["cost_per_unit"]
    out["volunteer_hours"] = out["units"] * out["volunteer_hours_per_unit"]
    out["planned_beneficiaries"] = out["units"] * out["beneficiaries_per_unit"]

    # Repair rare integer-packing gaps between the aggregate MILP and the day-by-day schedule.
    for _ in range(int(out["units"].sum()) + 1):
        active = out[out["units"] > 0].copy()
        schedule = schedule_interventions(active, volunteers, hours_per_day, PlanningHorizon("", horizon_days))
        placed = schedule.groupby("Intervention")["Units Started"].sum().to_dict() if not schedule.empty else {}
        required = active.set_index("intervention")["units"].astype(int).to_dict()
        if placed == required:
            return out, None

        candidates = []
        for i in out.index[out["units"] > 0]:
            category = out.loc[i, "category"]
            if objective == "Balanced programme" and horizon_days >= int(df.attrs.get("balanced_long_horizon_days", 20)):
                if out.loc[out["category"] == category, "units"].sum() <= 1:
                    continue

            value_loss = float(df.loc[i, "beneficiaries_per_unit"])
            if objective == "Maximum programme priority":
                value_loss *= float(df.loc[i, "priority_weight"])
            elif objective in {"Education focus", "Community support focus", "Environment focus"}:
                target = {"Education focus": "Education", "Community support focus": "Community", "Environment focus": "Environment"}[objective]
                if category == target:
                    value_loss += 1_000_000.0
            elif objective == "Balanced programme":
                value_loss += float(df.loc[i, "priority_weight"]) * 0.1
            candidates.append((value_loss, i))

        if not candidates:
            return None, "The selected plan cannot be fully scheduled within the configured working-day limits."

        _, i = min(candidates, key=lambda x: x[0])
        out.loc[i, "units"] -= 1
        out["allocated_budget"] = out["units"] * out["cost_per_unit"]
        out["volunteer_hours"] = out["units"] * out["volunteer_hours_per_unit"]
        out["planned_beneficiaries"] = out["units"] * out["beneficiaries_per_unit"]

    return None, "The selected plan could not be scheduled."


def schedule_interventions(
    allocation: pd.DataFrame,
    volunteers: int,
    hours_per_day: float,
    horizon: PlanningHorizon,
) -> pd.DataFrame:
    columns = ["Day", "Intervention", "Units Started", "Volunteer Hours", "Allocated Budget", "Planned Capacity"]
    if allocation is None or allocation.empty or volunteers <= 0 or hours_per_day <= 0:
        return pd.DataFrame(columns=columns)

    day_capacity = volunteers * hours_per_day
    day_remaining = [day_capacity] * horizon.days
    day_started = [dict() for _ in range(horizon.days)]
    rows = []
    meta = allocation.set_index("intervention")
    remaining = {r: int(meta.loc[r, "units"]) for r in meta.index if int(meta.loc[r, "units"]) > 0}

    # Fixed-duration sessions should be placed first; workload activities may span days.
    order = sorted(
        remaining,
        key=lambda name: (bool(meta.loc[name, "split_allowed"]), -float(meta.loc[name, "volunteer_hours_per_unit"]))
    )

    for intervention in order:
        unit_hours = float(meta.loc[intervention, "volunteer_hours_per_unit"])
        unit_budget = float(meta.loc[intervention, "allocated_budget"] / meta.loc[intervention, "units"])
        unit_capacity = float(meta.loc[intervention, "planned_beneficiaries"] / meta.loc[intervention, "units"])
        cap_per_day = int(meta.loc[intervention, "max_per_day"])
        split_allowed = bool(meta.loc[intervention, "split_allowed"])

        for _ in range(remaining[intervention]):
            if not split_allowed:
                placed = False
                for day_idx, available in enumerate(day_remaining):
                    if available + 1e-9 < unit_hours or cap_per_day <= 0:
                        continue
                    if day_started[day_idx].get(intervention, 0) >= cap_per_day:
                        continue
                    day_remaining[day_idx] -= unit_hours
                    day_started[day_idx][intervention] = day_started[day_idx].get(intervention, 0) + 1
                    rows.append({
                        "Day": f"Day {day_idx + 1}",
                        "Intervention": intervention,
                        "Units Started": 1,
                        "Volunteer Hours": unit_hours,
                        "Allocated Budget": unit_budget,
                        "Planned Capacity": unit_capacity,
                    })
                    placed = True
                    break
                if not placed:
                    return pd.DataFrame(columns=columns)
                continue

            work_left = unit_hours
            started = False
            for day_idx, available in enumerate(day_remaining):
                if work_left <= 1e-9:
                    break
                if available <= 1e-9 or cap_per_day <= 0:
                    continue
                if day_started[day_idx].get(intervention, 0) >= cap_per_day and not started:
                    continue
                used = min(work_left, available)
                day_remaining[day_idx] -= used
                if not started:
                    day_started[day_idx][intervention] = day_started[day_idx].get(intervention, 0) + 1
                rows.append({
                    "Day": f"Day {day_idx + 1}",
                    "Intervention": intervention,
                    "Units Started": 1 if not started else 0,
                    "Volunteer Hours": used,
                    "Allocated Budget": unit_budget if not started else 0.0,
                    "Planned Capacity": unit_capacity if not started else 0.0,
                })
                started = True
                work_left -= used
            if work_left > 1e-9:
                return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows, columns=columns)

def quick_impact(rates: dict, item: str, budget: float) -> tuple[int, float]:
    unit = float(rates[item])
    if unit <= 0:
        return 0, float(budget)
    units = int(math.floor(max(0.0, budget) / unit))
    return units, max(0.0, float(budget) - units * unit)


def volunteer_only_options(cfg: dict, volunteers: int, hours_per_day: float) -> pd.DataFrame:
    ops = cfg["operations"]
    if volunteers <= 0 or hours_per_day <= 0:
        return pd.DataFrame(columns=["Activity", "Volunteers Needed", "Duration", "Capacity", "Notes"])

    teams = volunteers // int(ops["learning_volunteers_per_team"])
    rows = []
    if teams >= int(ops["learning_teams_per_session"]):
        rows.append({
            "Activity": "Volunteer-led learning session",
            "Volunteers Needed": int(ops["learning_volunteers_per_team"]) * int(ops["learning_teams_per_session"]),
            "Duration": f"{ops['learning_session_hours']:.1f} hours",
            "Capacity": int(ops["learning_children_per_session"]),
            "Notes": "Uses existing venue/materials; no programme purchase cost included.",
        })
    rows.append({
        "Activity": "Community awareness / survey activity",
        "Volunteers Needed": 2,
        "Duration": "Flexible",
        "Capacity": "Field-defined",
        "Notes": "Plan only after local permission and activity scope are confirmed.",
    })
    rows.append({
        "Activity": "Volunteer mentoring / reading support",
        "Volunteers Needed": 1,
        "Duration": "Flexible",
        "Capacity": "Field-defined",
        "Notes": "No material purchase included; use existing resources.",
    })
    return pd.DataFrame(rows)
