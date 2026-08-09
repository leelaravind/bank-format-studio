# SECURITY & PRIVACY REQUIREMENTS

Status: PHASE 0 — binding requirements for the future implementation. No implementation yet.
Date: 2026-08-09

The application processes sensitive financial data (account numbers, balances,
counterparties, transaction descriptions). These requirements are product
commitments, not aspirations; each carries an ID for later test traceability.

## 1. Offline & data-sovereignty guarantees

- **SEC-01** The application MUST function fully offline. No network access is required for any core feature (conversion, validation, reconciliation, export).
- **SEC-02** The conversion/validation code paths MUST make zero network calls, ever. XSD schemas ship with the application and are resolved from the local install directory only; `schemaLocation`/`noNamespaceSchemaLocation` hints inside input files are ignored, and XML parsers are configured with network access disabled (`no_network=True` in lxml; xmlschema loaded from local paths only).
- **SEC-03** No telemetry, no analytics, no crash reporting to remote services, no update phone-home in V1. (A manual "check for updates" button, if ever added, must be user-initiated, clearly labelled, and send no document data — out of scope for V1.)
- **SEC-04** No customer bank data leaves the machine. No cloud processing, no remote logging.
- **SEC-05** Licence-key verification (Lemon Squeezy/Gumroad, future phase) MUST be designed to work offline after activation and MUST NOT transmit any document contents or filenames.

## 2. File handling

- **SEC-06** The application stores no bank files except outputs the user explicitly saves via a file dialog. No shadow copies, no auto-saved recents containing file contents.
- **SEC-07** Temporary files: avoid where possible (process in memory). Where unavoidable, create under the OS temp dir with `0600`-equivalent ACLs, unique unpredictable names, and delete them deterministically on completion and on startup (crash-leftover sweep). Best-effort overwrite-before-delete for temp files containing statement data.
- **SEC-08** Path traversal: output filenames derived from input data (e.g. statement IDs) MUST be sanitized (strip path separators, `..`, reserved Windows names CON/PRN/AUX/NUL/COM1../LPT1.., trailing dots/spaces, control chars). Output is written only inside the user-chosen directory; final resolved path must be verified to remain within it.
- **SEC-09** A "recent files" list, if implemented, stores paths only (never contents), is user-clearable, and can be disabled.

## 3. Logging & PII

- **SEC-10** Default log level logs no raw account numbers, counterparty names, references, or transaction descriptions. Log records reference positions ("statement 2, entry 14, field :86:") not values.
- **SEC-11** Where a value is needed for an error message shown to the user, it may appear in the UI but is masked in any persisted log (e.g. IBAN shown as `DE89…3000`). Diagnostic/verbose logging that includes values must be explicit opt-in per session, clearly warned, and written only to a user-chosen location.
- **SEC-12** Validation-error reports that the user exports may contain values (they own the data) — but the report must say it contains sensitive data.

## 4. Input parsing safety

- **SEC-13** XML: DTDs rejected; external entity resolution disabled; entity expansion limits enforced (billion-laughs); `huge_tree` disabled with a documented size limit (configurable, generous for real statements); parser never dereferences URLs. Applies to camt.053 input AND xlsx (xlsx is zip+XML — see SEC-15).
- **SEC-14** All inputs are untrusted: malformed MT940/CSV/XML must produce controlled, human-readable errors — never crashes, hangs, or resource exhaustion. Hard caps on line length, tag repetition counts, file size (documented, configurable).
- **SEC-15** xlsx import: zip-bomb protection (compression-ratio and total-uncompressed-size limits before extraction); entries with path traversal in archive names rejected; only expected sheet parts read.
- **SEC-16** CSV/Excel formula injection on EXPORT: cells beginning with `=`, `+`, `@`, TAB, CR (and `-` for non-numeric cells) are neutralized (apostrophe prefix) in the default Excel-safe mode; a strict RFC mode is available and clearly labelled. Numeric amount columns emitted as plain numbers are exempt.
- **SEC-17** CSV IMPORT: fields are treated as data only; nothing is ever evaluated.
- **SEC-18** Encoding handling: explicit, deterministic encoding detection rules (documented priority: BOM → declared XML encoding → configured default); no locale-dependent behaviour.

## 5. Platform & distribution

- **SEC-19** Release binaries are code-signed (see PACKAGING-STACK-RESEARCH.md owner actions). Installer makes no network calls except none — fully offline installer.
- **SEC-20** The build pipeline pins all dependency versions with hashes (`--require-hashes`) so shipped bytes are reproducible/auditable; dependency licence audit runs in CI (block GPL/AGPL).
- **SEC-21** No auto-update mechanism in V1.
- **SEC-22** Application does not request/require elevation beyond standard user install (per-user install preferred).

## 6. Memory & process hygiene (best-effort, documented honestly)

- **SEC-23** Statement data lives only in process memory during conversion; no swapping controls are promised (OS-managed), and marketing material must not overclaim "data never touches disk" if the OS may page memory. Honest wording required.
- **SEC-24** Clipboard: the app never places statement data on the clipboard except by explicit user copy action.

## 7. Test obligations

Each SEC-xx requirement must map to at least one test or release-checklist item in the implementation plan. Fixtures V02 (formula injection), C05 (schema-invalid), M06 (malformed), plus dedicated XXE/zip-bomb/path-traversal attack fixtures (to be added to FIXTURE-PLAN as a security set) cover SEC-08, SEC-13–SEC-17.
