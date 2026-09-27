# InAmigos Resource Allocation Optimizer

A working web-based resource planning and programme scheduling application built for **InAmigos Foundation**. The optimizer helps convert an organization's available **budget, volunteers and working time** into a structured programme plan.

**Live Application:** https://inamigos-resource-allocation-optimizer.streamlit.app/

## Project Overview

I built this project as a practical decision-support tool for NGO programme planning. Instead of treating a budget as a simple spending calculator, the application models programme activities as complete intervention units and considers the resources required to deliver them.

The system takes inputs such as available budget, volunteer capacity, working hours, planning horizon and programme objective. It then uses the configured programme rules to determine which interventions can be included, how many complete units can be supported, and how those activities can be distributed across the planning period.

The project was developed as a **working application** and is designed so that real programme data can be entered through the interface and through the configuration settings.

## How I Built It

### 1. Converted programme requirements into planning rules

I first converted the programme requirements into measurable variables such as:

- Cost per intervention unit
- Volunteer-hours required
- Required volunteer team size
- Activity capacity
- Maximum activities per day and week
- Minimum gap between repeated activities
- Planning-horizon rules

This made it possible to represent programme activities mathematically rather than treating them as simple text descriptions.

### 2. Created configurable intervention models

The main budgeted interventions were defined as structured planning units:

| Intervention | Project | Current planning model |
|---|---|---|
| Education Cycle | Project Bachpanshala | 30 children, 3 volunteers, 5-hour session and matching stationery |
| School Cleaning Drive | Project Prakriti | Cleaning activity with configured material cost and volunteer workload |
| Plantation Activity | Project Prakriti | 10 saplings with configured sapling cost and volunteer workload |
| Distribution Event | Project Seva | Quantity calculated from volunteers, event duration and distribution rate |

The application also includes all six InAmigos projects in its project coverage model:

- Project Seva
- Project Bachpanshala
- Project Jeev
- Project Udaan
- Project Prakriti
- Project Vikas

Jeev, Udaan and Vikas are represented in the application without inventing financial values where a field-specific cost model has not been configured.

### 3. Built the optimization engine

The planning engine uses **mixed-integer linear programming (MILP)** through SciPy's optimization tools.

The optimizer evaluates possible complete intervention units while respecting constraints such as:

- Available budget
- Volunteer capacity
- Working hours
- Intervention cadence
- Minimum gaps
- Minimum volunteer requirements
- Planning horizon

The model also supports different planning objectives so that the allocation can be oriented toward maximum reach, balance, education, community support or environment.

### 4. Added a scheduling engine

After the allocation is calculated, a separate scheduling layer turns the selected intervention quantities into a day-by-day programme calendar.

The scheduler considers the actual volunteer capacity available on each working day and applies the configured cadence and spacing rules.

The calendar shows the complete planning horizon. Even when no intervention is scheduled on a particular day, that day remains visible as **No activity planned** instead of disappearing from the calendar.

### 5. Built the application interface

The user interface was developed in **Streamlit** and organized into practical modules:

- Programme Planning
- Quick Impact
- Project Coverage
- Settings
- Programme Communication

The interface is designed around entering resources, generating a plan, reviewing the resulting programme and exporting the information for further use.

### 6. Added configurable real-world data

Programme rates and operating rules are stored separately from the main application logic. This makes it possible to update the system when actual costs or operational conditions change.

Examples of configurable rates include:

- Meal for 1 person
- Pencil
- Pen
- Notebook
- Stationery Kit
- School Bag
- Book
- Sapling
- Water Bottle
- Hygiene Kit
- School Cleaning Materials

The Settings section allows these values and operational rules to be changed for the current planning session. Settings can also be downloaded and loaded again.

## Main Features

### Programme Planning

The main planner accepts:

- Available budget
- Number of volunteers
- Working hours per day
- Planning horizon
- Planning objective
- Distribution item

It then generates a recommended intervention portfolio with budget, volunteer-hour and planned-capacity information.

### Resource Optimization

The optimizer selects complete intervention units instead of creating partial activities simply to spend the remaining budget.

This makes the output easier to interpret as a real programme plan because each selected unit corresponds to a defined intervention model.

### Automatic Planning Horizon

The application can choose a planning horizon automatically according to the available budget. It also supports manual selection of:

- 1 Day
- 1 Week
- 1 Month
- 3 Months

### Programme Objectives

Available objectives are:

- Maximum reach
- Balanced programme
- Education focus
- Community support focus
- Environment focus

### Programme Calendar

The optimizer creates a chronological schedule containing:

- Day
- Week
- Intervention
- Units started
- Volunteer hours
- Elapsed hours
- Allocated budget
- Planned capacity

The calendar is ordered numerically and includes every working day in the selected planning horizon.

### Communication Timeline

The generated programme is also converted into a week-by-week communication timeline. This connects programme delivery with planned communication and documentation activities.

### Quick Impact Calculator

The Quick Impact module calculates how many complete units of a selected item can be supported by a specified budget using the current configured rate.

For example, with a configured Stationery Kit rate of ₹100, a budget of ₹1,000 corresponds to 10 complete kits.

### Project Coverage

The Project Coverage section connects the optimizer with the wider InAmigos programme structure and shows the six projects represented by the application.

### Volunteer-Only Planning

When the available budget is zero, the application can still surface volunteer-led options instead of assigning unsupported material costs to activities.

### Programme Communication

For the generated intervention plan, the application produces:

- Social media caption options
- Programme-specific communication text
- Professional / CSR update text

These outputs are based on the actual allocation scenario generated by the optimizer.

### Export and Configuration

The application supports:

- Allocation CSV export
- Settings download
- Settings upload
- Configurable rates
- Configurable operating rules

## Current Planning Logic

### Education Cycle

The current model uses:

- 30 children per learning cycle
- 3 volunteers
- 5-hour session
- 15 volunteer-hours per cycle
- 30 matching stationery recipients
- ₹100 configured Stationery Kit rate

This gives a default stationery component of:

**30 × ₹100 = ₹3,000 per Education Cycle**

### School Cleaning Drive

The current model uses:

- ₹250 configured School Cleaning Materials rate
- 20 volunteer-hours per cleaning drive

The elapsed time can decrease when more volunteers work in parallel because the activity is represented as a fixed volunteer workload.

### Plantation Activity

The current model uses:

- 10 saplings per activity
- ₹30 configured cost per sapling
- 10 volunteer-hours per activity

The current configured sapling material cost is therefore:

**10 × ₹30 = ₹300 per Plantation Activity**

### Distribution Event

Distribution capacity is calculated from:

**Volunteers × Event Duration × Items per Volunteer per Hour**

The current baseline configuration uses:

- 1.5-hour event duration
- 20 items per volunteer per hour

The selected distribution item determines the associated material cost.

## Technology Stack

- **Python** — core application and planning logic
- **Streamlit** — web interface
- **Pandas** — structured programme data and tables
- **NumPy** — numerical processing
- **SciPy** — mixed-integer optimization
- **JSON** — editable application configuration
- **GitHub** — source repository and deployment source
- **Streamlit Community Cloud** — live web deployment

## Project Structure

```text
InAmigos Resource Allocation Optimizer/
│
├── app.py
│   └── Streamlit interface and application workflow
│
├── optimizer_logic.py
│   └── Intervention models, optimization and scheduling logic
│
├── config.json
│   └── Rates, operating rules, planning thresholds and distribution items
│
├── requirements.txt
│   └── Python dependencies
│
├── inamigos_logo.png
│   └── Application branding
│
├── .streamlit/
│   └── Streamlit UI configuration
│
└── README.md
    └── Project documentation
```

## Running the Project Locally

Install the dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app.py
```

The application will open in the browser through the local Streamlit server.

## Deployment

The application is deployed as a Streamlit web application using the project files in the repository.

The live application is available at:

**https://inamigos-resource-allocation-optimizer.streamlit.app/**

For deployment, the core application files should remain together so that `app.py`, `optimizer_logic.py` and `config.json` use the same version of the project.

## Using Real Programme Data

The optimizer is structured so that real programme values can replace the current baseline configuration.

For an actual planning cycle, the intended workflow is:

1. Enter the current available budget.
2. Enter the current volunteer capacity.
3. Enter realistic working hours per day.
4. Update rates in Settings when procurement or programme costs change.
5. Adjust operating rules when field delivery conditions change.
6. Select the required planning objective and horizon.
7. Run the allocation.
8. Review the recommended programme and calendar.
9. Export the allocation and use the generated outputs for operational planning and communication.

## Why the Project Was Built

The goal of the project is to bridge the gap between **available resources** and **practical programme execution**.

Instead of asking only:

> "How much money do we have?"

The optimizer is designed to answer a broader planning question:

> "Given our current budget, volunteer capacity and operating constraints, what complete programme activities can we realistically organize, and how can they be scheduled across the planning period?"

That makes the application useful as a planning layer between programme requirements and implementation.

## Author

Built as a practical AI/data-driven project for **InAmigos Foundation**, combining programme modelling, constrained optimization, scheduling and an interactive web application.
