# estimator.py — intentionally returns no simulated data.
# ShipSense only surfaces real measurements from the live URL audit or
# genuine user-event data ingested via the Novus tracker.
# Returning None from both functions ensures callers fall through to real
# data and never render invented numbers.


def estimate_metrics(product):
    """Return None — no simulated metrics."""
    return None


def estimate_behavior(product):
    """Return None — no simulated behavior."""
    return None
