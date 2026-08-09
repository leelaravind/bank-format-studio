# BANK STATEMENT FORMAT STUDIO V1
# ENGINEERING REMEDIATION — RELEASE BLOCKERS

## OBJECTIVE

Bank Statement Format Studio V1 has completed implementation and an independent release audit.

The audit verdict was:

AMBER — ENGINEERING READY, RELEASE ACTIONS/FIXES REQUIRED.

Your task is to fix the confirmed engineering defects and high-priority correctness/security/release-quality findings required to reach engineering GREEN.

This is a TARGETED REMEDIATION.

Do NOT redesign the architecture.
Do NOT restart research.
Do NOT expand V1 scope.
Do NOT add new product features.
Do NOT configure Gumroad/Lemon Squeezy.
Do NOT purchase/fabricate signing certificates.
Do NOT perform owner-only actions.

Read first:

1. `temp/FINAL-RELEASE-AUDIT.md`
2. `spec/IMPLEMENTATION-PLAN.md`
3. `IMPLEMENTATION-COMPLETION-REPORT.md`
4. relevant Phase 0/1 specifications
5. affected source/tests

Treat the independent audit as the remediation backlog.

Existing passing tests are regression requirements, not permission to preserve defective behaviour.

---

# PRIORITY 1 — FIX RELEASE-BLOCKING ENGINEERING DEFECTS

## B-1 — MT940 LONG REFERENCE LOSS / FALSE LOSS NOTE

Audit confirmed that MT940 writer truncation reporting can claim:

full value preserved in `:86:`

when the complete value is not actually emitted.

Fix the reference spill design.

Requirements:

- no reference may silently disappear;
- never claim preservation unless the full original information is actually represented;
- handle multiple overflowing references;
- handle coexistence with EndToEndId;
- preserve deterministic `:86:` generation;
- respect MT940 line/field constraints;
- if preservation is impossible, emit an accurate information-loss diagnostic;
- diagnostic must distinguish PRESERVED/DERIVED/TRUNCATED/DROPPED appropriately.

Add regression tests for:

- long customer reference;
- long bank reference;
- both long simultaneously;
- long references + EndToEndId;
- multiple spill values;
- round-trip behaviour;
- accurate loss-note text.

Never solve this by simply deleting the loss report.

---

## B-2 — DUPLICATE STATEMENT IDs IN CSV

Current CSV reconstruction assumes `statement_id` is globally unique.

Real bank data disproves that assumption.

Fix CSV serialization/reconstruction so multiple statements sharing the same statement ID remain distinct.

Requirements:

- do not overwrite statements;
- preserve original statement_id;
- deterministic grouping;
- transaction rows must map unambiguously to the correct statement occurrence;
- round-trip must preserve statement count/order and conservation keys;
- existing CSV dialect should remain compatible where safely possible;
- if dialect change is necessary, version/document it explicitly;
- avoid exposing an internal implementation identifier as if it were a bank identifier.

Use the real/public duplicate-ID scenario identified by the audit as a regression fixture where licensing permits, plus synthetic coverage.

Add tests for:

- two identical statement IDs;
- many identical IDs;
- identical IDs across different accounts;
- duplicate IDs with different dates/sequences;
- CSV round trip;
- CSV → camt;
- CSV → MT940;
- malformed/ambiguous CSV identity data.

No E_INTERNAL should be produced for valid duplicate-ID input.

---

## B-3 — FABRICATED CAMT DATE

Remove the silent:

`1970-01-01`

fallback for entries lacking both value date and booking date.

A missing date must never become fabricated financial data.

Determine the correct behaviour from the locked model/specification.

Preferred rule:

- use genuine value date when present;
- otherwise genuine booking date where the approved mapping allows it;
- if neither exists and the normalized model requires a date, produce a stable explicit diagnostic/error rather than inventing one.

Do not use current date, Unix epoch, creation date or any other invented date unless the specification explicitly authorizes it.

Add regression tests proving:

- ValDt only;
- BookgDt only;
- both;
- neither;
- no 1970/2070 artefact can escape;
- camt→MT940 behaviour is explicit and deterministic.

---

# PRIORITY 2 — HIGH-PRIORITY CORRECTNESS/FIDELITY FIXES

Work through every C-series engineering finding in `temp/FINAL-RELEASE-AUDIT.md`.

Do not limit remediation to the summaries below if the audit contains additional concrete findings.

## CAMT .02 BATCH DETAIL DIRECTION

The audit found `.02` batch-detail debit/credit direction can be lost.

Fix or accurately report the structural limitation.

If `.02` cannot represent per-detail direction:

- never imply that it can;
- emit explicit information-loss diagnostics;
- ensure aggregate arithmetic remains correct;
- prevent silent sign corruption.

Add mixed credit/debit detail tests.

---

## SILENT FIELD LOSS / TRUNCATION SWEEP

Audit every writer and reader for:

- `[:N]` truncation;
- omitted optional fields;
- character-set transliteration;
- merged fields;
- flattened structures;
- fallback/derived values;
- dropped references;
- dropped parties/accounts;
- dropped remittance;
- dropped additional information.

Every material representational loss must either:

1. be preserved elsewhere and truthfully documented;
2. generate an appropriate information-loss diagnostic; or
3. fail explicitly when safe conversion is impossible.

Do not flood users with meaningless diagnostics for implementation-internal formatting. Focus on actual source-information fidelity.

Add targeted regression tests.

---

## MT940 AMOUNT CONSTRAINT

Enforce the verified MT940 amount representation/length constraint.

Do not generate syntactically invalid MT940 for an oversized amount.

Use a stable error/diagnostic consistent with the error model.

Add boundary tests:

- maximum valid amount;
- one character/precision beyond;
- decimal variants;
- negative/debit semantics;
- reparse of valid boundary output.

---

# PRIORITY 3 — SECURITY / VERIFICATION CORRECTIONS

## PII REDACTION

Strengthen account/IBAN masking.

Current word-boundary-based matching can miss account-like values embedded in surrounding text.

Requirements:

- preserve useful masked prefix/suffix where appropriate;
- mask embedded IBAN/account-number patterns;
- avoid obvious false-negative cases;
- avoid destructive over-redaction where practical.

Add adversarial tests for:

- standalone IBAN;
- embedded IBAN;
- punctuation;
- JSON/log-like strings;
- long account number embedded in text;
- lowercase/mixed input if relevant;
- multiple values in one log line.

Existing PII-safe logging guarantees must continue to pass.

---

## XLSX CONSERVATION CLAIM

Do not return `conservation_verified=True` merely because XLSX is built from a CSV projection.

Either:

A. implement meaningful verification of the generated workbook/projection;

or

B. represent XLSX conservation status honestly without claiming verification that did not occur.

Prefer actual verification if it can be implemented cleanly without adding XLSX import as a product feature.

Internal verification code does NOT make XLSX import a customer-facing V1 feature.

Add tests that would fail if workbook values diverged from the normalized statements.

---

# PRIORITY 4 — RELEASE-QUALITY ENGINEERING FINDINGS

Resolve applicable high-priority findings from the audit, including:

- customer-facing CSV dialect documentation;
- stale README statements;
- undeclared test/build dependencies;
- build dependency pinning/reproducibility;
- untested CSV error branches;
- dead/unreachable error code where appropriate;
- THIRD-PARTY-NOTICES accuracy;
- distinction between tools used to build the product and components actually distributed.

Do not remove legally required notices.

Do not make legal conclusions beyond repository evidence.

For ambiguous licence matters, document:

OWNER/LEGAL REVIEW REQUIRED.

---

# CI

Audit and correct `ci/github-workflow-ci.yml` where necessary.

Ensure it reflects the real local quality gates:

- dependency installation;
- lint;
- tests;
- warnings-as-errors where appropriate;
- security suite;
- golden tests;
- licence gate.

If credentials still prevent installing the workflow under `.github/workflows`, leave the owner action clearly documented.

Do not bypass GitHub permissions.

---

# TESTING REQUIREMENTS

For every fixed finding:

1. create a regression test that fails against the old behaviour;
2. implement the correction;
3. demonstrate the regression test passes;
4. run the relevant subsystem suite.

Then run the complete suite.

Existing 205 tests must remain regression coverage.

The final total should therefore be GREATER than 205 unless a test is legitimately consolidated/replaced and explicitly justified.

Run at minimum:

- full pytest suite;
- warnings-as-errors verification;
- ruff;
- golden tests;
- security tests;
- licence gate;
- independent spot conversions;
- XSD validation;
- MT940 output reparse;
- conservation checks.

Never modify a golden expected result merely because implementation changed.

A golden change requires a documented specification/fidelity reason.

---

# INDEPENDENT REGRESSION PROBES

After fixes, perform new cases not copied directly from existing tests.

At minimum probe:

1. long customer + bank references together;
2. duplicate statement IDs;
3. missing camt dates;
4. `.02` mixed-direction batch details;
5. oversized MT940 amount;
6. embedded account number in a log message;
7. XLSX conservation tamper/difference detection.

Record results.

---

# REQUIREMENT TRACEABILITY

Re-evaluate:

INV-1..8
E1..E14
SEC-01..24

Do not assume previous PASS remains valid after remediation.

Any changed behaviour must remain compatible with the approved requirements or be documented as a justified correction to a defective interpretation.

---

# BUILD

After engineering tests are green:

- rebuild the PyInstaller distribution;
- rebuild the Inno Setup installer if locally possible;
- smoke-test the frozen application;
- verify required schemas/notices remain packaged.

Do NOT:

- code-sign;
- invent publisher identity;
- invent EULA ownership/legal wording;
- fabricate clean-VM results;
- fabricate VirusTotal results.

Those remain owner/release actions.

---

# GIT

Use logical remediation commits.

Suggested grouping:

1. fidelity/correctness blockers;
2. security/verification fixes;
3. documentation/dependency/CI cleanup;
4. final regression/build evidence.

Do not rewrite history.
Do not force-push.
Do not hide previous audit findings.

Push when the repository is coherent and all locally achievable gates pass.

---

# REQUIRED OUTPUT

Create:

`temp/ENGINEERING-REMEDIATION-REPORT.md`

The report must contain:

## 1. Original Findings

List every B/C engineering finding from FINAL-RELEASE-AUDIT.

## 2. Fix Status

For each:

FIXED
PARTIALLY FIXED
NOT FIXED
OWNER ACTION

Include exact source/test files changed.

## 3. B-1 Evidence

Explain exactly how long references are now handled.

## 4. B-2 Evidence

Explain duplicate statement identity design.

## 5. B-3 Evidence

Explain missing-date behaviour.

## 6. Fidelity Sweep

List silent-loss/truncation paths found and treatment.

## 7. Security Fixes

Include PII masking results.

## 8. XLSX Verification

Explain exactly what `conservation_verified` means after remediation.

## 9. Tests

Provide exact:

- previous count;
- new count;
- pass/fail/skip;
- golden count;
- security count;
- warnings result;
- lint result.

## 10. Independent Probe Results

Report all seven required probes.

## 11. Requirement Status

INV-1..8
E1..E14
SEC-01..24

## 12. Licensing/Dependency Status

Document changes and unresolved review items.

## 13. Build Status

Frozen app and installer results.

## 14. Remaining Engineering Defects

Do not hide known issues.

## 15. Owner/Release Actions Remaining

Keep separate from engineering defects.

## 16. Git Status

Commits and push status.

## 17. ENGINEERING VERDICT

Choose exactly one:

RED — ENGINEERING NOT READY

AMBER — ENGINEERING FIXES STILL REQUIRED

GREEN — ENGINEERING READY FOR RELEASE PREPARATION

GREEN does NOT mean commercially released.

It means all locally achievable engineering blockers identified by the audit have been corrected and independently reverified.

---

# STOP CONDITION

Stop after:

- remediation;
- regression testing;
- locally achievable build verification;
- remediation report;
- commits/push where permitted.

Do NOT proceed to:

- code-signing;
- EULA/legal identity decisions;
- clean-VM owner test;
- VirusTotal submission;
- Lemon Squeezy;
- Gumroad;
- ITISYOU listing;
- marketing.

Those belong to the next release-preparation phase.