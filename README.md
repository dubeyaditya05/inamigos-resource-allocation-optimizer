# InAmigos Foundation - Resource Allocation Optimizer

A decision-support dashboard for planning meaningful NGO interventions under budget, volunteer-capacity and working-time constraints.

## Deployment

Upload the files in this folder to a GitHub repository and deploy `app.py` using Streamlit Community Cloud.

No database or cloud-storage service is required for the current deployment model.

## Included files

- `app.py` - dashboard interface
- `optimizer_logic.py` - planning and optimisation engine
- `config.json` - editable rates and operating rules
- `inamigos_logo.png` - InAmigos branding
- `requirements.txt` - Python dependencies
- `README.md` - deployment notes

## Local run

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Core planning logic

The application uses complete intervention units and activity-specific operating rules.

- Education Cycle: 30 children with matching stationery support for the same 30 children; 5-hour learning session; 3 teams of 3 volunteers; 45 volunteer-hours per cycle.
- School Cleaning Drive: 20 volunteer-hours; additional volunteers reduce elapsed completion time without reducing the total workload.
- Plantation Activity: 10 volunteer-hours and 10 saplings per activity; additional volunteers reduce elapsed completion time.
- Distribution Event: 1.5 hours; capacity is volunteers x 20 items per volunteer per hour; quantities are whole items.
- Quick Impact: direct calculations for configured support items such as meals, pencils, notebooks and kits.
- Large budgets: the planning horizon can expand from a day to a week, month or three months, with working-day scheduling and longer-period summaries.
- Balanced planning: category concentration and longer-horizon category coverage rules prevent a large allocation from collapsing into one activity type.

## Settings

Rates, team sizes, activity duration, working days, distribution capacity, daily activity limits and planning thresholds are editable in the Settings tab and can be exported/imported as JSON.

The configured values should be aligned with current approved programme and procurement data before operational use.
