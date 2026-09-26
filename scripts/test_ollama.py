"""End-to-end checks for the local Ollama smart-filter path."""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_server


CASES = [
    {
        "query": "critical inverter work orders in Munster with estimated cost over 5000",
        "check": lambda row: (
            row["priority"] == "Critical"
            and row["asset_type"] == "Inverter"
            and row["region"] == "Munster"
            and row["estimated_cost_eur"] > 5000
        ),
    },
    {
        "query": "open or in progress work orders with generation loss above 100 kW",
        "check": lambda row: (
            row["status"] in {"Open", "In Progress"}
            and row["generation_loss_kw"] is not None
            and row["generation_loss_kw"] > 100
        ),
    },
    {
        "query": "top 5 most expensive inverter repairs",
        "check": lambda row: row["asset_type"] == "Inverter",
        "result_check": lambda result: (
            result["total"] == 5
            and len(result["rows"]) == 5
            and [row["estimated_cost_eur"] for row in result["rows"]]
            == sorted((row["estimated_cost_eur"] for row in result["rows"]), reverse=True)
        ),
    },
]


def post_payload(url: str, values: dict) -> dict:
    payload = json.dumps(values).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError("App returned HTTP " + str(exc.code) + ": " + detail) from exc


def post_query(url: str, query: str) -> dict:
    return post_payload(url, {"smart_query": query, "page_size": 100})


def check_rows(query: str, result: dict, check) -> None:
    rows = result["rows"]
    if not rows:
        raise AssertionError("No rows returned for: " + query)
    invalid = [row for row in rows if not check(row)]
    if invalid:
        raise AssertionError(
            "Filter returned rows outside the request: "
            + json.dumps(invalid[:3], ensure_ascii=False)
            + "; plan="
            + json.dumps(result.get("plan"), ensure_ascii=False)
        )


def main() -> None:
    server = create_server("127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = "http://127.0.0.1:" + str(port)
    base_url = origin + "/api/query"
    configured_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")
    models = list(dict.fromkeys([configured_model, "qwen2.5-coder:1.5b"]))
    original_model = os.environ.get("OLLAMA_MODEL")
    try:
        with urllib.request.urlopen(origin + "/", timeout=10) as response:
            page = response.read()
            if response.status != 200 or b"Work orders" not in page or b"Build a filter" in page:
                raise AssertionError("The smart-filter-only table page did not load")
        with urllib.request.urlopen(origin + "/app.js", timeout=10) as response:
            script = response.read()
            if response.status != 200 or b"smart_plan" not in script or b"manual_filters" in script:
                raise AssertionError("The smart-filter table client did not load")
        print("PASS | smart-filter-only app and table UI are served")

        for case in CASES:
            os.environ["OLLAMA_MODEL"] = configured_model
            result = post_query(base_url, case["query"])
            check_rows(case["query"], result, case["check"])
            if not result.get("plan", {}).get("filters"):
                raise AssertionError("Ollama did not create filter conditions")
            if case.get("result_check") and not case["result_check"](result):
                raise AssertionError("Sort or top-N result did not match: " + case["query"])
            print("PASS | " + case["query"] + " | " + result["plan"].get("model", configured_model))
            print("  Matching records: " + str(result["matched_count"]))

            if case["query"].startswith("critical inverter"):
                cached = post_payload(base_url, {"smart_plan": result["plan"], "page_size": 100})
                if cached["matched_count"] != result["matched_count"]:
                    raise AssertionError("Reusing a validated plan changed its matching records")
                print("PASS | cached plan reuse preserves the filter during pagination")

        today = date.today()
        this_week = today - timedelta(days=today.weekday())
        last_week_start = this_week - timedelta(days=7)
        query = "opened before last week"
        for model in models:
            os.environ["OLLAMA_MODEL"] = model
            result = post_query(base_url, query)
            expected = last_week_start.isoformat()
            expected_filter = {"field": "opened_at", "op": "lt", "value": expected}
            if expected_filter not in result.get("plan", {}).get("filters", []):
                raise AssertionError(
                    model + " produced the wrong last-week boundary: "
                    + json.dumps(result.get("plan"), ensure_ascii=False)
                )
            check_rows(query, result, lambda row: row["opened_at"] < expected)
            print("PASS | " + model + " interprets 'opened before last week' as opened_at < " + expected)

        print("\nAll local Ollama smart-filter checks passed.")
    finally:
        if original_model is None:
            os.environ.pop("OLLAMA_MODEL", None)
        else:
            os.environ["OLLAMA_MODEL"] = original_model
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
