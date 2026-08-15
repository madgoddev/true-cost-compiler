# TrueCostCompiler

TrueCostCompiler is a reusable, contract-only GenLayer Intelligent Contract that
turns a bounded bundle of public offer terms into a deterministic fee program.
Other contracts can pin the resulting model hash and calculate a scenario's
amount without asking an LLM again.

It answers a narrow question:

> Which mandatory charges and discounts are stated in this supplied offer, and
> can they be represented safely by the published v1 fee grammar?

It does **not** authenticate a source, crawl a URL, guarantee that a merchant
will honor a price, decide a billing dispute, or provide legal, tax, or financial
advice. Source URIs are provenance labels only. All submitted text and pricing
logic become public chain data and are disclosed to validators.

## Why this needs GenLayer

Pricing terms are commonly split across prose, tables, footnotes, conditions,
and exceptions. A deterministic parser cannot safely infer that `$2.50 per km`
is mandatory, that a regional fee applies only to one enum value, or that a
percentage must be applied after other charges.

During `compile_offer`, the leader proposes a closed, executable fee program.
Protocol v2 gives the model complete JSON templates for the program, all three
calculation-specific rule shapes, and integer, enum and boolean conditions. It
requires every rule to retain all nine fields, including the zero and empty
fields that are unused by a particular calculation. The deterministic parser
still rejects every missing or extra key rather than repairing model output.
Each validator receives the complete offer and proposed program, then performs
a substantive review of:

- whether every encoded amount, effect, formula, condition and citation is
  supported;
- whether nothing material was invented;
- whether every mandatory pricing term is either represented or conservatively
  marked unresolved; and
- whether ordering and condition logic preserve the supplied terms.

The validator is not allowed to approve a result merely because it has valid
JSON. Storage is written only after consensus.

## Distinct output primitive

The result is an executable fee program, not a `VERIFIED/FAILED` verdict, a
document-difference report, a dispute judgment, or a provider-status journal.

```text
Supplied public terms
        |
        v
GenLayer semantic compilation + substantive validator review
        |
        v
Immutable fee program + model hash
        |
        v
Deterministic quote for a bounded scenario
```

## Supported fee grammar

Each offer explicitly declares a currency and `minor_unit_exponent` (`2` means
cents for the synthetic USD example). Each rule has an `ADD` or `SUBTRACT`
effect and one calculation:

- `FIXED`
- `PER_INTEGER_PARAMETER`
- `BASIS_POINTS_OF_RUNNING_TOTAL`

Conditions are conjunctions over declared integer, enum, or boolean scenario
parameters. Rules execute in ascending `stage`; ties use canonical rule order.
The program operates in the offer's explicitly declared minor currency unit.
Fixed and per-parameter rules use `NONE` rounding. A percentage rule must encode
`FLOOR`, `HALF_UP`, or `CEILING`, and validators must find that policy in the
supplied terms. If rounding is material but unstated, the model must remain
incomplete with `AMBIGUOUS_AMOUNT` rather than silently choosing a convention.

If a material term cannot be represented safely, the program records one or
more closed uncertainty codes:

- `AMBIGUOUS_AMOUNT`
- `AMBIGUOUS_CONDITION`
- `CONFLICTING_SOURCE_TERMS`
- `HOSTILE_SOURCE_INSTRUCTION`
- `MANDATORY_CHARGE_UNMAPPED`
- `SCENARIO_PARAMETER_MISSING`
- `TAX_TREATMENT_UNCLEAR`
- `UNSUPPORTED_FORMULA`

An incomplete program remains inspectable, but `quote` reverts and
`matches_complete_program` returns `false`.

## Core ABI

The contract has no constructor parameters and exposes one write method:

```text
compile_offer(offer_json) -> offer_id
```

Its nine views are:

```text
preview_offer_id(offer_json) -> offer_id
has_compilation(offer_id) -> bool
get_offer(offer_id) -> object
get_fee_program(offer_id) -> object
quote(offer_id, expected_model_hash, scenario_json) -> object
matches_complete_program(offer_id, expected_model_hash) -> bool
get_program_count() -> int
get_program_id(index) -> offer_id
get_protocol() -> object
```

`quote` requires the expected model hash so a downstream consumer explicitly
binds itself to the reviewed program.

## Input example

See [examples/metrobox-offer.json](examples/metrobox-offer.json). Its declared
parameters are `distance_km`, `region`, and `expedited`. The example is synthetic
and does not describe a real merchant.

## Development

The contract pins a concrete GenVM runner on its first line.

```powershell
python -m pip install -r requirements.txt
genvm-lint check contracts\true_cost_compiler.py --json
genvm-lint schema contracts\true_cost_compiler.py --json
genvm-lint typecheck contracts\true_cost_compiler.py --strict --json
python -m pytest tests\direct -q
```

For the five-validator simulator, start GLSim in one terminal:

```powershell
python tests\start_sim.py --port 4000 --validators 5
```

Then run:

```powershell
python -m pytest tests\integration\test_truecost_five_validators.py -v -s
```

Stop the simulator after the run.

## Verification status

Protocol v2 is verified on StudioNet at
`0x07694E36773892d1FDd24C5F11d02Db61b4D6135`. Its deployment and live
`compile_offer` smoke are FINALIZED with MAJORITY_AGREE and successful leader
execution. Readback contains the expected content ID, a complete four-rule
program, zero uncertainty, a passing checkpoint gate, and a sample quote of
5,170 minor units. The deployed 34,622 bytes are byte-identical to the frozen
source. See [`deployments/studionet.json`](deployments/studionet.json).

The same frozen protocol-v2 source is also verified on Bradbury at
`0x2b9a96ff4C88a93C76143699EEd66C38e5748Cee`. Its deployment and live
`compile_offer` smoke are FINALIZED with unanimous AGREE votes and
FINISHED_WITH_RETURN execution. Independent readback reproduced the expected
offer ID, a complete four-rule program, zero uncertainty, the passing checkpoint
gate, and the same 5,170-minor-unit quote. See
[`deployments/bradbury.json`](deployments/bradbury.json).

The earlier protocol-v1 StudioNet deployment remains a fail-closed diagnostic
only: its smoke returned `[LLM_ERROR] rule_keys` and stored zero programs.
Lifecycle finality alone is never treated as successful execution.

## Consumer warning

A complete model means validators supported the bounded compilation under
protocol/prompt policy v2 using the unchanged offer-v1 and fee-program-v1
grammars. It is not proof that the supplied text is authentic, exhaustive,
current, legally enforceable, or commercially honored. Consequential systems
should retain human review and should bind the network, contract address,
protocol version, prompt policy, offer ID, model hash, and finalized transaction
state.
