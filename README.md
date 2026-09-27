# InAmigos Resource Allocation Optimizer

Streamlit decision-support application for programme planning, direct-support calculations, resource constraints and multi-period scheduling.

## Deployment
Upload the contents of this folder to the GitHub repository root and deploy `app.py` with Streamlit Community Cloud. Keep `app.py` and `optimizer_logic.py` from this same package together.

## Included
- InAmigos branding and light theme
- Programme Planning
- Quick Impact calculator
- Project Coverage for all six named projects
- Configurable rates and operating rules
- Budget + volunteer capacity modelling
- Whole-unit intervention logic
- Education cycle: 30 children + matching stationery, using 3 volunteers for a 5-hour session
- Project Seva, Bachpanshala and Prakriti budgeted interventions
- Jeev, Udaan and Vikas represented through field-configured/volunteer-led coverage without invented cost assumptions
- Auto planning horizon, weekly cadence and minimum-gap scheduling
- Multi-period programme calendar
- Direct-support alternatives
- CSV and settings export

## Release QA
- Fixed light-only interface; application surfaces do not depend on the viewer's dark-mode preference.
- Action buttons use a light green InAmigos treatment.
- Programme Calendar and Communication Timeline sort Week numbers numerically.
- Detailed schedule remains numerically ordered by Day.
- Release candidate was checked with deterministic planning cases, randomized regression cases, UI execution harness cases, source guards, and package-content checks.
