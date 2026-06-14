# ShipSense

ShipSense is an AI-powered product analytics platform that helps solo builders and product managers understand user behavior and decide what to fix next. It ingests user interaction data, computes behavioral metrics, and generates actionable insights powered by a purpose-built AI agent.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Development](#development)
- [Deployment](#deployment)
- [License](#license)

---

## Overview

ShipSense turns raw user event data into a single, prioritized recommendation. Instead of drowning in dashboards and spreadsheets, builders get a direct answer: "What is the one thing I should do next?"

The platform provides:

- Product onboarding that immediately generates an initial AI insight based on existing data.
- Behavioral analytics including top actions, drop-off funnels, active users, and session duration.
- AI-generated insights using a structured analysis framework (WHAT I SEE / WHY IT MATTERS / WHAT TO DO / EFFORT / IMPACT).
- A conversational agent that answers product questions with data-backed answers and unsolicited follow-up insights.
- A dashboard UI for visualizing metrics and interacting with the agent.

---

## Architecture

The project is organized as three independent modules:

- `agent/` -- Standalone AI agent package containing the ShipSense analyst logic, OpenAI integration, prompt definitions, and rule-based fallbacks. Can be used independently of the backend.
- `backend/` -- FastAPI application exposing a REST API for product management, behavioral event ingestion, analytics computation, insight generation, and agent chat.
- `frontend/` -- React single-page application built with Vite, Tailwind CSS, and Recharts for dashboard visualization.

The backend depends on the agent package at the project root level. The frontend communicates with the backend through HTTP API calls.

### Data Flow

1. A user onboards a product via the API or the onboarding page.
2. Behavioral events (actions with user IDs and timestamps) are ingested and stored in SQLite.
3. The analyzer computes metrics: top actions, drop-off rates, active users, average session duration, and behavioral patterns.
4. The agent consumes these metrics to produce structured insights or answer conversational questions.
5. Insights are saved and served through the API to the frontend dashboard.

---

## Features

### Product Onboarding

Register a product by providing its URL, type (consumers, b2b, or internal tool), core action, and your user ID. The system immediately generates an initial insight based on any existing event data.

### Behavioral Analytics

- **Top Actions** -- Ranked list of the most frequent user actions with user counts and percentages.
- **Drop-Off Funnels** -- Automatic detection of where users fail to progress between sequential actions.
- **Active Users** -- Count of unique users within a configurable time window (default: 7 days).
- **Session Duration** -- Average session length estimated from event timestamps with 30-minute session timeouts.
- **Pattern Detection** -- Automatic flagging of unusual behavior such as low engagement on specific actions or rapid action switching that may indicate confusion.

### AI Insights

The ShipSense agent analyzes product data using a structured framework and produces:

- **WHAT I SEE** -- A concise summary of the data with specific numbers.
- **WHY IT MATTERS** -- The impact on the product's core goal.
- **WHAT TO DO** -- One specific, actionable fix.
- **EFFORT** -- Low, Medium, or High.
- **IMPACT** -- Low, Medium, or High.

Insights are generated via OpenAI GPT-4o. When the API key is unavailable or an error occurs, a rule-based fallback produces reasonable insights using the same structure.

### Agent Chat

A conversational interface that answers product-specific questions. The agent:

- Answers the specific question first, directly, in one sentence.
- Adds one relevant data point from the product data.
- Ends with one follow-up insight the user did not ask for but needs.
- Maintains conversation history for context-aware responses.

When GPT is unavailable, a rule-based fallback provides data-informed answers.

### Dashboard

A React-based dashboard with:

- **Overview** -- High-level metrics (active users, session duration, drop-off rate, top action).
- **User Behavior** -- Detailed behavior analytics with top actions and drop-off points.
- **AI Insights** -- Generated insights with recommended actions.
- **Ask Agent** -- Chat interface for asking product questions.
- **Settings** -- Product configuration.

---

## Tech Stack

### Backend

- **Language:** Python 3.10+
- **Framework:** FastAPI
- **Database:** SQLite (via sqlite3)
- **AI:** OpenAI Python SDK (GPT-4o)
- **Server:** Uvicorn

### Frontend

- **Language:** JavaScript (ES modules)
- **Framework:** React 19
- **Build Tool:** Vite
- **Styling:** Tailwind CSS 4
- **Charts:** Recharts
- **HTTP Client:** Axios
- **Routing:** React Router 7

### Agent

- **Language:** Python 3.10+
- **Dependencies:** OpenAI Python SDK
- **Design:** Modular package with client, context builder, prompt definitions, insight generation, and chat handling modules.

---

## Getting Started

### Prerequisites

- Python 3.10 or later
- Node.js 18 or later
- npm 9 or later

### Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd ship-sense
   ```

2. Set up the Python virtual environment:

   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. Install Python dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

4. Install frontend dependencies:

   ```bash
   cd frontend
   npm install
   cd ..
   ```

5. Configure environment variables (see [Configuration](#configuration)).

### Running the Development Servers

**Backend:**

```bash
cd backend
uvicorn shipsense.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`. Interactive API documentation is at `http://localhost:8000/docs`.

**Frontend:**

```bash
cd frontend
npm run dev
```

The frontend is available at `http://localhost:5173`.

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes (for AI features) | Your OpenAI API key for GPT-4o access. Without this key, the system falls back to rule-based analysis. |

The backend loads this file automatically via `python-dotenv`.

### Frontend Configuration

Set `VITE_API_URL` in `frontend/.env` to point to the backend API:

```
VITE_API_URL=http://localhost:8000/api
```

If unset, the frontend defaults to `/api` (same origin, useful for production deployments where the frontend is served by the same host).

---

## Project Structure

```
ship-sense/
├── agent/                          # Standalone AI agent package
│   ├── __init__.py                 # Public exports: generate_insights, chat_with_agent
│   ├── chat.py                     # Chat handler with GPT and fallback logic
│   ├── client.py                   # OpenAI client singleton
│   ├── context.py                  # Context builder for agent prompts
│   ├── insights.py                 # Insight generation with GPT and fallback
│   └── prompt.py                   # System prompt definitions
│
├── backend/                        # FastAPI application
│   ├── shipsense.db               # SQLite database (auto-created)
│   ├── requirements.txt           # Python dependencies
│   └── shipsense/                 # Python package
│       ├── __init__.py
│       ├── main.py                # API routes and application entrypoint
│       ├── models.py              # Pydantic request/response schemas
│       ├── db.py                  # SQLite database layer
│       └── analyzer.py            # Behavioral analytics engine
│
├── frontend/                       # React application
│   ├── index.html                 # HTML entrypoint
│   ├── package.json               # Node dependencies and scripts
│   ├── vite.config.js             # Vite build configuration
│   ├── eslint.config.js           # ESLint configuration
│   └── src/
│       ├── main.jsx               # React entrypoint
│       ├── App.jsx                # Application shell and routing
│       ├── index.css              # Tailwind CSS imports and global styles
│       ├── api/
│       │   └── client.js          # Axios HTTP client
│       ├── components/            # Reusable UI components
│       │   ├── Button.jsx
│       │   ├── Card.jsx
│       │   ├── DashboardLayout.jsx
│       │   ├── Input.jsx
│       │   ├── Loading.jsx
│       │   ├── MetricCard.jsx
│       │   ├── Sidebar.jsx
│       │   ├── StatusMessage.jsx
│       │   └── Table.jsx
│       ├── data/
│       │   └── mock.js            # Mock data for development
│       └── pages/
│           ├── Landing.jsx        # Public landing page
│           ├── Onboarding.jsx     # Product onboarding flow
│           └── dashboard/
│               ├── Overview.jsx   # Dashboard overview
│               ├── UserBehavior.jsx  # Behavior analytics
│               ├── AIInsights.jsx # AI-generated insights
│               ├── AskAgent.jsx   # Agent chat interface
│               └── Settings.jsx   # Product settings
│
├── venv/                          # Python virtual environment
└── .env                           # Environment variables
```

---

## API Reference

### Health

**GET /health**

Returns the API status and version.

Response:
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

### Onboard a Product

**POST /api/onboard**

Registers a new product and generates initial insights.

Request:
```json
{
  "url": "https://example.com",
  "product_type": "consumers",
  "core_action": "create account",
  "user_id": "user_abc"
}
```

`product_type` must be one of: `consumers`, `b2b`, `internal tool`.

Response:
```json
{
  "product_id": 1,
  "initial_insights": "WHAT I SEE:\n..."
}
```

### Get Product

**GET /api/product/{product_id}**

Returns product details with computed metrics.

### Ingest Behavior Events

**POST /api/behavior/ingest**

Ingests a batch of user behavior events for a product.

Request:
```json
{
  "product_id": 1,
  "events": [
    {
      "action": "click_signup",
      "user_id": "user_abc",
      "timestamp": "2026-06-14T12:00:00Z"
    }
  ]
}
```

### Query Behavior

**GET /api/behavior/{product_id}**

Returns top actions and drop-off points.

### Get Insights

**GET /api/insights/{product_id}**

Generates and returns AI insights with recommended actions.

### Agent Chat

**POST /api/agent/chat**

Sends a message to the AI agent and receives a response.

Request:
```json
{
  "product_id": 1,
  "user_id": "user_abc",
  "message": "Why are users dropping off?"
}
```

Response:
```json
{
  "reply": "42% of users drop off at the API key configuration step...",
  "data_point": "API key config: 42% drop-off",
  "confidence": 0.85
}
```

### Get Metrics

**GET /api/metrics/{product_id}**

Returns high-level product metrics.

---

## Development

### Running Tests

Tests are executed using `pytest` from the `backend/` directory:

```bash
cd backend
pytest
```

### Linting

**Frontend:**

```bash
cd frontend
npm run lint
```

**Backend:** Uses standard Python tooling. Run `ruff check shipsense/` or `pylint shipsense/` from the `backend/` directory.

### Database

The SQLite database (`shipsense.db`) is created automatically in the `backend/` directory on first startup. To reset the database, stop the server and delete the file.

The database contains four tables:

- **products** -- Registered products with URL, type, and core action.
- **events** -- User behavior events with action, user ID, and timestamp.
- **insights** -- Cached AI insights with summary and recommended actions.
- **chat_history** -- Conversation history for the agent chat feature.

### Agent Package

The agent package at `agent/` is a standalone Python package that can be imported independently of the backend. It exposes two public functions:

- `generate_insights(product, top_actions, drop_offs, active_users, avg_session, patterns)` -- Returns structured insights with summary and recommended actions.
- `chat_with_agent(product, message, top_actions, drop_offs, active_users, avg_session, patterns, chat_history)` -- Returns a conversational reply with a supporting data point.

Both functions include rule-based fallbacks that activate when the OpenAI API is unavailable.

---

## Deployment

### Backend

The FastAPI application can be deployed with any ASGI server:

```bash
uvicorn shipsense.main:app --host 0.0.0.0 --port 8000
```

For production, consider:

- Using a production ASGI server (uvicorn with workers, gunicorn + uvicorn workers).
- Switching to a production database (PostgreSQL via SQLAlchemy).
- Setting environment variables through your deployment platform.
- Serving the frontend static build from the same host or a CDN.

### Frontend

Build the static assets:

```bash
cd frontend
npm run build
```

The output in `frontend/dist/` can be served by any static file server (Nginx, Caddy, Cloudflare Pages, etc.).

---

## License

MIT
