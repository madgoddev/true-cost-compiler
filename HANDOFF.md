# Handoff

TrueCostCompiler is a standalone, contract-only GenLayer project. It contains no
frontend and has no dependency on sibling projects in this workspace.

The current source is protocol v2. It deliberately retains
`truecostcompiler/offer/v1`, `truecostcompiler/fee-program/v1`, and the `tcc1:`
content-ID derivation, while changing the protocol schema and exact-output
prompt policy to v2. Offer IDs and model-hash derivation therefore remain stable
for identical normalized offer/program content.

Do not reuse the earlier protocol-v1 StudioNet deployment as release evidence.
Its deployment finalized, but the first live compilation smoke finalized with
`[LLM_ERROR] rule_keys` and stored no program. The hardcoded temporary Studio
smoke script has been removed. The fresh protocol-v2 Studio deployment and live
compile/readback smoke are verified in `deployments/studionet.json`.

Completed gates for the frozen protocol-v2 source are:

1. lint, schema and strict type checking pass;
2. 100 direct tests and five five-validator GLSim tests pass;
3. the independent code/security/originality audit returned `GO`; and
4. the verified StudioNet record preserves the exact v2 source and does not
   substitute the diagnostic protocol-v1 address; and
5. the byte-identical Bradbury deployment and live compile/readback smoke are
   FINALIZED with AGREE and FINISHED_WITH_RETURN in
   `deployments/bradbury.json`.

The explicit-allowlist archive verification described below is complete, and
both curated deployment records are present. The distributable ZIP keeps its
SHA-256 in a sibling checksum file outside the archive.

The final ZIP must use an explicit allowlist and exclude `.git`, `.venv`,
`.tools`, caches, generated artifacts, environment files, raw receipts, logs,
wallets, keystores, keys and secrets. Keep the ZIP SHA-256 in a sibling checksum
file outside the archive.

This protocol compiles supplied public text. It does not authenticate source
provenance or guarantee a real-world price.
