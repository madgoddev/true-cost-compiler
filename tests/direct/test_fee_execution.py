from __future__ import annotations

import copy
import json

import pytest

from fixtures.fee_program_cases import (
    APPROVAL,
    SCENARIO_REMOTE_EXPEDITED,
    clone_offer,
    clone_program,
    encode,
    expected_model_hash,
    expected_offer_id,
)


def compile_with(compiler, direct_vm, program):
    direct_vm.mock_llm("TCC_COMPILE_FEE_PROGRAM_V2", encode(program))
    return compiler.compile_offer(encode(clone_offer()))


def test_complete_program_persists_and_quotes(compiler, direct_vm):
    offer_id = compile_with(compiler, direct_vm, clone_program())
    assert offer_id == expected_offer_id()
    assert compiler.get_program_count() == 1
    assert compiler.get_program_id(0) == offer_id
    assert compiler.has_compilation(offer_id) is True
    assert compiler.get_offer(offer_id)["currency"] == "USD"
    program = compiler.get_fee_program(offer_id)
    assert program["complete"] is True
    assert program["uncertainty_mask"] == 0
    assert program["model_hash"] == expected_model_hash()
    quote = compiler.quote(
        offer_id,
        program["model_hash"],
        encode(SCENARIO_REMOTE_EXPEDITED),
    )
    assert quote["total_minor"] == 4620
    assert quote["applied_rule_indexes"] == [0, 1, 2, 3]
    assert compiler.matches_complete_program(offer_id, program["model_hash"]) is True


def test_conditions_exclude_remote_and_expedited_rules(compiler, direct_vm):
    offer_id = compile_with(compiler, direct_vm, clone_program())
    program = compiler.get_fee_program(offer_id)
    quote = compiler.quote(
        offer_id,
        program["model_hash"],
        encode({"distance_km": 2, "expedited": False, "region": "LOCAL"}),
    )
    assert quote["total_minor"] == 1500
    assert quote["applied_rule_indexes"] == [0, 2]


def test_program_is_global_and_cached_without_second_llm(compiler, direct_vm, direct_bob):
    source = encode(clone_offer())
    offer_id = compile_with(compiler, direct_vm, clone_program())
    direct_vm.clear_mocks()
    direct_vm.sender = direct_bob
    assert compiler.compile_offer(source) == offer_id
    assert compiler.get_program_count() == 1


def test_incomplete_program_is_visible_but_cannot_quote(compiler, direct_vm):
    offer_id = compile_with(compiler, direct_vm, clone_program(False))
    program = compiler.get_fee_program(offer_id)
    assert program["complete"] is False
    assert program["uncertainty_codes"] == ["UNSUPPORTED_FORMULA"]
    assert program["uncertainty_mask"] == 1 << 7
    assert compiler.matches_complete_program(offer_id, program["model_hash"]) is False
    with direct_vm.expect_revert("fee_program_incomplete"):
        compiler.quote(
            offer_id,
            program["model_hash"],
            encode(SCENARIO_REMOTE_EXPEDITED),
        )


@pytest.mark.parametrize(
    "scenario,reason",
    [
        ({"distance_km": True, "expedited": True, "region": "REMOTE"}, "scenario_integer_type"),
        ({"distance_km": 501, "expedited": True, "region": "REMOTE"}, "scenario_integer_range"),
        ({"distance_km": 1, "expedited": "yes", "region": "REMOTE"}, "scenario_boolean_type"),
        ({"distance_km": 1, "expedited": True, "region": "MOON"}, "scenario_enum_value"),
        ({"distance_km": 1, "expedited": True}, "scenario_parameter_keys"),
        ({"distance_km": 1, "expedited": True, "region": "REMOTE", "x": 1}, "scenario_parameter_keys"),
    ],
)
def test_scenario_validation(compiler, direct_vm, scenario, reason):
    offer_id = compile_with(compiler, direct_vm, clone_program())
    model_hash = compiler.get_fee_program(offer_id)["model_hash"]
    with direct_vm.expect_revert(reason):
        compiler.quote(offer_id, model_hash, encode(scenario))


def test_model_hash_must_be_pinned(compiler, direct_vm):
    offer_id = compile_with(compiler, direct_vm, clone_program())
    with direct_vm.expect_revert("model_hash_mismatch"):
        compiler.quote(offer_id, "0" * 64, encode(SCENARIO_REMOTE_EXPEDITED))
    assert compiler.matches_complete_program(offer_id, "0" * 64) is False


def test_subtraction_that_makes_total_negative_fails(compiler, direct_vm):
    program = clone_program()
    program["rules"] = [
        {
            "stage": 0,
            "effect": "SUBTRACT",
            "calculation": "FIXED",
            "value_minor": 100,
            "basis_points": 0,
            "multiplier_parameter": "",
            "rounding": "NONE",
            "conditions": [],
            "source_document_ids": ["PRICING"],
        }
    ]
    offer_id = compile_with(compiler, direct_vm, program)
    model_hash = compiler.get_fee_program(offer_id)["model_hash"]
    with direct_vm.expect_revert("negative_total_for_scenario"):
        compiler.quote(offer_id, model_hash, encode(SCENARIO_REMOTE_EXPEDITED))


@pytest.mark.parametrize(
    "rounding,expected_total",
    [("FLOOR", 1501), ("HALF_UP", 1502), ("CEILING", 1502)],
)
def test_percentage_rounding_is_explicit_and_deterministic(
    compiler, direct_vm, rounding, expected_total
):
    program = clone_program()
    program["rules"] = [
        {
            "stage": 0,
            "effect": "ADD",
            "calculation": "FIXED",
            "value_minor": 1001,
            "basis_points": 0,
            "multiplier_parameter": "",
            "rounding": "NONE",
            "conditions": [],
            "source_document_ids": ["PRICING"],
        },
        {
            "stage": 1,
            "effect": "ADD",
            "calculation": "BASIS_POINTS_OF_RUNNING_TOTAL",
            "value_minor": 0,
            "basis_points": 5000,
            "multiplier_parameter": "",
            "rounding": rounding,
            "conditions": [],
            "source_document_ids": ["TERMS"],
        },
    ]
    offer_id = compile_with(compiler, direct_vm, program)
    model_hash = compiler.get_fee_program(offer_id)["model_hash"]
    quote = compiler.quote(
        offer_id,
        model_hash,
        encode(SCENARIO_REMOTE_EXPEDITED),
    )
    assert quote["total_minor"] == expected_total


@pytest.mark.parametrize(
    "mutator,reason",
    [
        (lambda p: p.update(extra=True), "fee_program_keys"),
        (lambda p: p.update(schema="v2"), "fee_program_schema"),
        (lambda p: p.update(rules="bad"), "rules_count"),
        (lambda p: p.update(uncertainty_codes=["UNKNOWN"]), "uncertainty_code"),
        (lambda p: p.update(uncertainty_codes=["AMBIGUOUS_AMOUNT", "AMBIGUOUS_AMOUNT"]), "duplicate_uncertainty_code"),
        (lambda p: p.update(rules=[], uncertainty_codes=[]), "empty_complete_program"),
    ],
)
def test_malformed_model_response_is_atomic(compiler, direct_vm, mutator, reason):
    program = clone_program()
    mutator(program)
    direct_vm.mock_llm("TCC_COMPILE_FEE_PROGRAM_V2", encode(program))
    with direct_vm.expect_revert(reason):
        compiler.compile_offer(encode(clone_offer()))
    assert compiler.get_program_count() == 0
    assert compiler.has_compilation(expected_offer_id()) is False


@pytest.mark.parametrize(
    "field,bad,reason",
    [
        ("stage", True, "rule_stage"),
        ("effect", "MULTIPLY", "rule_effect"),
        ("calculation", "FORMULA", "rule_calculation"),
        ("value_minor", -1, "rule_value_minor"),
        ("basis_points", True, "rule_basis_points"),
        ("multiplier_parameter", "unknown", "fixed_rule_shape"),
        ("rounding", "BANKERS", "rule_rounding"),
        ("source_document_ids", [], "rule_source_count"),
    ],
)
def test_rule_shape_is_strict(compiler, direct_vm, field, bad, reason):
    program = clone_program()
    program["rules"][0][field] = bad
    direct_vm.mock_llm("TCC_COMPILE_FEE_PROGRAM_V2", encode(program))
    with direct_vm.expect_revert(reason):
        compiler.compile_offer(encode(clone_offer()))


def test_protocol_exposes_safety_boundary(compiler):
    protocol = compiler.get_protocol()
    assert protocol["protocol_version"] == 2
    assert protocol["protocol_schema"] == "truecostcompiler/protocol/v2"
    assert protocol["prompt_policy"] == "truecostcompiler/exact-fee-program-output/v2"
    assert protocol["offer_schema"] == "truecostcompiler/offer/v1"
    assert protocol["program_schema"] == "truecostcompiler/fee-program/v1"
    assert protocol["candidate_validation"] == "SOURCE_GROUNDED_SUBSTANTIVE_REVIEW"
    assert protocol["input_sources_are_authenticated"] is False
    assert protocol["source_uris_are_provenance_labels_only"] is True
    assert protocol["quote_requires_complete_program"] is True
