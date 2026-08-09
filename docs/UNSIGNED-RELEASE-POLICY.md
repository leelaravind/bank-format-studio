# UNSIGNED RELEASE POLICY (£0 path) — V1

Status: BINDING for V1 releases. Date: 2026-08-09.
Supersedes the "Never released unsigned" rule previously in RELEASE-CHECKLIST.md.
Replacement rule: **never presented as signed.**

## 1. Decision

V1 release binaries (`BankFormatStudio.exe` and the Inno Setup installer) are
distributed **without Authenticode code signing**, at zero signing cost, under
the mitigations in §3. This is a funding decision, not a security claim:
nothing in this policy makes an unsigned binary equivalent to a signed one.

## 2. Evaluation — why £0, and what it costs

Paid options (rejected for V1 on cost, not on merit):

- **Microsoft Trusted Signing**: $9.99/mo Basic, but identity validation has
  eligibility constraints (individual availability varies by region; orgs
  generally need 3+ years verifiable history).
- **OV certificate**: ~$250–550/yr, cloud/HSM-backed.
- EV no longer grants instant SmartScreen reputation (removed 2024), so EV's
  premium buys nothing extra here.

Accepted consequences of shipping unsigned — these are facts to disclose, not
problems to paper over:

- **SmartScreen** will show "Windows protected your PC" for the downloaded
  installer (Mark of the Web). Reputation is per file hash, so the warning
  returns with **every new release**.
- The UAC-free per-user install still surfaces **"Unknown publisher"** wherever
  Windows displays publisher identity.
- PyInstaller output has an elevated **antivirus false-positive** risk; signing
  was one of the standard mitigations and is unavailable on this path.
- Some managed environments (AppLocker/WDAC, corporate policy) **block unsigned
  executables outright**. No mitigation exists; those users cannot be served by
  the £0 path.
- Windows cannot cryptographically attribute the file to the publisher. Anyone
  can distribute a tampered copy under our name; the checksum manifest in §3
  lets users detect this **only if they verify it**.

## 3. Mandatory mitigations (the £0 path)

1. **Checksum manifest.** `packaging/build.ps1` generates
   `packaging/Output/SHA256SUMS.txt` covering the installer and
   `BankFormatStudio.exe` (sha256sum format: `<hash>  <filename>`). A release
   without this manifest is invalid.
2. **Two independent channels.** The manifest contents are published both on
   the download page and in a second channel the download host cannot silently
   rewrite (e.g. the source repository). A hash published only next to the
   download detects transfer corruption but not a compromised host.
3. **VirusTotal pre-publication scan** of the installer; publish the scan link
   with the release; submit false positives to Microsoft. (Uploading shares the
   binary with AV vendors — acceptable for release artifacts.)
4. **Disclosure at the point of download.** Every page offering the download
   carries the §5 disclosure text (or a faithful equivalent). Release notes
   state the release is unsigned.
5. **Identity metadata stays consistent** (exe version resource, installer
   `AppPublisher`, About dialog) — already enforced by
   `tests/unit/test_release_packaging.py`. Metadata is trivially copyable and
   is **not** an authenticity mechanism; it exists for transparency and
   support, and no material may present it as verification.
6. Existing AV-surface decisions stand: `--onedir`, no UPX, no self-update.

Optional £0 hardening (owner choice, not required for V1): a detached
signature over `SHA256SUMS.txt` with a free tool (minisign or `ssh-keygen -Y
sign`), public key pinned in the repository. This adds authenticity for users
who verify it, but it is **not Authenticode** and must never be described as
"code signing".

## 4. Prohibitions

- **No self-signed Authenticode certificates.** They still show "Unknown
  publisher", build no reputation, and function only as an imitation of being
  signed.
- **No claim, wording, or imagery implying the binaries are code-signed,
  "verified by Microsoft", or SmartScreen-approved.** This includes marketing
  copy, the download page, the installer UI, and documentation.
- **Never instruct users to disable or weaken SmartScreen, Defender, or any
  other protection.** Describing the standard per-file flow Windows itself
  offers ("More info" → "Run anyway") is acceptable only alongside the
  verification steps in §5.
- The build and installer must never fabricate a signature or stage a signing
  hook that pretends to have run (existing rule, restated).

## 5. Required download-page disclosure text

> **This installer is not code-signed.** Windows SmartScreen will warn
> ("Windows protected your PC" / publisher unknown) — this is expected for
> every release. Before installing, verify the download:
>
> 1. In PowerShell:
>    `Get-FileHash .\BankFormatStudio-<version>-setup.exe -Algorithm SHA256`
> 2. Compare the result against `SHA256SUMS.txt` published here **and** at
>    [second channel]. Install only if they match exactly.
>
> If the hashes match and you choose to proceed, select "More info" then
> "Run anyway" on the SmartScreen prompt. If they do not match, delete the
> download and report it via [support contact].

## 6. Exit criteria

This policy lapses the moment Authenticode signing (Trusted Signing or an OV
certificate) is available to the owner. SEC-19 then reverts to
signed-mandatory, the SignTool hooks in `packaging/installer.iss` and
`packaging/build.ps1` are configured, and the checksum manifest (§3.1–3.2)
continues alongside the signature — it remains useful, it just stops being the
only integrity mechanism.
