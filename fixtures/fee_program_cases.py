from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


OFFER = {
    "schema": "truecostcompiler/offer/v1",
    "offer_name": "MetroBox public delivery offer",
    "currency": "USD",
    "minor_unit_exponent": 2,
    "source_documents": [
        {
            "id": "PRICING",
            "uri": "https://pricing.example.test/metrobox",
            "retrieved_at": "2026-08-12T09:00:00Z",
            "text": (
                "Every delivery has a $10.00 booking charge. Distance costs $2.50 "
                "per whole kilometre. Deliveries in the REMOTE region add $7.00."
            ),
        },
        {
            "id": "TERMS",
            "uri": "https://pricing.example.test/metrobox/terms",
            "retrieved_at": "2026-08-12T09:00:00Z",
            "text": (
                "If expedited service is selected, add 10% after the booking, "
                "distance, and regional charges and round to the nearest cent, "
                "with half cents rounded up. Listed prices include all taxes."
            ),
        },
    ],
    "parameters": [
        {
            "name": "distance_km",
            "kind": "INTEGER",
            "minimum": 0,
            "maximum": 500,
            "values": [],
        },
        {
            "name": "expedited",
            "kind": "BOOLEAN",
            "minimum": 0,
            "maximum": 1,
            "values": [],
        },
        {
            "name": "region",
            "kind": "ENUM",
            "minimum": 0,
            "maximum": 0,
            "values": ["REMOTE", "LOCAL"],
        },
    ],
}


COMPLETE_PROGRAM = {
    "schema": "truecostcompiler/fee-program/v1",
    "rules": [
        {
            "stage": 0,
            "effect": "ADD",
            "calculation": "FIXED",
            "value_minor": 1000,
            "basis_points": 0,
            "multiplier_parameter": "",
            "rounding": "NONE",
            "conditions": [],
            "source_document_ids": ["PRICING"],
        },
        {
            "stage": 1,
            "effect": "ADD",
            "calculation": "PER_INTEGER_PARAMETER",
            "value_minor": 250,
            "basis_points": 0,
            "multiplier_parameter": "distance_km",
            "rounding": "NONE",
            "conditions": [],
            "source_document_ids": ["PRICING"],
        },
        {
            "stage": 1,
            "effect": "ADD",
            "calculation": "FIXED",
            "value_minor": 700,
            "basis_points": 0,
            "multiplier_parameter": "",
            "rounding": "NONE",
            "conditions": [
                {"parameter": "region", "operator": "EQ", "value": "REMOTE"}
            ],
            "source_document_ids": ["PRICING"],
        },
        {
            "stage": 2,
            "effect": "ADD",
            "calculation": "BASIS_POINTS_OF_RUNNING_TOTAL",
            "value_minor": 0,
            "basis_points": 1000,
            "multiplier_parameter": "",
            "rounding": "HALF_UP",
            "conditions": [
                {"parameter": "expedited", "operator": "EQ", "value": True}
            ],
            "source_document_ids": ["TERMS"],
        },
    ],
    "uncertainty_codes": [],
}


INCOMPLETE_PROGRAM = {
    "schema": "truecostcompiler/fee-program/v1",
    "rules": [copy.deepcopy(COMPLETE_PROGRAM["rules"][0])],
    "uncertainty_codes": ["UNSUPPORTED_FORMULA"],
}


APPROVAL = {
    "candidate_faithful": True,
    "candidate_conservative": True,
    "scope_accounted_for": True,
    "condition_logic_supported": True,
}


SCENARIO_REMOTE_EXPEDITED = {
    "distance_km": 10,
    "expedited": True,
    "region": "REMOTE",
}


def clone_offer() -> dict[str, Any]:
    return copy.deepcopy(OFFER)


def clone_program(complete: bool = True) -> dict[str, Any]:
    return copy.deepcopy(COMPLETE_PROGRAM if complete else INCOMPLETE_PROGRAM)


def encode(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def normalized_offer() -> dict[str, Any]:
    offer = clone_offer()
    offer["parameters"] = sorted(offer["parameters"], key=lambda item: item["name"])
    for parameter in offer["parameters"]:
        parameter["values"] = sorted(parameter["values"])
    offer["source_documents"] = sorted(
        offer["source_documents"], key=lambda item: item["id"]
    )
    return offer


def expected_offer_id() -> str:
    preimage = "truecostcompiler/offer/v1\x00" + canonical(normalized_offer())
    return "tcc1:" + hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def normalized_program(program: dict[str, Any] | None = None) -> dict[str, Any]:
    result = copy.deepcopy(COMPLETE_PROGRAM if program is None else program)
    for rule in result["rules"]:
        rule["conditions"] = sorted(rule["conditions"], key=canonical)
        rule["source_document_ids"] = sorted(rule["source_document_ids"])
    result["rules"] = sorted(result["rules"], key=lambda item: (item["stage"], canonical(item)))
    result["uncertainty_codes"] = sorted(result["uncertainty_codes"])
    return result


def expected_model_hash(program: dict[str, Any] | None = None) -> str:
    preimage = "truecostcompiler/fee-program/v1\x00" + canonical(normalized_program(program))
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()
