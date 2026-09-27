Final release

# InAmigos Resource Allocation Optimizer

Streamlit decision-support application for programme planning, direct-support calculations, resource constraints and multi-period scheduling.

## Deployment

Upload the contents of this folder to the GitHub repository root and deploy `app.py` with Streamlit Community Cloud.

## Local run

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Included

- InAmigos branding
- English-only interface
- Programme planner
- Quick Impact calculator
- Configurable rates and operating rules
- Budget + volunteer capacity modelling
- Whole-unit intervention logic
- Education cycle: 30 children with matching stationery support
- Activity-specific volunteer logic
- Distribution capacity based on volunteer count and configured rate
- Auto planning horizon
- Weekly cadence and minimum-gap scheduling
- Large-budget multi-period programme calendar
- Direct-support alternatives when the main programme is constrained
- Scenario-derived social and professional/CSR content drafts
- CSV and settings export
