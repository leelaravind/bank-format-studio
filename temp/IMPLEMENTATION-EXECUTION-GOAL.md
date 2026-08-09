# GOAL — IMPLEMENT BANK STATEMENT FORMAT STUDIO V1

You are now the implementation engineer for **Bank Statement Format Studio V1**.

The repository already contains completed Phase 0 research and an approved Phase 1 implementation plan.

## PRIMARY OBJECTIVE

Implement the complete production-ready V1 defined by:

`spec/IMPLEMENTATION-PLAN.md`

Execute milestones **P1-M0 through P1-M10**.

Do not create another implementation plan.
Do not restart product research.
Do not redesign the approved architecture.

Read all repository documentation before modifying anything, especially:

* `spec/IMPLEMENTATION-PLAN.md`
* `spec/DATA-MAPPING-RESEARCH.md`
* `spec/CSV-FORMAT-STRATEGY.md`
* `spec/FIXTURE-PLAN.md`
* `spec/GOLDEN-CASE-REQUIREMENTS.md`
* `spec/RECONCILIATION-REQUIREMENTS.md`
* `docs/SECURITY-REQUIREMENTS.md`
* V1 scope, licence, packaging, provenance and source-pack documents.

The implementation plan is the execution authority. Supporting specifications are binding unless the plan explicitly supersedes them.

## FIRST ACTION

Before product code, update `spec/FIXTURE-PLAN.md` to explicitly define the S01–S08 security fixture family promised by the implementation plan.

Include coverage for the planned XML/XXE/entity attacks, malicious schema-location behaviour, path traversal/reserved filenames, XLSX zip-bomb/archive traversal, CSV formula injection and malformed/resource-exhaustion/fuzz cases as appropriate.

Then begin P1-M0.

## IMPLEMENTATION RULES

Preserve the approved architecture:

`bfs_core` — pure conversion/domain library
`bfs_app` — PySide6 desktop GUI
`bfs_cli` — internal CLI/testing interface

All conversions must follow:

input → reader → normalized model → reconciliation → writer → output + reconciliation report + information-loss report

Never implement direct format-to-format shortcuts.

Use `decimal.Decimal` for financial arithmetic. Never use binary floating-point for monetary values.

Support the locked V1 formats only:

* MT940
* camt.053.001.02
* camt.053.001.08
* documented CSV interchange format
* XLSX export

Do not introduce BAI2, camt.052, camt.054, MT942, arbitrary-bank CSV import, cloud processing, telemetry, auto-update, or other scope expansion.

XLSX import remains outside committed V1.

## LOCKED TECHNICAL DECISIONS

Implement GATE-1 through GATE-4 exactly as resolved in the implementation plan.

In particular:

* MT940 `:61:` marks: C, D, RC, RD only.
* Preserve reversal semantics.
* Use version-neutral normalized models with thin camt .02/.08 adapters.
* Implement the approved `:28C:`/sequence/pagination behaviour.
* camt→MT940 structured `:86:` output uses the approved slash code-word convention.
* German GVC is input-side only.
* `NONREF` remains verbatim.
* CSV uses `snake_case`.
* `statements.csv` is mandatory.
* XLSX is the two-table export defined in the plan.

Do not silently substitute alternative interpretations.

## FIDELITY

Never claim or engineer fake losslessness.

Every conversion must produce an information-loss report.

Any dropped, truncated, transliterated, flattened, heuristically derived or otherwise changed information must be represented through the approved diagnostics/loss mechanism.

Silent information loss is a defect.

Generated camt output must validate against the bundled appropriate XSD.

Generated MT940 must reparse successfully and satisfy reconciliation requirements.

## RECONCILIATION

Implement INV-1 through INV-8 and E1 through E14.

Financial conservation is a release-critical invariant.

For every applicable conversion verify preservation of:

* opening balance
* closing balance
* total credits
* total debits
* transaction count
* currency semantics
* reversal semantics

Balance mismatches must never be hidden or automatically “fixed”.

## TESTING

Build the synthetic fixture suite and golden-case system defined by the specifications.

Implement approximately the planned ~45 golden cases plus required gate/security cases.

Golden tests must verify:

input → normalized model → output → reconciliation → diagnostics/loss report.

Expected outputs must be deterministic.

Use a pinned/injected clock where timestamps would otherwise make outputs nondeterministic.

Every INV-1..8, E1..E14 and SEC-01..24 must have its planned verification.

Do not mark a milestone complete merely because code compiles.

Run relevant tests after each milestone and the complete suite at integration boundaries.

If a test exposes a specification/implementation conflict, investigate the root cause. Do not weaken the test simply to obtain green CI.

## SECURITY

Implement SEC-01 through SEC-24.

Core conversion must operate completely offline.

No telemetry, analytics, crash reporting, remote schemas or document-data network transmission.

Use hardened XML processing.

Reject dangerous DTD/entity/network-resolution behaviour.

Implement file-size/resource protections, path containment, Windows reserved-name handling, safe temporary-file behaviour, CSV formula-injection protection and PII-safe logging.

Run the complete conversion suite under the planned socket-blocking harness.

Bank-statement contents must never be transmitted externally.

## DEPENDENCIES & LICENSING

Use only dependencies approved by the repository's licence research unless a replacement is strictly necessary.

Pin dependencies appropriately.

Preserve LGPL obligations and THIRD-PARTY-NOTICES requirements.

CI must include the planned dependency/licence gates.

Do not introduce GPL/AGPL dependencies into the distributed application.

If a new dependency is genuinely necessary, stop that specific change, document the reason/licence and prefer an already-approved or permissively licensed alternative.

## GUI

Implement the approved PySide6 desktop workflow only after the core is proven:

Open → detect/validate → preview → choose target → convert → reconciliation/loss results → save.

The GUI must remain thin. Business/conversion logic belongs in `bfs_core`.

Errors must be understandable to a normal user while preserving stable diagnostic codes internally.

Do not expose unnecessary technical complexity in the primary workflow.

## PACKAGING

Produce the planned Windows distribution using PyInstaller `--onedir` and Inno Setup.

The installed application must function offline on the targeted Windows environments.

Complete required licence notices and packaging assets.

Code-signing infrastructure may be prepared as a hook if owner credentials/certificate are unavailable. Do not fabricate signing success.

Likewise, do not fabricate VirusTotal, Lemon Squeezy or Gumroad results that require owner/external actions.

Record those as explicit OWNER ACTIONS where necessary.

## EXECUTION METHOD

Work milestone-by-milestone:

P1-M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9 → M10.

At each milestone:

1. implement the milestone;
2. run its tests/verification;
3. fix failures;
4. verify exit criteria;
5. commit the completed milestone with a clear Git message;
6. continue automatically to the next milestone.

Do not wait for approval between milestones unless genuinely blocked by something only the owner can provide.

Use subagents/parallel work where useful, but maintain one coherent architecture and review all integrated output.

Do not push broken intermediate states.

## SOURCE INTEGRITY

Never modify evidence, fixtures or expected results merely to make faulty implementation pass.

Public/reference assets must retain provenance.

Synthetic data must remain clearly synthetic.

Do not introduce real customer financial data.

Do not invent unsupported financial-format semantics.

Where the specification intentionally requires warnings or information-loss notes, preserve them.

## QUALITY BAR

This is a commercial desktop product, not a prototype.

Before completion:

* remove dead/debug code;
* run formatting/lint/type checks;
* run unit tests;
* run integration tests;
* run golden tests;
* run security tests;
* validate generated camt against XSDs;
* reparse generated MT940;
* test deterministic outputs;
* verify reconciliation;
* verify offline operation;
* audit dependencies/licences;
* build the Windows application/installer where the environment permits;
* perform available smoke tests.

Do not declare success with knowingly failing tests.

## GIT

Commit milestone work logically.

Do not rewrite existing repository history.

Do not force-push.

Push completed implementation to the configured remote only after the repository is in a coherent tested state.

## FINAL DELIVERABLE

When P1-M0 through P1-M10 are complete, create:

`IMPLEMENTATION-COMPLETION-REPORT.md`

Include:

* implementation summary;
* final architecture;
* milestone status M0–M10;
* files/modules created;
* supported formats/features;
* test counts and exact results;
* golden-case results;
* INV-1..8 status;
* E1..E14 status;
* SEC-01..24 status;
* dependency/licence audit result;
* packaging/build result;
* known limitations;
* information-loss behaviour;
* deviations from the approved plan, with reasons;
* unresolved defects;
* owner actions still required;
* Git commits created;
* final commit hash;
* whether remote push succeeded;
* exact commands needed to run tests, application and build.

Clearly distinguish:

**COMPLETE**
**PARTIAL**
**BLOCKED — OWNER ACTION REQUIRED**
**NOT IMPLEMENTED**

Never report something as tested if it was only inspected.

## COMPLETION CONDITION

The task is complete only when the implementation, automated verification, documentation and locally achievable packaging work defined by the approved plan have been executed.

External owner-only operations such as purchasing/providing a code-signing certificate, marketplace publication or other credentials must not block completion of engineering work.

Proceed now.

Start by reading the repository and approved specifications, add S01–S08 to the fixture plan, then execute P1-M0 through P1-M10 continuously.
