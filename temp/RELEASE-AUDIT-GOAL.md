# BANK STATEMENT FORMAT STUDIO V1
# PHASE 2 — FINAL RELEASE AUDIT

## ROLE

Act as an independent senior software release auditor.

Bank Statement Format Studio V1 has completed implementation.

Engineering currently reports:

- 205/205 tests passing
- 37 golden tests
- 69 security tests
- ruff clean
- licence gate passing
- PyInstaller Windows build successful
- Inno Setup installer successful
- application works offline
- binaries currently unsigned

Do NOT trust these claims merely because they appear in the completion report.

Verify them against the actual repository, source code, tests, configuration and build artifacts wherever possible.

## OBJECTIVE

Determine whether this repository is genuinely ready to become a commercially distributed V1 Windows product.

This phase is AUDIT ONLY.

DO NOT:

- modify production code
- fix defects
- redesign architecture
- expand product scope
- change tests to make them pass
- regenerate golden outputs merely to obtain green tests
- alter licence files
- rebuild unless required to verify a claim
- commit changes
- push changes
- publish anything
- configure Lemon Squeezy/Gumroad
- claim owner-only checks were completed

You MAY execute tests, static analysis, build verification and read-only diagnostic commands.

Create one final report:

`temp/FINAL-RELEASE-AUDIT.md`

---

# 1. IMPLEMENTATION CLAIM VERIFICATION

Audit `IMPLEMENTATION-COMPLETION-REPORT.md`.

For every major claim classify:

VERIFIED
PARTIALLY VERIFIED
UNVERIFIED
CONTRADICTED

Verify at minimum:

- supported formats
- normalized-model architecture
- Decimal-only financial arithmetic
- XSD validation
- reconciliation
- information-loss reporting
- offline operation
- GUI/CLI presence
- test counts
- golden tests
- security tests
- packaging
- installer
- licence gate
- dependency versions

Do not repeat claims without evidence.

---

# 2. V1 SCOPE AUDIT

Compare implementation against the approved Phase 0/Phase 1 specifications.

Confirm V1 contains only the approved scope:

- MT940 read/write
- camt.053.001.02 read/write
- camt.053.001.08 read/write
- documented CSV interchange read/write
- XLSX export only
- reconciliation reports
- information-loss reports
- offline Windows GUI

Confirm excluded functionality has not accidentally entered the product:

- BAI2
- camt.052
- camt.054
- MT942
- arbitrary-bank CSV import
- XLSX import
- Open Banking
- cloud processing
- telemetry
- analytics
- auto-update
- AI features

Report scope deviations.

---

# 3. FINANCIAL CORRECTNESS AUDIT

Inspect implementation of:

INV-1 through INV-8
E1 through E14
GATE-1 through GATE-4

Look specifically for:

- float usage in financial paths
- sign/reversal mistakes
- debit/credit inversions
- incorrect balance arithmetic
- currency mistakes
- date/year inference problems
- sequence/page problems
- truncation without diagnostics
- unsupported-field silent loss
- camt version confusion
- MT940 formatting violations
- reconciliation bypasses
- errors converted into warnings incorrectly

Run relevant tests.

Perform several independent spot-check conversions rather than relying only on existing golden tests.

---

# 4. ROUND-TRIP / LOSS AUDIT

Audit the claim that the product does NOT promise false losslessness.

Verify:

MT940 → camt → MT940

and

camt → MT940 → camt

produce conservation results consistent with the specification.

Verify every intentional:

- dropped field
- truncated field
- transliteration
- flattening
- derivation
- merge

can produce an appropriate information-loss note.

Search for writer paths where information can disappear silently.

Classify any silent-loss path as RELEASE BLOCKER unless demonstrably harmless and specified.

---

# 5. XML / CAMT AUDIT

Verify:

- bundled XSD versions
- namespace detection
- .02/.08 handling
- local schema resolution
- generated camt XSD validation
- malformed XML handling
- DTD rejection
- external entity rejection
- schemaLocation network avoidance
- unsupported namespace behaviour
- resource exhaustion protections

Check actual implementation, not only tests.

---

# 6. MT940 AUDIT

Inspect:

- envelope stripping
- encoding handling
- :60: / :62: balances
- :61: C/D/RC/RD handling
- :86: parsing/writing
- structured slash convention
- GVC input behaviour
- :28C: sequence/page handling
- multi-page statements
- reversal semantics
- year-boundary handling
- writer reparsing

Identify assumptions likely to fail on real-world bank variants.

Separate:

RELEASE BLOCKER
KNOWN V1 LIMITATION
ACCEPTABLE

---

# 7. CSV/XLSX AUDIT

Verify:

- documented CSV dialect
- mandatory statements.csv
- deterministic columns
- snake_case
- NONREF handling
- CSV formula-injection protection
- CSV import never evaluates formulas
- encoding handling
- XLSX export only
- workbook safety/resource limits
- deterministic XLSX output where claimed

Check whether spreadsheet cells can accidentally execute formulas when opened.

---

# 8. SECURITY AUDIT

Audit SEC-01 through SEC-24 against actual implementation.

Pay particular attention to:

- network calls
- telemetry
- analytics
- HTTP libraries
- remote schemas
- XML XXE
- XML entity expansion
- zip bombs
- archive traversal
- filesystem traversal
- Windows reserved filenames
- unsafe temp files
- logging of bank/account/customer data
- clipboard writes
- command execution
- subprocess use
- unsafe deserialization
- eval/exec
- dynamic imports
- dependency risks
- crash paths caused by malicious input

Search the repository for suspicious APIs/imports.

Run security tests.

Report each SEC requirement:

PASS
PARTIAL
FAIL
MANUAL

---

# 9. PRIVACY/OFFLINE AUDIT

The commercial positioning depends heavily on local/offline processing.

Verify `bfs_core` and the packaged application do not intentionally transmit:

- bank files
- account numbers
- names
- transaction descriptions
- diagnostics
- telemetry
- crash reports

Search dependencies and application code for network-capable behaviour.

Distinguish between a library merely being technically capable of networking and the product actually invoking networking.

Verify socket-blocking tests meaningfully cover conversion paths.

---

# 10. DEPENDENCY / LICENCE AUDIT

Audit:

`pyproject.toml`
lock files
build configuration
`THIRD-PARTY-NOTICES.txt`
bundled licences
PyInstaller configuration
actual packaged dependencies

Verify licences and distribution obligations for at least:

- mt-940
- lxml
- xmlschema
- defusedxml
- openpyxl
- PySide6 / Qt
- shiboken6
- PyInstaller
- Python runtime
- ISO 20022 schemas

Check whether development-only packages are unnecessarily shipped.

Investigate the THIRD-PARTY-NOTICES statement that PyInstaller and related packages appear under GPL licences and confirm whether applicable exceptions/distribution conditions are correctly handled.

Pay particular attention to Qt LGPL compliance:

- dynamic libraries separate/replaceable
- licence texts included
- notices included
- no static Qt linking
- exact Qt/PySide source availability information
- installer does not prevent replacement of Qt DLLs

Do NOT provide legal advice.

Instead classify:

CLEAR FOR TECHNICAL RELEASE
CONDITIONALLY ACCEPTABLE
NEEDS OWNER/LEGAL REVIEW
BLOCKER

---

# 11. ISO 20022 ASSET AUDIT

Verify:

- exact bundled schemas
- provenance records
- hashes
- modification status
- notices
- redistribution basis documented in the repository

Check the outstanding owner action concerning browser re-download/hash confirmation.

Do not mark it complete unless evidence exists.

Determine whether this is:

RELEASE BLOCKER
RECOMMENDED BEFORE RELEASE
NON-BLOCKING

---

# 12. PACKAGING AUDIT

Inspect:

- `packaging/bfs.spec`
- `packaging/build.ps1`
- `packaging/installer.iss`
- packaged distribution if present

Verify:

- application version
- executable naming
- installer naming
- per-user installation
- no unnecessary elevation
- uninstall support
- offline installation
- licence files included
- notices included
- schemas included
- no development fixtures accidentally shipped
- no secrets
- no source repository metadata
- no unnecessary sensitive files

Inspect final artifact contents.

---

# 13. RELEASE IDENTITY AUDIT

Current installer contains an owner placeholder for AppPublisher.

Identify every remaining placeholder such as:

TODO
OWNER ACTION
CHANGEME
example.com
placeholder names
temporary product names
development paths
debug labels

Report exact file and line/location.

Do NOT choose the owner's legal/publisher identity yourself.

Also check:

- product version
- app display name
- executable metadata
- copyright fields
- icon status
- About dialog
- EULA
- privacy/offline wording
- support/contact placeholders

---

# 14. CODE SIGNING AUDIT

Do NOT attempt to purchase or fabricate a certificate.

Verify signing hooks exist and determine exactly what remains.

Classify unsigned release as appropriate for:

PRIVATE TESTING
SOFT/BETA DISTRIBUTION
COMMERCIAL PUBLIC RELEASE

Explain likely Windows SmartScreen implications technically without claiming reputation outcomes.

Provide exact owner action required.

---

# 15. CI AUDIT

Inspect:

`ci/github-workflow-ci.yml`

Compare it against local verification commands.

Verify:

- workflow syntax
- Python matrix
- dependency installation
- tests
- security tests
- lint
- licence gate
- packaging where applicable
- hashes/pinning
- no secret leakage

The workflow is currently parked outside `.github/workflows`.

Do NOT move it during this audit.

Determine whether restoring it is required before commercial release.

---

# 16. TEST QUALITY AUDIT

Do not evaluate only test quantity.

Assess whether the 205 tests actually exercise important failure modes.

Look for:

- tests that merely assert implementation behaviour instead of specification behaviour
- weak assertions
- excessive mocking
- golden files generated by the same code being tested without independent validation
- skipped tests
- xfails
- warnings hiding failures
- untested error branches
- insufficient real-world variant coverage

Verify reported counts independently.

Report confidence:

HIGH
MEDIUM
LOW

for:

MT940
camt
CSV
XLSX
reconciliation
security
GUI
packaging

---

# 17. BUILD REPRODUCIBILITY

Determine whether a fresh developer machine can reproduce the release.

Check:

- pinned dependencies
- hashes
- Python requirements
- external build tools
- Inno Setup dependency
- deterministic artifacts where claimed
- undocumented local dependencies

Identify anything that exists only because of the current development machine.

---

# 18. CLEAN-MACHINE TEST PLAN

Do not pretend to perform a clean-VM test unless this environment genuinely is one.

Create an exact manual clean Windows test checklist for the owner.

It should include:

install
launch
offline/network-disabled operation
MT940 input
camt .02 input
camt .08 input
CSV input
all output formats
reconciliation report
loss report
malformed input
uninstall
residual files
non-admin account
Windows Defender/SmartScreen observations

---

# 19. COMMERCIAL RELEASE PACKAGE AUDIT

Determine exactly what should be delivered to a paying customer.

Identify whether customer should receive:

installer only

or

installer + documentation/licence material

or another package.

Verify source code, tests, internal fixtures and Git metadata are NOT required in the customer package.

Recommend exact release ZIP structure.

Do not configure marketplace listings yet.

---

# 20. FINAL RELEASE CLASSIFICATION

Finish `temp/FINAL-RELEASE-AUDIT.md` with:

## A. VERIFIED CLAIMS

## B. RELEASE BLOCKERS
Issues that must be fixed before selling.

## C. HIGH-PRIORITY FIXES
Strongly recommended before public release.

## D. ACCEPTED V1 LIMITATIONS
Valid limitations that do not block release.

## E. OWNER ACTIONS
Only actions Claude cannot legitimately complete.

## F. OPTIONAL POST-V1 IMPROVEMENTS
Do not mix these with release blockers.

## G. REQUIREMENT STATUS
INV-1..8
E1..E14
SEC-01..24

## H. TEST CONFIDENCE
By subsystem.

## I. LICENCE/REDISTRIBUTION STATUS

## J. PACKAGING STATUS

## K. CLEAN-VM TEST CHECKLIST

## L. EXACT FILES REQUIRING CHANGES
File + issue only. Do not change them.

## M. FINAL VERDICT

Choose exactly one:

RED — NOT READY FOR RELEASE

AMBER — ENGINEERING READY, RELEASE ACTIONS/FIXES REQUIRED

GREEN — READY FOR COMMERCIAL DISTRIBUTION

Do not choose GREEN while a release-blocking owner action remains incomplete.

## N. NEXT ACTION

If RED/AMBER, provide the smallest ordered set of actions required to reach GREEN.

Do not implement them.

---

# AUDIT STANDARD

Be adversarial.

Do not protect the previous implementation from criticism.

Do not assume passing tests prove correctness.

Do not create problems merely to appear thorough either.

Every finding must be supported by repository evidence, executed verification, or clearly labelled engineering inference.

Distinguish:

verified fact
test evidence
static-analysis evidence
manual requirement
engineering inference

The goal is to determine whether we can responsibly package and sell V1.

STOP after writing `temp/FINAL-RELEASE-AUDIT.md`.

Do not fix anything.
Do not commit.
Do not push.