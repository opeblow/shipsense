# ShipSense

ShipSense is an evidence-driven product decision system for fast-moving
builders. It combines a public product-health audit with real, instrumented
user behavior to answer:

> What is the most important product problem to fix next, why does it matter,
> and did the shipped fix work?

The product is built around a closed loop:

```text
Measure -> Diagnose -> Decide -> Act -> Verify
```

ShipSense is not intended to be another general analytics dashboard. Its
primary output is one prioritized Decision Card, backed by inspectable
evidence and connected to a measurable experiment.

## What ShipSense can see

ShipSense has two evidence modes. They are deliberately kept separate.

### Immediate technical evidence

Given a public URL, ShipSense can inspect:

- Page structure and content signals
- Performance and mobile-readiness signals
- Accessibility and SEO signals
- Response and security headers
- Google PageSpeed results when the external service is available

This provides useful product-health evidence before any instrumentation is
installed. It does **not** reveal how real users behave.

### Instrumented behavioral evidence

After the ShipSense Event Collector is installed, ShipSense can measure:

- Event occurrences and unique users
- Sessions
- Explicit critical-flow progression
- Funnel continuation and drop-off
- Repeated and abandoned actions
- Before-and-after results for a shipped experiment

ShipSense does not infer behavior from a URL crawl. Unknown behavior remains
unknown until events arrive.

## How it helps

A typical ShipSense workflow is:

1. Connect a public product URL and describe the product's core outcome.
2. Define the exact event names in its critical user flow.
3. Review the immediate technical baseline.
4. Install the product-scoped collector and receive real events.
5. Refresh the Decision Card when stronger evidence arrives.
6. Turn the decision into an experiment with a frozen baseline.
7. Mark the change as shipped and collect post-ship evidence.
8. Evaluate whether the target metric improved.
9. Ask the Analyst questions and inspect the evidence behind each answer.

For example, if the configured flow is `landing -> signup -> activated`,
ShipSense can identify that only 40% of users continue past `landing`,
recommend one change, and later determine that the post-ship completion rate
rose to 80%. The recommendation, sample size, baseline, result, and cited
Analyst response remain inspectable.

## Core capabilities

- **Decision Cards:** one prioritized problem, evidence, recommendation,
  expected result, effort, impact, confidence reasons, verification metric,
  and invalidating conditions.
- **Evidence workspace:** separates technical observations from behavioral
  measurements and labels their source.
- **Critical flows:** product owners define the ordered events that represent
  success instead of relying on guessed funnels.
- **Instrumentation confidence:** reports step coverage, unique-user samples,
  likely event-name mismatches, downstream-only events, ordering violations,
  and the exact actions required before a behavioral decision is valid.
- **Product context:** stores the target user, user problem, value proposition,
  business goal, and operating constraints as owner-declared context.
- **Testable cause hypotheses:** combines measured drop-off with public page
  interaction context to propose possible causes, confidence, supporting
  evidence IDs, and a validation action. Hypotheses are never presented as
  measured findings.
- **Experiments:** freeze a baseline, mark a change as shipped, evaluate only
  post-ship data, and return a keep, iterate, or revisit outcome.
- **Grounded Analyst:** answers from a normalized evidence registry, returns
  valid citation IDs, and derives confidence from cited evidence quality.
- **Versioned decisions:** new evidence marks the current decision stale;
  refreshing creates a new version instead of silently rewriting history.
- **Workspace isolation:** browser-held workspace keys scope dashboard data;
  separate collector keys authorize event ingestion for one product.
- **Safe public auditing:** rejects local, private, link-local, reserved,
  credential-bearing, and nonstandard-port targets and validates redirects.

The complete behavioral and data rules are documented in
[the data contracts](docs/data-contracts.md).

## Current status

The backend has been exercised locally against real external infrastructure,
not only mocks:

- 59 backend tests pass.
- A complete API journey passes from workspace creation through experiment
  evaluation and cited Analyst answers.
- SQLite persistence survives a backend restart.
- A real public URL audit succeeds.
- Cold-start live URL decisions clearly identify when they are based on a
  public audit only and when behavioral evidence is still unavailable.
- A real GPT-4o request succeeds when `OPENAI_API_KEY` is configured.
- A production frontend build communicates with the local backend.
- Pendo loading, `trackAgent`, collector delivery, and CORS checks pass.
- Frontend lint and production build pass.

The local run produced a behavioral baseline of 40%, an evaluated post-ship
result of 80%, and a cited Analyst response grounded in that experiment.

Still unverified in the current environment:

- Runtime behavior against an actual PostgreSQL server
- The current Render and Vercel deployments

See the dated [local infrastructure test report](docs/local-infrastructure-test.md)
for the exact test scope and results.

## Architecture

```text
Public product URL --------> URL auditor -----------+
                                                     |
Product website ------------> Event Collector ------+--> Evidence registry
                                                           |
Product intent + flow -------------------------------------+
                                                           |
                                                           v
                                                    Decision engine
                                                           |
                                      +--------------------+------------------+
                                      |                                       |
                                      v                                       v
                                Decision Card                           Grounded Analyst
                                      |
                                      v
                                  Experiment
                                      |
                                      v
                              Before/after result
```

The repository contains:

- `backend/` — FastAPI API, SQLAlchemy persistence, URL auditing, event
  analysis, decisions, experiments, and collector asset.
- `agent/` — OpenAI and deterministic fallback logic for insights and
  evidence-grounded Analyst responses.
- `frontend/` — React 19 and Vite application with Today, Evidence,
  Experiments, Technical Health, Analyst, and Settings views.
- `docs/` — product rules, data contracts, infrastructure evidence, and the
  weakness register.
- `scripts/` — PostgreSQL and public deployment verification.

### Technology

- Python 3.12
- FastAPI and Uvicorn
- SQLAlchemy Core
- SQLite locally; PostgreSQL through `DATABASE_URL`
- OpenAI Python SDK using GPT-4o
- React 19, Vite 8, Tailwind CSS 4, and Recharts

## Local setup

### Prerequisites

- Python 3.12
- Node.js 20.19 or newer; `.nvmrc` pins Node 22.12
- npm

### Install

```bash
git clone https://github.com/opeblow/shipsense.git
cd shipsense

python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt

cd frontend
npm install
cd ..
```

For Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

### Configure the backend

Create `backend/.env`:

```dotenv
OPENAI_API_KEY=your_key_here
# Optional. If omitted, local SQLite is used.
# DATABASE_URL=postgresql://user:password@host:5432/shipsense
```

`OPENAI_API_KEY` is optional. Without it, deterministic fallback analysis is
used. If `DATABASE_URL` is omitted, the backend creates a local
`backend/shipsense.db` SQLite database.

### Configure the frontend

Create `frontend/.env`:

```dotenv
VITE_API_URL=http://localhost:8000
```

`VITE_API_URL` must be the backend origin. Do not append `/api`; the client
adds API paths itself.

### Run

Start the backend:

```bash
source .venv/bin/activate
cd backend
uvicorn shipsense.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Open:

- Frontend: `http://localhost:5173`
- API health: `http://localhost:8000/health`
- Interactive API documentation: `http://localhost:8000/docs`

## First product setup

Onboarding asks for:

- A public URL
- Product type
- Core user action
- Target user, user problem, and value proposition
- An ordered critical flow using exact event names

After product creation, ShipSense generates a product ID and collector key.
Install the generated snippet on the connected product:

```html
<script
  src="http://localhost:8000/static/shipsense-collector.js"
  data-product-id="YOUR_PRODUCT_ID"
  data-collector-key="YOUR_COLLECTOR_KEY"
  data-api-url="http://localhost:8000">
</script>
```

The collector records page views and stable clicks. Product-specific actions
should be sent explicitly:

```html
<button data-shipsense="signup_started">Start signup</button>

<script>
  window.ShipSense.track("signup_completed", {
    plan: "pro"
  });
</script>
```

The strings passed to `track` must match the configured critical-flow steps.
Settings reports the event count and latest received event so installation can
be verified. It also reports flow coverage and baseline readiness for every
configured transition. Rotating the collector key invalidates the old snippet.

For a fast walkthrough, the first onboarding screen can create an explicitly
labelled sample workspace. Its events and experiment results are synthetic and
remain visibly labelled as sample data throughout the dashboard.

## Recommended demo flow

For a short hackathon demo, use the labelled sample workspace. It shows the
complete loop without asking judges to install a collector during the demo.

1. Open onboarding and click **Explore labelled sample data**.
2. On **Today**, show the four-step loop: evidence, decision basis,
   hypothesis, and verification.
3. Explain that the Decision Card is the primary output: one product problem,
   evidence, recommendation, baseline, and verification metric.
4. Open **Evidence** to show the behavioral events, session stats, and
   observed transitions behind the decision.
5. Open **Experiments** to show the frozen baseline, post-ship result, and
   keep/iterate recommendation.
6. Open **Settings** to show how a real product connects through the
   collector snippet and readiness checks.

Suggested demo line:

> ShipSense starts with evidence, chooses one product decision, forms a
> testable hypothesis, and verifies whether the shipped change worked.

Real URL onboarding is still useful in the demo as a cold-start proof. Before
events arrive, ShipSense presents a live audit decision and explicitly says it
is not a user-behavior decision yet.

## API model

The browser first creates an anonymous workspace:

```http
POST /api/workspaces
```

Dashboard requests then include:

```http
X-Workspace-Key: <workspace_key>
```

Collector ingestion uses the product ID and collector key in its JSON payload
instead of the workspace header.

Important route groups:

| Purpose | Routes |
|---|---|
| Health and API schema | `GET /health`, `GET /docs`, `GET /openapi.json` |
| Workspace and products | `POST /api/workspaces`, `GET /api/products`, `POST /api/onboard` |
| Technical evidence | `POST /api/audit-url`, `GET /api/audit/{product_id}`, `POST /api/audit/{product_id}/refresh` |
| Behavior | `POST /api/behavior/ingest`, `GET /api/behavior/{product_id}`, `GET /api/metrics/{product_id}` |
| Instrumentation | `GET /api/product/{product_id}/instrumentation-readiness` |
| Product context | `PUT /api/product/{product_id}/context` |
| Decisions | `GET /api/decision/{product_id}`, `POST /api/decision/{product_id}/refresh` |
| Experiments | `POST /api/experiments`, `POST /api/experiments/{id}/ship`, `POST /api/experiments/{id}/evaluate` |
| Analyst | `GET /api/agent/context/{product_id}`, `POST /api/agent/chat` |
| Integration | `PUT /api/product/{product_id}/critical-flow`, collector status and key rotation routes |
| Labelled demo | `POST /api/demo/sample-product` |

Use the generated OpenAPI documentation for complete request and response
schemas.

## Sponsor integration and product collector

The two integrations serve different purposes:

- **Novus by Pendo:** the official sponsor SDK is loaded in
  `frontend/index.html`; Analyst interactions emit `trackAgent`
  instrumentation.
- **ShipSense Event Collector:** the script served from
  `/static/shipsense-collector.js` sends product-specific behavioral evidence
  into ShipSense.

They are intentionally named and implemented separately.

## Verification

Run the backend suite from the repository root:

```bash
source .venv/bin/activate
PYTHONPATH=backend:. python3 -m pytest backend/tests -q
```

Run frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

Test a real PostgreSQL database:

```bash
DATABASE_URL='postgresql://user:password@host:5432/shipsense' \
  python3 scripts/postgres_smoke.py
```

Verify public deployments:

```bash
python3 scripts/verify_deployment.py \
  --backend https://your-api.example \
  --frontend https://your-app.example
```

The deployment verifier checks backend health, product persistence, the
collector asset, frontend API binding, the Pendo SDK, and `trackAgent`
instrumentation.

## Deployment

`render.yaml` defines a Render web service and PostgreSQL database. The backend
requires:

```dotenv
DATABASE_URL=postgresql://...
OPENAI_API_KEY=...
```

Build the frontend for Vercel or another static host with:

```bash
cd frontend
VITE_API_URL=https://your-api.example npm run build
```

Because Vite embeds environment variables at build time, changing
`VITE_API_URL` requires a new frontend build.

## Data and security boundaries

- Collector visitor IDs are anonymous browser-generated identifiers.
- Workspace and collector credentials are application keys, not a complete
  user-account authentication system.
- Collector events may contain custom properties chosen by the integrating
  product; sensitive personal data should not be sent.
- Public URL auditing performs SSRF-oriented validation on the initial target
  and redirects.
- Cross-origin event ingestion is currently enabled for collector delivery.
- Consent, retention, deletion, and production abuse controls remain open
  work and are listed in the weakness register.

## Documentation

- [Data contracts](docs/data-contracts.md)
- [Local infrastructure test report](docs/local-infrastructure-test.md)

## License

MIT
