# Unloan Moneyview

A privacy-first money planner that turns an individual's age, location, income, expenses, debt, protection and milestones into a practical wealth roadmap.

## What it provides

- A financial foundation score based on savings, debt, emergency readiness and insurance.
- A location- and dependent-aware emergency fund target.
- A suggested monthly split across emergency savings, protection, milestones and retirement.
- Inflation-adjusted milestone costs, required monthly investments and funding-gap guidance.
- Age- and risk-aware 5, 10, 20 and retirement-horizon wealth projections.
- A printable plan that does not require signup or persist personal inputs on the server.
- Six-step progressive onboarding with selectable expense, investment, debt and goal cards.
- Contextual estimated benchmarks from an editable `data/benchmarks.json` configuration.
- A score explanation, five-phase roadmap, monthly action plan, milestone dates and AI-style coach insights.

All figures are educational estimates, not regulated financial advice. Returns are illustrative and are not guaranteed. Benchmark ranges are clearly labelled heuristic planning guideposts—not verified population averages.

The Money Planner must not create fear by overemphasizing risks, shortfalls, or emergency gaps. It should give users a positive, practical roadmap based on what they have today and help them build a better financial future step by step.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open `http://localhost:8000`.

## Test

```bash
python -m unittest discover -s tests -v
```

## Deploy to Vercel

The Flask application is exposed through `api/index.py`, with routing configured in `vercel.json`.

```bash
vercel --prod
```

No environment variables are required. Personal inputs are processed only to generate the response and are not persisted by the application.
