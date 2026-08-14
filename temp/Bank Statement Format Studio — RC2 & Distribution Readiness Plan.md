# Bank Statement Format Studio V1
## RC2 Freeze + VirusTotal + Distribution Compliance + Customer Package

### Objective

Take the corrected Windows build through the remaining pre-marketplace release preparation in one controlled session.

Current corrected installer:

`BankFormatStudio-1.0.0-setup.exe`

Expected SHA-256:

`7e1cd5c8898b9c9cb56c222ddf5074bb2800f077bcb521626551e9b110a5042a`

Publisher:

`Leela Aravind Karlapudi`

Brand:

`ITISYOU`

Support:

`support@itisyou.app`

The previous RC/hash `308ffce4...0799` is superseded and must never be published.

---

# 1. RC2 FREEZE

First inspect repository state and the corrected icon commit `48d3a53`.

Verify:

- working tree state;
- version remains 1.0.0;
- publisher identity;
- EULA release information;
- support address;
- product icon integration;
- unsigned-release policy;
- CI status;
- installer identity;
- SHA256SUMS;
- release documentation.

Confirm the installer SHA-256 independently.

Run all appropriate release gates.

Do NOT rebuild merely to reproduce an existing successful result.

If the existing artifact exactly matches the expected hash and repository state, preserve it byte-for-byte.

Create/update the release-candidate report identifying this exact installer as:

`Bank Statement Format Studio V1 RC2`

Record:

- filename;
- byte size;
- SHA-256;
- source commit;
- build provenance;
- test results;
- CI evidence;
- unsigned status;
- publisher;
- support contact;
- superseded RC information.

No artifact may silently change after RC2 freeze.

Any binary-changing correction invalidates RC2 and requires a new hash.

---

# 2. VIRUSTOTAL RELEASE CHECK

Use only the exact frozen RC2 installer.

If VirusTotal submission/access is available and authorized, scan the exact installer and record:

- SHA-256 submitted;
- scan date;
- detection count;
- detection names/vendors;
- meaningful behavioural observations;
- VirusTotal report URL where appropriate.

Do not automatically classify detections as false positives.

Investigate any detection sufficiently to distinguish likely packaging/heuristic detections from credible malware findings.

If VirusTotal cannot be accessed or submission requires owner interaction:

STOP that subtask and clearly report:

`OWNER ACTION REQUIRED — VIRUSTOTAL`

Provide the exact RC2 file and hash that must be submitted and the evidence that must be returned.

Do not claim VirusTotal PASS without an actual scan.

Never upload source code, customer data, bank statements, test fixtures containing sensitive data, credentials or secrets.

---

# 3. DISTRIBUTION / MARKETPLACE COMPLIANCE AUDIT

Audit the final product positioning for commercial distribution.

The product must be represented accurately as:

**Bank Statement Format Studio — an offline Windows utility for converting supported bank-statement formats including MT940, ISO 20022 camt.053, CSV and supported export formats.**

It is NOT:

- an AI product;
- banking software;
- accounting advice;
- financial advice;
- tax advice;
- a cloud bank-data processor;
- an automated financial decision system.

Verify that proposed customer claims are supported by actual V1 functionality.

Audit:

- product identity;
- publisher identity;
- EULA;
- third-party licensing;
- LGPL obligations;
- privacy/offline claims;
- supported formats;
- system requirements;
- limitations;
- unsigned Windows disclosure;
- SmartScreen expectations;
- checksum verification instructions;
- support contact;
- refund/support information required before marketplace publication.

Research current marketplace requirements where necessary rather than relying on old repository research.

Separate:

PASS  
OWNER ACTION  
MARKETPLACE-SPECIFIC REQUIREMENT  
BLOCKER

Do not create or publish marketplace listings in this session.

---

# 4. FINAL CUSTOMER DISTRIBUTION PACKAGE

Prepare a release-package directory for RC2 without modifying the frozen installer.

It should contain only customer/release material appropriate for distribution.

At minimum evaluate inclusion of:

- exact RC2 installer;
- SHA256SUMS.txt;
- EULA;
- installation/readme guide;
- supported-format documentation;
- CSV dialect documentation where customer relevant;
- third-party notices;
- required third-party licence texts;
- unsigned Windows/SmartScreen guidance.

Do not expose:

- source code;
- repository metadata;
- tests;
- internal audit documents;
- threat/security fixtures;
- build scripts;
- developer notes;
- credentials;
- secrets;
- temp files;
- unnecessary internal specifications.

Create a customer-facing installation guide explaining the unsigned release honestly.

Never instruct customers to disable Windows Defender or SmartScreen.

If Windows presents an unsigned publisher warning, explain the legitimate Windows workflow and SHA-256 verification procedure without describing the product as signed.

---

# 5. PACKAGE INTEGRITY AUDIT

After assembling the customer package:

- recursively inventory it;
- inspect for accidental internal/development files;
- scan text files for secrets/placeholders;
- verify publisher/support/product names;
- verify version consistency;
- verify installer hash against frozen RC2;
- verify SHA256SUMS;
- verify EULA/notices/licence presence;
- verify no superseded RC installer is included.

The frozen installer must remain byte-identical.

---

# 6. FINAL REPORT

Create:

`temp/RC2-DISTRIBUTION-READINESS-REPORT.md`

Report:

- RC2 identity;
- commit;
- installer filename;
- exact SHA-256;
- test/CI evidence;
- VirusTotal result OR explicit owner action;
- compliance findings;
- customer-package contents;
- integrity results;
- unsigned-release disclosures;
- outstanding owner actions;
- marketplace blockers;
- GO / CONDITIONAL GO / NO-GO recommendation for proceeding to Gumroad setup.

Do not mark external checks complete without evidence.

Do not publish anything.

Do not create a Gumroad product.

Do not modify the ITISYOU website/product page.

Do not introduce unrelated product changes.

Commit and push documentation/customer-package preparation only when appropriate. Never commit generated release binaries if repository policy excludes them.

### Stop condition

Stop when RC2 and the customer distribution package have been fully audited and the report has been produced, or when an external owner-only action prevents truthful completion.