#!/usr/bin/env python3
import argparse
import json
import re
import urllib.request


def request(url, method="GET", payload=None, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        body = response.read().decode()
        content_type = response.headers.get("content-type", "")
        return json.loads(body) if "json" in content_type else body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    parser.add_argument("--frontend", required=True)
    parser.add_argument(
        "--allow-sqlite",
        action="store_true",
        help="Allow SQLite instead of requiring PostgreSQL",
    )
    args = parser.parse_args()
    backend = args.backend.rstrip("/")
    frontend = args.frontend.rstrip("/")

    health = request(f"{backend}/health")
    assert health["status"] == "ok"
    if not args.allow_sqlite:
        assert health["database"] == "postgresql", health

    workspace = request(f"{backend}/api/workspaces", method="POST")
    workspace_headers = {"X-Workspace-Key": workspace["workspace_key"]}
    onboard = request(
        f"{backend}/api/onboard",
        method="POST",
        headers=workspace_headers,
        payload={
            "url": "https://example.com",
            "product_type": "b2b",
            "core_action": "signup",
            "critical_flow": ["landing", "signup"],
            "audit_data": {"performance_score": 75},
        },
    )
    products = request(f"{backend}/api/products", headers=workspace_headers)
    assert any(item["id"] == onboard["product_id"] for item in products)
    recovered = request(
        f"{backend}/api/product/{onboard['product_id']}",
        headers=workspace_headers,
    )
    assert recovered["id"] == onboard["product_id"]

    collector = request(f"{backend}/static/shipsense-collector.js")
    assert "data-collector-key" in collector
    assert "collector_key" in collector

    html = request(frontend)
    assert "cdn.pendo.io/agent/static/" in html
    asset_match = re.search(r'<script[^>]+src="(/assets/[^"]+\.js)"', html)
    assert asset_match, "Frontend JavaScript asset not found"
    bundle = request(f"{frontend}{asset_match.group(1)}")
    assert "trackAgent" in bundle
    assert backend in bundle

    print("Deployment verification passed")
    print(f"Backend database: {health['database']}")
    print(f"Persisted product: {onboard['product_id']}")
    print("Collector, frontend API binding, Pendo SDK, and trackAgent verified")


if __name__ == "__main__":
    main()
