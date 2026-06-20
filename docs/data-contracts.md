# ShipSense Data Contracts

## Canonical event

Every event accepted by the ShipSense Event Collector has this logical shape:

```json
{
  "event_id": "01J...",
  "schema_version": 1,
  "name": "signup_completed",
  "anonymous_id": "visitor_...",
  "session_id": "session_...",
  "occurred_at": "2026-06-20T12:34:56.000Z",
  "page_url": "https://product.example/onboarding",
  "properties": {}
}
```

During migration, the existing fields map as follows:

| Legacy field | Canonical field |
| --- | --- |
| `action` | `name` |
| `user_id` | `anonymous_id` |
| `timestamp` | `occurred_at` |

### Validation

- `event_id`, when supplied, is unique within a product.
- `schema_version` is a positive integer.
- `name` is non-empty and limited to 120 characters.
- `anonymous_id` is non-empty.
- `occurred_at` is a valid ISO-8601 timestamp and is normalized to UTC.
- `session_id`, `page_url`, and `properties` are optional.
- Sensitive input values, passwords, tokens, and personal page content are not
  collected.
- Malformed events are rejected at ingestion rather than silently included in
  analytics.

## Event occurrence

An event occurrence is one accepted canonical event.

`event_count` always refers to occurrences. It must never be labelled as users.

## Unique user

A unique user is a distinct `anonymous_id` within the selected time window.

`unique_users` always refers to distinct users, not events.

## Session

Events belong to the same session when:

1. They share a supplied `session_id`; or
2. They belong to the same user and consecutive events are less than 30 minutes
   apart.

A gap of 30 minutes or more starts a new session.

Session duration is the difference between the first and last event. A
single-event session has a duration of zero seconds and is included in session
counts but excluded from average duration until the UI explicitly supports
that distinction.

## Top action

A top action record contains:

```json
{
  "action": "signup_completed",
  "event_count": 14,
  "unique_users": 10,
  "event_frequency": "35%",
  "user_frequency": "50%"
}
```

- `event_frequency` is the share of valid event occurrences.
- `user_frequency` is the share of unique users who performed the action at
  least once.

## Funnel and drop-off

A funnel is an explicitly ordered list of steps. For a two-step transition:

- `users_who_reached` is the number of unique users who performed the first
  step.
- `users_who_continued` is the number of those users who later performed the
  next step.
- Repeated occurrences by the same user count once.
- The next step must occur after the first step.
- Intervening events do not invalidate continuation.
- Drop-off is:

```text
1 - users_who_continued / users_who_reached
```

When no explicit funnel exists, ShipSense may infer candidate transitions for
exploration, but inferred transitions must be labelled as inferred.

## Instrumentation readiness

Readiness is evaluated against the explicitly configured critical flow.

```text
collector_connected
event_count
last_event_at
configured_steps[]
coverage_count
coverage_percent
unique_users
minimum_sample
decision_ready
status
flow_steps[]
transitions[]
observed_actions[]
issues[]
next_actions[]
```

Each flow step reports:

```text
step
position
observed
event_count
unique_users
first_seen_at
last_seen_at
possible_matches[]
```

Each transition reports:

```text
step
next_step
users_who_reached
users_who_continued
minimum_sample
sample_gap
ready
orphaned_next_step_users
out_of_order_users
```

A behavioral decision is ready only when:

1. At least one valid collector event has arrived.
2. At least two unique critical-flow steps are configured.
3. Every configured step has been observed using its exact event name.
4. Every transition has at least five unique users at its starting step.

Ordering warnings do not discard valid ordered continuations, but they remain
visible because they may indicate incorrect event placement or identity
handling. Duplicate configured step names are invalid.

## Product context

Product context is declared by the product owner:

```text
target_user
user_problem
value_proposition
business_goal
constraints
```

It may guide language and hypothesis generation, but it is not measured
behavior. Analyst citations identify it with `source_type=product_context`.

The public HTML audit may capture bounded interaction context:

```text
h1_text
meta_description_text
primary_ctas[]
form_summaries[]
nav_labels[]
```

This describes the fetched public HTML response. It does not prove visibility,
attention, interaction, or behavior.

## Evidence

Every evidence record has:

```text
id
product_id
source_type
source_snapshot_id
metric_key
value
unit
sample_size
measured_at
freshness
quality
metadata
```

Allowed initial `source_type` values:

- `technical_audit`
- `behavior`
- `funnel`
- `experiment`
- `instrumentation`
- `product_context`

## Decision

Every Decision Card has:

```text
id
product_id
title
problem
evidence_ids[]
affected_flow
recommendation
expected_outcome
target_metric
baseline_value
effort
impact
confidence
confidence_reasons[]
invalidating_conditions[]
status
created_at
source_snapshot_id
```

The decision engine must reject factual claims that do not reference available
evidence IDs.

Behavioral decisions may also include testable hypotheses:

```text
id
statement
basis_evidence_ids[]
confidence
rationale
validation_action
```

A hypothesis is a possible explanation for measured evidence. It must not be
worded as an observed fact, and it must include a concrete validation action.

## Experiment

Every experiment has:

```text
id
product_id
decision_id
name
hypothesis
target_metric
guardrail_metrics[]
baseline_window
comparison_window
baseline_value
target_value
status
shipped_at
result
created_at
```

Initial statuses:

- `planned`
- `shipped`
- `collecting`
- `evaluated`
- `inconclusive`
