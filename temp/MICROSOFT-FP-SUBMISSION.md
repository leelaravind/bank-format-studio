# Microsoft False-Positive Submission Pack — RC3

Prepared 2026-08-14. Use this verbatim; it contains only true, verifiable
statements. Do not claim the file is signed or "verified".

## The file to submit (verify the hash first)

```powershell
Get-FileHash F:\bank-format-studio\packaging\Output\BankFormatStudio-1.0.0-setup.exe -Algorithm SHA256
```

Must print exactly:

```
F393F34968CD4E703506D8AB2DEF2B341F7DE59CA0485EBE4851EB6FE6A8F340
```

If it does not match, STOP — do not submit.

## Where

https://www.microsoft.com/en-us/wdsi/filesubmission

- Sign in with any Microsoft account (create one for support@itisyou.app
  if preferred — submissions tie to the account for status tracking).
- **"What do you believe this file is?"** → *Incorrectly detected as
  malware (false positive)*
- **Submitter type** → *Software developer* (this queue gets priority
  review over home-user submissions)
- **Detection name** → `Trojan:Win32/Wacatac.B!ml`
- Upload `BankFormatStudio-1.0.0-setup.exe` (36,892,164 bytes)

## Suggested "Additional information" text (paste)

> I am the developer and publisher of this file. It is the official
> installer for "Bank Statement Format Studio" 1.0.0, a commercial offline
> Windows desktop utility that converts bank-statement file formats
> (MT940, ISO 20022 camt.053, CSV, XLSX export) locally on the user's
> machine.
>
> Technical profile: Inno Setup 6 installer wrapping a PyInstaller 6.22.0
> onedir-packaged Python/Qt (PySide6) application. Per-user install, no
> elevation, no drivers, no services, no scheduled tasks, no Run keys. The
> application contains no networking code and makes no network
> connections (it is fully offline by design; the only registry writes are
> the standard per-user Inno uninstall entries).
>
> The file is currently unsigned (code signing is planned). The detection
> is Trojan:Win32/Wacatac.B!ml — a machine-learning verdict. A current
> Microsoft Defender engine (4.18.26070.9, signatures 1.457.156.0) scans
> the identical file clean locally, and the VirusTotal behavioural
> sandboxes show no network communications, no injection APIs and no
> persistence beyond the installation itself.
>
> Publisher: Leela Aravind Karlapudi (ITISYOU) — support@itisyou.app
> SHA-256: f393f34968cd4e703506d8ab2def2b341f7de59ca0485ebe4851eb6fe6a8f340

## After submitting

1. Record the **submission ID** (shown on the confirmation page / email)
   in this file.
2. Track status at https://www.microsoft.com/en-us/wdsi/submissionhistory
   while signed in. Confirmed false positives are typically cleared in
   1–3 business days; the fix lands via cloud/definition updates — **no
   rebuild is needed and the hash does not change.**
3. When Microsoft reports "Not malware" / detection removed: on the RC3
   VirusTotal page, press **Re-analyze** and record the new ratio and
   date in `temp/ANTIVIRUS-RELEASE-DECISION.md`.
4. If Arctic Wolf still shows `Unsafe` after Microsoft clears (their
   verdict often follows other engines): email
   **falsepositive@arcticwolf.com** with the SHA-256, the VT link, and
   one line describing the product; record the reply.
5. If Microsoft instead **confirms** the detection as genuine (not
   expected given the evidence, but do not prejudge): treat the release
   as NO-GO and reopen the investigation — do not publish.

## Fields to fill in as evidence accumulates

- RC3 VirusTotal report URL: ______
- RC3 detection ratio at first scan: ______ (date: ______)
- Microsoft submission ID: ______ (date: ______)
- Microsoft outcome: ______ (date: ______)
- Post-clear re-analysis ratio: ______ (date: ______)
- Arctic Wolf contact/outcome (if needed): ______
