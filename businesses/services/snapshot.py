"""
Freeze everything a simulation reads into one JSON document.

A run keeps this snapshot forever. Re-running it, explaining it with AI or printing it
in a report always uses these exact values, even if the business is edited later.
"""

import hashlib
import json


def plain(value) -> str:
    """2400.0000 -> "2400", 22.5000 -> "22.5". normalize() alone gives "2.4E+3"."""
    return format(value.normalize(), "f")


def build_snapshot(business, template_key: str, parameters: dict, overrides=None) -> dict:
    """
    `overrides` ({key: value}) replaces assumption values for one-off what-ifs, such as a
    slider in the preview. Overridden values are marked so nobody mistakes them for the
    saved inputs.
    """
    overrides = overrides or {}
    assumptions = {
        a.key: {"value": plain(a.value), "unit": a.unit, "source": a.source}
        for a in business.assumptions.all()
    }
    for key, value in overrides.items():
        unit = assumptions.get(key, {}).get("unit", "")
        assumptions[key] = {"value": str(value), "unit": unit, "source": "what_if"}

    components = [
        {
            "key": c.key,
            "name": c.name,
            "kind": c.kind,
            "criticality": c.criticality,
            "depends_on": sorted(d.key for d in c.depends_on.all()),
        }
        for c in business.components.prefetch_related("depends_on").order_by("key")
    ]
    return {
        "business": {
            "id": str(business.id),
            "name": business.name,
            "mode": business.mode,
            "currency": business.currency,
        },
        "template_key": template_key,
        "parameters": dict(sorted(parameters.items())),
        "assumptions": dict(sorted(assumptions.items())),
        "components": components,
    }


def snapshot_hash(snapshot: dict) -> str:
    """Same inputs -> same hash, regardless of key order (sort_keys) or whitespace."""
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assumption_values(snapshot: dict) -> dict[str, str]:
    return {key: item["value"] for key, item in snapshot["assumptions"].items()}
