"""
Replays docs/postman_collection.json through Django's test client.

Each request is sent exactly as the collection defines it (method, URL, body), variables
are saved the way its Postman test scripts save them, and the status code its test
expects is asserted. If the API changes and the collection doesn't, this fails, so the
collection students import can't silently go stale. Gemini and the website are faked.
"""

import json
import re
from pathlib import Path

import pytest

from intelligence.services import ai_client, scan_service
from intelligence.tests.fakes import FakeFetcher, FakeTransport
from intelligence.tests.test_ai_client import good_answer
from intelligence.tests.test_scan_and_committee import committee_answer, desk, profile_answer

COLLECTION = Path(__file__).resolve().parents[2] / "docs" / "postman_collection.json"
pytestmark = pytest.mark.django_db


def substitute(text: str, variables: dict) -> str:
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables.get(m.group(1), "")), text)


def expected_statuses(script: list[str]) -> list[int] | None:
    joined = "\n".join(script)
    if match := re.search(r"to\.have\.status\((\d+)\)", joined):
        return [int(match.group(1))]
    if match := re.search(r"oneOf\(\[([\d, ]+)\]\)", joined):
        return [int(n) for n in match.group(1).split(",")]
    return None


def save_variables(script: list[str], response, variables: dict) -> None:
    joined = "\n".join(script)
    for name, field in re.findall(r"set\('(\w+)', pm\.response\.json\(\)\.(\w+)\)", joined):
        if response.status_code < 300:
            variables[name] = response.json()[field]
    if "set('alertId', a.id)" in joined and response.json():
        variables["alertId"] = response.json()[0]["id"]


def test_collection_runs_top_to_bottom(client, alice, monkeypatch):
    # The outside world, faked: two Gemini answers and a tiny website.
    site = "https://books.toscrape.com/"
    monkeypatch.setattr(
        scan_service, "SafeFetcher", lambda: FakeFetcher({site: "<h1>Books</h1>£51.77"})
    )
    # Fake answers without website citations: the citation rule would (rightly) reject a
    # URL this run never fetched.
    desks = [desk(role, "hold") for role in ("finance", "operations", "market_competition", "risk")]
    transports = iter(
        [
            FakeTransport(good_answer()),
            FakeTransport(committee_answer(desks)),
            FakeTransport(profile_answer(dependencies=[])),
        ]
    )
    monkeypatch.setattr(ai_client, "default_transport", lambda: next(transports))

    collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
    variables = {v["key"]: v["value"] for v in collection["variable"]}
    variables.update(baseUrl="", email="alice@kirana.test", password="harbour-lantern-42")

    sent = 0
    for folder in collection["item"]:
        for item in folder["item"]:
            request = item["request"]
            url = substitute(request["url"]["raw"], variables)
            kwargs = {}
            body = request.get("body")
            if body and body["mode"] == "raw":
                kwargs = {
                    "data": substitute(body["raw"], variables),
                    "content_type": "application/json",
                }
            elif body and body["mode"] == "urlencoded":
                kwargs = {
                    "data": {
                        p["key"]: substitute(p["value"], variables) for p in body["urlencoded"]
                    }
                }
            response = getattr(client, request["method"].lower())(url, **kwargs)
            if hasattr(response, "streaming_content"):
                b"".join(response.streaming_content)  # an SSE stream runs the scan

            script = next(
                (e["script"]["exec"] for e in item.get("event", []) if e["listen"] == "test"), []
            )
            expected = expected_statuses(script)
            if expected:
                assert response.status_code in expected, (
                    f"{folder['name']} / {item['name']}: {response.status_code} "
                    f"{getattr(response, 'content', b'')[:300]!r}"
                )
            save_variables(script, response, variables)
            sent += 1

    assert sent == 30
    assert variables["decisionId"] and variables["runId"] and variables["eventsUrl"]
