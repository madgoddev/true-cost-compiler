from __future__ import annotations

import copy
import json
from pathlib import Path

from gltest import get_contract_factory, get_validator_factory
from gltest.assertions import tx_execution_failed, tx_execution_succeeded
from gltest.types import TransactionStatus
from gltest.utils import extract_contract_address

from fixtures.fee_program_cases import (
    APPROVAL,
    SCENARIO_REMOTE_EXPEDITED,
    clone_offer,
    clone_program,
    encode,
    expected_offer_id,
)


CONTRACT_FILE = Path(__file__).resolve().parents[2] / "contracts" / "true_cost_compiler.py"


def pretty(receipt) -> str:
    return json.dumps(receipt, indent=2, sort_keys=True, default=str)


def context(program, timestamp: str, review=APPROVAL):
    replies = {
        "TCC_COMPILE_FEE_PROGRAM_V2": encode(program),
        "TCC_REVIEW_FEE_PROGRAM_V2": encode(review),
    }
    validators = get_validator_factory().batch_create_mock_validators(
        5,
        mock_llm_response={"nondet_exec_prompt": replies},
    )
    return {
        "validators": [validator.to_dict() for validator in validators],
        "genvm_datetime": timestamp,
    }


def assert_five(receipt, vote: str) -> None:
    votes = receipt.get("consensus_data", {}).get("votes", {})
    assert isinstance(votes, dict), pretty(receipt)
    assert len(votes) == 5, pretty(receipt)
    assert set(votes.values()) == {vote}, pretty(receipt)


def deploy():
    factory = get_contract_factory(contract_file_path=CONTRACT_FILE)
    receipt = factory.deploy_contract_tx(
        args=[],
        wait_transaction_status=TransactionStatus.FINALIZED,
    )
    assert tx_execution_succeeded(receipt), pretty(receipt)
    assert_five(receipt, "agree")
    return factory.build_contract(extract_contract_address(receipt))


def write_program(contract, offer, program, timestamp):
    return contract.compile_offer(args=[encode(offer)]).transact(
        transaction_context=context(program, timestamp),
        wait_transaction_status=TransactionStatus.FINALIZED,
    )


def test_complete_program_persists_and_executes_quote_with_five_votes():
    contract = deploy()
    receipt = write_program(
        contract,
        clone_offer(),
        clone_program(),
        "2026-08-12T11:00:00Z",
    )
    assert tx_execution_succeeded(receipt), pretty(receipt)
    assert_five(receipt, "agree")
    offer_id = contract.preview_offer_id(args=[encode(clone_offer())]).call()
    assert offer_id == expected_offer_id()
    model = contract.get_fee_program(args=[offer_id]).call()
    assert model["complete"] is True
    quote = contract.quote(
        args=[offer_id, model["model_hash"], encode(SCENARIO_REMOTE_EXPEDITED)]
    ).call()
    assert quote["total_minor"] == 4620
    assert contract.matches_complete_program(
        args=[offer_id, model["model_hash"]]
    ).call() is True


def test_incomplete_program_persists_as_nonquotable_with_five_votes():
    contract = deploy()
    receipt = write_program(
        contract,
        clone_offer(),
        clone_program(False),
        "2026-08-12T11:10:00Z",
    )
    assert tx_execution_succeeded(receipt), pretty(receipt)
    assert_five(receipt, "agree")
    offer_id = expected_offer_id()
    model = contract.get_fee_program(args=[offer_id]).call()
    assert model["complete"] is False
    assert model["uncertainty_codes"] == ["UNSUPPORTED_FORMULA"]
    assert contract.matches_complete_program(
        args=[offer_id, model["model_hash"]]
    ).call() is False


def test_cache_hit_does_not_add_a_second_record_or_require_llm():
    contract = deploy()
    first = write_program(
        contract,
        clone_offer(),
        clone_program(),
        "2026-08-12T11:20:00Z",
    )
    assert tx_execution_succeeded(first), pretty(first)
    assert_five(first, "agree")
    offer = clone_offer()
    offer["source_documents"].reverse()
    offer["parameters"].reverse()
    cached = contract.compile_offer(args=[json.dumps(offer, indent=2)]).transact(
        wait_transaction_status=TransactionStatus.FINALIZED,
    )
    assert tx_execution_succeeded(cached), pretty(cached)
    assert_five(cached, "agree")
    assert contract.get_program_count().call() == 1
    assert contract.get_program_id(args=[0]).call() == expected_offer_id()


def test_invalid_model_execution_fails_atomically_for_all_validators():
    contract = deploy()
    invalid = clone_program()
    invalid["rules"][0]["value_minor"] = -1
    receipt = write_program(
        contract,
        clone_offer(),
        invalid,
        "2026-08-12T11:30:00Z",
    )
    assert tx_execution_failed(receipt), pretty(receipt)
    assert_five(receipt, "agree")
    assert contract.get_program_count().call() == 0
    assert contract.has_compilation(args=[expected_offer_id()]).call() is False


def test_unknown_uncertainty_code_fails_without_allocating_state():
    contract = deploy()
    invalid = clone_program()
    invalid["uncertainty_codes"] = ["MODEL_SAYS_MAYBE"]
    receipt = write_program(
        contract,
        clone_offer(),
        invalid,
        "2026-08-12T11:40:00Z",
    )
    assert tx_execution_failed(receipt), pretty(receipt)
    assert_five(receipt, "agree")
    assert contract.get_program_count().call() == 0
