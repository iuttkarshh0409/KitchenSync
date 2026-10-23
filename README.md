# KitchenSync

**TechSprint · Team 18**  
Dual-brand kitchen coordination for **Momobuzz** (momos) and **Woksum** (wok dishes).

KitchenSync provides a shared ordering flow for both brands, schedules work across steamer and wok stations, checks combo contribution economics, and gives operators a branch review dashboard. This is a local, demonstrable MVP built with React, Vite, TypeScript, FastAPI, and SQLite.

## Contents

- [What the demo does](#what-the-demo-does)
- [Requirements](#requirements)
- [Run locally](#run-locally)
- [Acceptance demo](#acceptance-demo)
- [Scheduling and business rules](#scheduling-and-business-rules)
- [Configuration and data](#configuration-and-data)
- [API overview](#api-overview)
- [Tests and production build](#tests-and-production-build)
- [Project layout](#project-layout)
- [Push to GitHub](#push-to-github)
- [Known limitations](#known-limitations)

## What the demo does

- **Overview:** operational snapshot and links into ordering and kitchen workflows.
- **Order food:** one cart can contain Momobuzz and Woksum items. Estimates refresh from station workload; the preview shows planned starts/finishes, synchronization variance, and a backend-calculated profitability report.
- **Student combo:** a dedicated both-brand builder using existing menu items. It applies the same price and profitability rules, with no unconfigured student discount.
- **Kitchen:** separate steamer and wok queues with task status, quantities, order identities, batch membership, planned times, and start/complete actions.
- **Orders & batches:** inspect persisted orders and combine eligible identical queued dishes while preserving each source order item.
- **Text parser:** parse inputs such as `2 veg momo 1 chicken hakka noodles fast`; aliases, quantities, and priority notes are supported. Unknown or ambiguous menu references require correction.
- **Analytics:** calculate order/task metrics from persisted data, with date filtering and synthetic demo records identified.
- **Branches:** compare order volume, average ticket, configured capacity and supported operational measures. Bhanwarkuan remains open. Jabalpur is marked **Review / Consolidation Decision Required** for human review; the application does not close or consolidate outlets.
- **Cost settings:** configure menu selling prices, ingredient estimates, delivery cost, platform commission, other order-level cost, and optional minimum contribution profit/margin policy.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer and npm
- Windows PowerShell examples are used below; equivalent Python/npm commands work on macOS and Linux

## Run locally

From the repository root, create and activate a virtual environment and install backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the API in that terminal:

```powershell
python -m uvicorn backend.main:app --reload
```

In a second terminal, install frontend dependencies and run Vite:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). FastAPI's interactive API docs are at [http://localhost:8000/docs](http://localhost:8000/docs). Vite proxies `/api` requests to `http://127.0.0.1:8000`.

On first API startup, SQLite tables and additive schema migrations are initialized and demo menu, branch, and `DEMO-*` order data are seeded. The SQLite database is local runtime state and is excluded from Git.

> If PowerShell blocks activation scripts, run `python -m pip install -r requirements.txt` using the virtual environment's Python executable directly: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. Use `.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload` to start the API without activation.

## Acceptance demo

1. Open **Order food** or **Student combo** and select a Momobuzz steamed momo item plus a Woksum wok dish.
2. Review the cooking durations and schedule. With idle stations and the sample 10-minute steamer / 3-minute wok durations, the steamer starts first and the wok starts seven minutes later; both target the same finish time.
3. Inspect the expected finish-time variance and the two-minute synchronization target. Existing task workload changes the estimate; infeasible schedules are flagged with predicted variance.
4. Review revenue, ingredient costs, delivery, platform fee, other costs, estimated contribution profit and margin. Missing cost configuration is explicitly marked incomplete; a configured threshold violation blocks submission.
5. Try a Momobuzz selling price of ₹68.99 in **Cost settings** to see the backend reject it. ₹69.00 is the minimum configured per-unit price and discounts are not currently offered.
6. Submit an approved order and open **Kitchen** to start and complete its tasks. Use **Orders & batches** to optimize eligible identical queued momo tasks while retaining each order ID.
7. Open **Branches** to review order evidence and set a manual review status. Jabalpur remains open and requires a human consolidation decision; Bhanwarkuan remains open.
8. Open **Text parser** and enter `2 veg momo 1 chicken hakka noodles fast` to preview parsed menu identities, quantities, brands, stations, and priority.

## Scheduling and business rules

### Finish-time synchronization

The scheduler treats each station as a single-capacity queue. For a new order with one item at each idle station, planned finish time is aligned by choosing a common target no earlier than the slower item can finish. Thus, for a 10-minute steamer item and 3-minute wok item, the steamer starts at T+0 and the wok starts at T+7; both finish at T+10.

The scheduler accounts for queued/active station intervals and sequential tasks at the same station. It reports each planned start/finish and the spread between item finish times. Synchronization succeeds only when the predicted spread is at most two minutes. When station conflicts make that impossible, the schedule reports the deviation instead of claiming success.

### Cross-order batching

Only identical menu items assigned to the same station are eligible. The default arrival window is three minutes and can be configured. Eligible tasks must still be queued; active/completed tasks are not merged. Batch membership retains the original order-item and customer order relationships. The MVP uses a conservative wait policy and does not hold a customer's scheduled work solely to grow a batch.

### Pricing and profitability

All currency calculations use Python `Decimal` and are rounded to two decimal places. For an order:

```text
Item revenue = Σ(configured selling price per unit × quantity)
Platform fee = item revenue × configured commission percentage
Estimated cost = ingredient costs + order-level delivery cost + platform fee + other configured costs
Contribution profit = item revenue − estimated cost
Contribution margin % = (contribution profit ÷ item revenue) × 100, when revenue > 0
```

Delivery and other configured order costs are counted once per order, not once per line. The API ignores browser-supplied prices and totals and recalculates from persisted menu/configuration data. The current app does not configure discounts; non-zero submitted discounts are rejected. A Momobuzz item's effective unit selling price must be at least ₹69.00, enforced on both menu configuration and order submission.

Profitability policy thresholds are configurable. No official minimum profit or margin was supplied, so the seeded policy is an illustrative demo setting, not organiser policy. Missing ingredient, delivery, or commission cost configuration returns an `incomplete_costs` warning and blocks a false profitable/approved result.

### Branch evidence

Branch order volume, ticket size, capacity utilization, revenue and other available measures are calculated from stored orders. Seeded `DEMO-*` tickets, ingredient costs, fee values, and outlet capacities are synthetic and are called out in the UI. The organiser's crisis figures (walk-in orders −45%, ticket ₹180 → ₹125, competitor momo price ₹59) are displayed as scenario inputs, not used to invent outlet results. Jabalpur's review status is decision support only; branch closure or consolidation remains a human decision.

## Configuration and data

The main application database is `backend/kitchensync.db`. Delete it only when you intentionally want to reset local demo data; it is ignored by Git. Database startup adds missing columns/tables safely and preserves legacy records.

The **Cost settings** UI and API allow configuration of:

- Menu item selling price and ingredient cost per unit.
- Delivery cost per order.
- Platform commission percentage.
- Other configured order cost.
- Optional minimum contribution profit and contribution margin percentage.
- Branch configured daily capacity and manual review status (where exposed by the branch UI/API).

Configuration is stored in SQLite. Sample prices, costs, commission, threshold, and capacities are for demonstration only; replace them with verified business values before using results for a real operating decision.

## API overview

The backend is served under `/api` (interactive schema at `/docs`). Core routes include:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/menu` | Menu items, brands, stations and configured pricing |
| `GET` | `/api/stations` | Station queues, workload and tasks |
| `GET` | `/api/orders` | Persisted orders |
| `POST` | `/api/orders/preview` | Validate and preview server-calculated schedule and profitability |
| `POST` | `/api/orders` | Validate and create an order |
| `GET` | `/api/orders/{order_id}` | Read an order and its items/tasks |
| `POST` | `/api/orders/{order_id}/schedule` | Recompute an order schedule |
| `POST` | `/api/tasks/{task_id}/start` | Start a queued kitchen task |
| `POST` | `/api/tasks/{task_id}/complete` | Complete an active kitchen task |
| `POST` | `/api/orders/parse` | Parse informal text into validated structured items |
| `GET` | `/api/batches` | List persisted cross-order batches |
| `POST` | `/api/batches/optimize` | Find and form eligible queued batches |
| `GET` | `/api/config` | Read fee and profitability policy configuration |
| `PUT` | `/api/config` | Update fee and profitability configuration |
| `PUT` | `/api/menu/cost` | Configure item selling/ingredient costs; enforces the momo floor |
| `GET` | `/api/branches` | Branch evidence, with optional `from_date` / `to_date` filters |
| `PUT` | `/api/branches/{id}/review` | Set manual review state; does not close an outlet |
| `GET` | `/api/analytics/summary` | Calculate order and station analytics |

Exact request and response models are available from FastAPI's OpenAPI docs at `/docs`.

## Tests and production build

Run backend tests from the project root:

```powershell
python -m pytest backend -q
```

Build the frontend:

```powershell
cd frontend
npm run build
```

The automated backend suite covers scheduling alignment and conflicts, queued workload, parser validation, batching identity, price floor and discount rejection, profitability policy and incomplete-cost behavior, server-side price resolution, schema initialization, and branch safeguards. The Vite configuration uses its built-in TypeScript/JSX transform; no Babel React plugin or SWC plugin is required.

## Project layout

```text
KitchenSync/
├── backend/
│   ├── main.py            # FastAPI routes, SQLite-backed persistence
│   ├── database.py        # Schema initialization, migrations and demo seed
│   ├── scheduler.py      # Station queue and synchronization logic
│   ├── batching.py       # Cross-order batch eligibility and formation
│   ├── profitability.py  # Decimal-safe price and contribution policy
│   ├── parser.py         # Alias-based text order parser
│   ├── analytics.py      # Data-derived analytics
│   └── test_*.py          # Backend automated tests
├── frontend/
│   ├── src/main.tsx       # Application views and API-connected workflows
│   ├── package.json
│   └── vite.config.ts
├── requirements.txt
├── .gitignore
└── README.md
```

## Push to GitHub

The target repository is `https://github.com/iuttkarshh0409/KitchenSync`. From the project root, inspect the current Git state first:

```powershell
git status
git remote -v
```

If this directory is not yet a Git repository, initialize it and make the initial commit:

```powershell
git init
git add .
git status
git commit -m "Build KitchenSync crisis adaptation MVP"
```

Configure the requested GitHub repository as `origin`. If `origin` does not exist:

```powershell
git remote add origin https://github.com/iuttkarshh0409/KitchenSync.git
```

If `origin` already exists but points elsewhere, update it:

```powershell
git remote set-url origin https://github.com/iuttkarshh0409/KitchenSync.git
```

Then push the current branch. For a new repository with no existing history, the following creates/uses `main`:

```powershell
git branch -M main
git push -u origin main
```

If the GitHub repository already has commits you need to preserve, first fetch and inspect its history (`git fetch origin`, `git log --oneline --graph --all`), then reconcile the histories before pushing. GitHub authentication may prompt through the configured credential manager; do not put a password or token in the remote URL.

## Known limitations

- Kitchen updates use lightweight polling; there is no event stream or WebSocket.
- Authentication, POS integration, voice transcription, and delivery-driver integration are not included.
- Demo costs and branch capacities need verified business configuration before decisions are based on them.
- Branch dashboard supports evidence review only; it cannot execute a closure or consolidation.
- No full browser-based multi-user walkthrough is included in the automated test suite.
