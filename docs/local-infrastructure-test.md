# Local Infrastructure Test Report

Test date: June 20, 2026

## Environment

- Backend: local Uvicorn process on `127.0.0.1`
- Database: fresh SQLite file
- Frontend: production Vite build served locally
- OpenAI: configured external API and real GPT-4o request
- Audit target: `https://example.com`
- Google PageSpeed: real external API

## Passed

- Backend startup and database initialization
- Health check and SQLite connectivity
- Workspace creation
- Public product onboarding
- SSRF-safe DNS validation
- Real HTTP page fetch and response-header audit
- HTML parsing: page title, H1, links, security headers, and other structure
- OpenAI key authentication
- Real GPT-4o response using model `gpt-4o-2024-08-06`
- OpenAI-backed initial product insight
- Collector-authenticated event ingestion
- Duplicate-safe event persistence
- Decision stale-state detection after new evidence
- Decision refresh and version increment
- Explicit funnel baseline: 40%
- Experiment creation and ship timestamp
- Post-ship event ingestion
- Experiment evaluation: 80% completion, improved by 40 percentage points
- Evidence-cited Analyst answer
- SQLite persistence across a backend restart
- Product, critical flow, experiment result, and Analyst evidence recovery
- Production frontend bundle bound to local backend
- Pendo SDK present
- `trackAgent` present in the built frontend
- Cross-origin preflight between local frontend and backend
- Deployment verification script
- Manual browser walkthrough of the local frontend/backend sample path
- Real URL cold-start path labels audit-only decisions separately from
  behavior-backed decisions

## External limitation observed

Google PageSpeed returned HTTP 429 for both mobile and desktop strategies from
this environment. ShipSense continued using real HTML and response-header
evidence. The audit result now exposes `pagespeed_error` so missing Lighthouse
scores are explained instead of silently appearing as null.

## Automated verification

- 59 backend tests pass
- Complete API journey test passed
- Frontend lint passed
- Frontend production build passed
- Python and script compilation passed
- 26 OpenAPI routes generated

## Not tested locally

- PostgreSQL runtime, because no PostgreSQL server or `DATABASE_URL` is
  available in the local environment
- Render and Vercel deployment state
- Automated in-app browser interaction, because the in-app browser was
  unavailable

Dedicated scripts are available for the first two:

```bash
DATABASE_URL='postgresql://...' python scripts/postgres_smoke.py
```

```bash
python scripts/verify_deployment.py \
  --backend https://your-api.example \
  --frontend https://your-app.example
```
