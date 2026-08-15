from __future__ import annotations

import copy
import json

import pytest

from fixtures.fee_program_cases import clone_offer, encode, expected_offer_id


def test_preview_is_content_addressed_and_canonical(compiler):
    first = clone_offer()
    second = clone_offer()
    second["parameters"].reverse()
    second["source_documents"].reverse()
    second["parameters"][0]["values"] = list(reversed(second["parameters"][0]["values"]))
    assert compiler.preview_offer_id(encode(first)) == expected_offer_id()
    assert compiler.preview_offer_id(encode(second)) == expected_offer_id()


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda value: value.update(schema="wrong"), "unsupported_offer_schema"),
        (lambda value: value.update(currency="usd"), "currency_format"),
        (lambda value: value.update(currency="USDD"), "currency_format"),
        (lambda value: value.update(minor_unit_exponent=True), "minor_unit_exponent"),
        (lambda value: value.update(minor_unit_exponent=-1), "minor_unit_exponent"),
        (lambda value: value.update(minor_unit_exponent=7), "minor_unit_exponent"),
        (lambda value: value.update(offer_name=""), "offer_name_length"),
        (lambda value: value.update(source_documents=[]), "source_documents_count"),
        (lambda value: value.update(source_documents="not-list"), "source_documents_count"),
        (lambda value: value.update(parameters="not-list"), "parameters_count"),
        (lambda value: value.update(parameters=[True]), "parameter_must_be_object"),
    ],
)
def test_top_level_shape_rejects_before_consensus(compiler, direct_vm, mutation, reason):
    offer = clone_offer()
    mutation(offer)
    with direct_vm.expect_revert(reason):
        compiler.preview_offer_id(encode(offer))
    assert len(direct_vm._captured_validators) == 0


def test_duplicate_json_key_is_rejected(compiler, direct_vm):
    raw = encode(clone_offer())
    raw = raw[:-1] + ',"currency":"EUR"}'
    with direct_vm.expect_revert("invalid_json"):
        compiler.preview_offer_id(raw)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_json_number_is_rejected(compiler, direct_vm, constant):
    raw = encode(clone_offer()).replace('"minimum":0', '"minimum":' + constant, 1)
    with direct_vm.expect_revert("invalid_json"):
        compiler.preview_offer_id(raw)


@pytest.mark.parametrize(
    "field,bad_value,reason",
    [
        ("id", "bad-id", "document_id_format"),
        ("id", "A/B", "document_id_format"),
        ("uri", "http://example.test", "document_uri_must_be_https"),
        ("uri", "https://user@example.test/x", "document_uri_authority"),
        ("retrieved_at", "today", "retrieved_at_length"),
        ("text", "", "document_text_length"),
        ("text", "bad\x00text", "document_text_contains_control"),
    ],
)
def test_document_boundary(compiler, direct_vm, field, bad_value, reason):
    offer = clone_offer()
    offer["source_documents"][0][field] = bad_value
    with direct_vm.expect_revert(reason):
        compiler.preview_offer_id(encode(offer))


def test_duplicate_document_ids_reject(compiler, direct_vm):
    offer = clone_offer()
    offer["source_documents"][1]["id"] = offer["source_documents"][0]["id"]
    with direct_vm.expect_revert("duplicate_document_id"):
        compiler.preview_offer_id(encode(offer))


@pytest.mark.parametrize(
    "kind,minimum,maximum,values,reason",
    [
        ("INTEGER", True, 5, [], "parameter_bounds_type"),
        ("INTEGER", -1, 5, [], "integer_parameter_bounds"),
        ("INTEGER", 6, 5, [], "integer_parameter_bounds"),
        ("INTEGER", 0, 5, ["x"], "integer_parameter_values_must_be_empty"),
        ("ENUM", 1, 0, ["x"], "enum_parameter_bounds_must_be_zero"),
        ("ENUM", 0, 0, [], "enum_parameter_values_count"),
        ("ENUM", 0, 0, ["x", "x"], "duplicate_enum_value"),
        ("BOOLEAN", 0, 0, [], "boolean_parameter_shape"),
        ("FLOAT", 0, 1, [], "parameter_kind"),
    ],
)
def test_parameter_kind_invariants(
    compiler, direct_vm, kind, minimum, maximum, values, reason
):
    offer = clone_offer()
    parameter = offer["parameters"][0]
    parameter.update(kind=kind, minimum=minimum, maximum=maximum, values=values)
    with direct_vm.expect_revert(reason):
        compiler.preview_offer_id(encode(offer))


def test_duplicate_parameter_names_reject(compiler, direct_vm):
    offer = clone_offer()
    offer["parameters"][1]["name"] = offer["parameters"][0]["name"]
    with direct_vm.expect_revert("duplicate_parameter_name"):
        compiler.preview_offer_id(encode(offer))


def test_unknown_extra_fields_are_rejected_at_every_level(compiler, direct_vm):
    cases = []
    top = clone_offer()
    top["extra"] = 1
    cases.append(top)
    document = clone_offer()
    document["source_documents"][0]["extra"] = 1
    cases.append(document)
    parameter = clone_offer()
    parameter["parameters"][0]["extra"] = 1
    cases.append(parameter)
    for case in cases:
        with direct_vm.expect_revert("_keys"):
            compiler.preview_offer_id(encode(case))


def test_raw_size_cap_rejects_without_llm(compiler, direct_vm):
    offer = clone_offer()
    offer["source_documents"][0]["text"] = "x" * 15_500
    raw = json.dumps(offer)
    with direct_vm.expect_revert("offer_json_too_large"):
        compiler.compile_offer(raw)
    assert len(direct_vm._captured_validators) == 0


def test_missing_and_invalid_ids_fail_closed(compiler, direct_vm):
    assert compiler.has_compilation("not-an-id") is False
    assert compiler.has_compilation("tcc1:" + "0" * 64) is False
    with direct_vm.expect_revert("compilation_not_found"):
        compiler.get_offer("tcc1:" + "0" * 64)
    with direct_vm.expect_revert("program_index_out_of_bounds"):
        compiler.get_program_id(0)
