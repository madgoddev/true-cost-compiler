# Security and audit notes

## Controls

- Concrete GenVM dependency pinned on line one.
- No caller-controlled web request or SSRF surface.
- Duplicate JSON keys and nonfinite numeric constants rejected for offer input.
- Exact object keys, exact scalar types, bounded UTF-8 sizes, bounded arrays and
  closed enums throughout the public and model boundaries.
- Protocol v2 supplies a complete valid program template, complete templates
  for every supported calculation, and typed condition templates. It explicitly
  requires calculation-specific zero, empty-string and `NONE` fields and bans
  missing or extra keys.
- Model output is never auto-repaired. A malformed rule remains an
  `[LLM_ERROR]` and the transaction writes no state.
- Python booleans never satisfy integer fields.
- Untrusted source text is isolated between explicit prompt delimiters and the
  warning is repeated after each block.
- Validator review is grounded in the complete offer and checks semantic
  faithfulness, conservative handling, material coverage and condition logic.
- Model errors never become consensus-approved stored state.
- State is written only after `run_nondet_unsafe` returns an accepted program.
- Stored snapshots and programs are re-normalized, re-canonicalized and
  content-ID checked on every material read.
- Incomplete programs cannot quote or satisfy the downstream checkpoint gate.
- Quote arithmetic is bounded and rejects negative totals.
- Percentage rounding is an explicit reviewed rule field; an unstated material
  rounding policy must keep the program incomplete.

## Test evidence

Verification on the protocol-v2 frozen contract candidate with SHA-256
`5AAC8F139F8B64D2400A0369B244F775B062F96F84665D66FA67269FD0C61845`
and size 34,622 bytes:

- GenVM lint and SDK validation: pass;
- ABI schema extraction: pass, 10 methods, 9 views, 1 write, 0 constructor
  parameters;
- strict type check: zero diagnostics;
- direct suite: 100 passed;
- five-validator GLSim suite: 5 passed; and
- combined: 105 passed.

GLSim 0.29.2 shares the first validator's static mocks across the simulated
validator set. It proves five-vote execution, storage, cache and fail-closed
behavior under a common model response, but it cannot honestly simulate
heterogeneous 3/5 responses. Captured direct-validator tests separately cover
false review dimensions, malformed review output, forged leaders, leader
errors, the exact v2 prompt templates, every missing rule field,
representative extra rule fields, and missing or extra condition fields.

## Closed Studio liveness finding

The protocol-v1 candidate finalized a StudioNet deployment, but its first live
write smoke failed with `[LLM_ERROR] rule_keys`; no program was stored and the
program count remained zero. Strict rejection prevented malformed state, but
the prompt did not make calculation-specific unused fields concrete enough for
the live model. Protocol v2 replaces that prompt policy with complete exact
templates and a final key-by-key self-check. A fresh protocol-v2 StudioNet
deployment and live compilation now pass exact source, schema, program,
checkpoint, and quote readback; see `deployments/studionet.json`. The old
deployed address and source hash remain diagnostic, not release evidence.
The byte-identical protocol-v2 deployment and live compilation also pass on
Bradbury with FINALIZED, unanimous AGREE, FINISHED_WITH_RETURN, and independent
program/checkpoint/quote readback; see `deployments/bradbury.json`.

## Residual risks

1. **Source authenticity:** URI, retrieval time, currency and source text are
   caller-supplied public claims. The contract does not authenticate them.
2. **Correlated model failure:** validators can share a mistaken interpretation
   or follow sophisticated prompt injection despite the controls.
3. **Completeness is bounded:** protocol/prompt policy v2 still supports only
   the unchanged fee-program-v1 grammar. Complex caps, tiers, external indexes
   and formulas must be marked unresolved.
4. **Pricing and legal drift:** an immutable program can become stale whenever
   an offer or applicable law changes. Changed evidence must produce a new ID.
5. **Public disclosure:** terms and scenario schemas are public chain plaintext.
   Do not submit credentials, private quotes, personal data, confidential
   discounts or authenticated URLs.
6. **Storage spam:** compilation is permissionless and the catalogue is
   append-only. Network fees are the primary economic control.
7. **Model and review liveness:** exact output templates reduce malformed-rule
   failures but cannot guarantee that every model follows them. Strict parsing
   will continue to fail closed. Exact conservative review can also fail
   consensus when terms are genuinely ambiguous; retrying does not turn
   ambiguity into certainty.
8. **Not a settlement oracle:** the program cannot prove what a merchant charged
   or decide entitlement, refunds, taxes or damages.

Consequential consumers must not auto-release substantial value from this
primitive without independent controls and human review.
