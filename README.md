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

## Final UI controls
- Fixed light-only interface; Streamlit theme/menu toolbar is hidden in the app UI.
- InAmigos green action buttons are applied to primary, form-submit and download controls.
- Project Coverage lists all six projects and verified activity areas; activities without grounded cost rules remain volunteer-led/configurable rather than receiving invented costs.
