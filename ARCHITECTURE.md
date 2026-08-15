# Architecture

## Trust boundary

The caller supplies a strict JSON offer containing public text, provenance
labels, a currency code plus minor-unit exponent, and a bounded scenario-parameter schema. The contract
does not dereference the supplied URIs and does not authenticate them.

GenLayer owns the semantic state transition: compiling supported pricing terms
into a closed fee grammar and obtaining substantive validator support before
committing the immutable program.

## State model

An offer ID is:

```text
tcc1:sha256("truecostcompiler/offer/v1" + NUL + canonical_offer_json)
```

The ID is global within the protocol and independent of the caller. Equivalent
JSON ordering produces the same ID. Changed text, parameters, provenance labels,
or retrieval labels produce a different ID.

State is split into:

- canonical source snapshots;
- canonical fee programs;
- compilation timestamps; and
- an indexed program catalogue.

The single write is atomic. A failed model response, invalid candidate, validator
rejection, or execution failure cannot allocate a partial record. Repeating an
existing canonical offer revalidates stored coherence and returns the cached ID
without another LLM call.

## Consensus boundary

The leader's proposed model is normalized into closed enums, bounded integers,
declared parameters, canonical conditions, and supplied document IDs. A
validator then reviews the candidate against the entire canonical offer using
four substantive criteria. All four exact booleans must be true.

The validator sees the offer, not only the leader output. Model errors and
unknown errors force disagreement. The candidate is copied through canonical
JSON before storage so later metadata cannot mutate the captured consensus
object by reference.

## Deterministic execution

`quote` performs no nondeterministic work. It:

1. reloads and revalidates the stored offer and program;
2. checks the caller's expected model hash;
3. rejects every program containing an uncertainty code;
4. validates an exact scenario against all declared parameters; and
5. evaluates sorted rules with bounded integer arithmetic.

Percentage calculations apply the source-supported `FLOOR`, `HALF_UP`, or
`CEILING` rule explicitly. Negative or oversized totals fail instead of being
silently clamped.

## Versioning

The offer schema, fee-program schema, ID namespace, calculation grammar and
uncertainty taxonomy remain fixed at v1. Protocol v2 changes only the consensus
prompt policy: it gives the leader complete exact JSON templates and requires
all unused rule fields explicitly. Consequently, `tcc1:` offer IDs and v1 model
hashes remain stable for identical canonical content. A future semantic or fee
grammar change requires a new offer/program schema and a new contract. Existing
records are immutable snapshots.
