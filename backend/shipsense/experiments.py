from datetime import datetime, timezone

from . import analyzer


MIN_EVALUATION_SAMPLE = 5


def parse_baseline(value):
    normalized = str(value).strip()
    if normalized.endswith("%"):
        return float(normalized[:-1]), "percent"
    if "/" in normalized:
        return float(normalized.split("/", 1)[0]), "score"
    return float(normalized), "number"


def evaluate_experiment(experiment, product, events, audit_data):
    if not experiment.get("shipped_at"):
        return "planned", {
            "conclusion": "not_shipped",
            "message": "Mark the experiment as shipped before evaluating it.",
        }

    metric = experiment["target_metric"]

    if metric.startswith("funnel:") and metric.endswith(":completion_rate"):
        baseline, _ = parse_baseline(experiment["baseline_value"])
        _, step, next_step, _ = metric.split(":", 3)
        drop_offs = analyzer.calculate_drop_off(
            events,
            steps=[step, next_step],
        )
        transition = drop_offs[0] if drop_offs else None
        sample_size = transition["users_who_reached"] if transition else 0
        if sample_size < MIN_EVALUATION_SAMPLE:
            return "inconclusive", {
                "conclusion": "insufficient_data",
                "message": (
                    f"Only {sample_size} users reached the measured step after "
                    f"shipping; at least {MIN_EVALUATION_SAMPLE} are required."
                ),
                "sample_size": sample_size,
            }
        current = 100 - int(transition["drop_off_rate"].rstrip("%"))
        return _comparison_result(baseline, current, "percent", sample_size)

    if metric.startswith("technical_audit:"):
        metric_key = metric.split(":", 1)[1]
        if metric_key == "security_score":
            current = (audit_data or {}).get("security_headers", {}).get("security_score")
        else:
            current = audit_data.get(metric_key) if audit_data else None
        if current is None:
            return "inconclusive", {
                "conclusion": "missing_measurement",
                "message": "Refresh the technical audit before evaluating this experiment.",
            }
        if metric_key == "has_mobile_viewport":
            improved = bool(current)
            return "evaluated", {
                "conclusion": "improved" if improved else "unchanged",
                "recommendation": "keep" if improved else "iterate",
                "baseline": False,
                "current": bool(current),
                "change": int(bool(current)),
                "unit": "boolean",
                "sample_size": None,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            }
        baseline, unit = parse_baseline(experiment["baseline_value"])
        higher_is_better = metric_key not in {"images_missing_alt"}
        return _comparison_result(
            baseline,
            float(current),
            unit,
            None,
            higher_is_better=higher_is_better,
        )

    return "inconclusive", {
        "conclusion": "unsupported_metric",
        "message": f"ShipSense cannot evaluate '{metric}' yet.",
    }


def _comparison_result(
    baseline,
    current,
    unit,
    sample_size,
    higher_is_better=True,
):
    change = current - baseline
    improvement = change if higher_is_better else -change
    if improvement > 0:
        conclusion = "improved"
        recommendation = "keep"
    elif improvement < 0:
        conclusion = "regressed"
        recommendation = "revisit"
    else:
        conclusion = "unchanged"
        recommendation = "iterate"

    return "evaluated", {
        "conclusion": conclusion,
        "recommendation": recommendation,
        "baseline": baseline,
        "current": current,
        "change": change,
        "unit": unit,
        "sample_size": sample_size,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
