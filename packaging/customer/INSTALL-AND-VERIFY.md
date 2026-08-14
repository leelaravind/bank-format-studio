# Bank Statement Format Studio 1.0.0 — Installation & Verification Guide

Publisher: Leela Aravind Karlapudi (ITISYOU) · Support: support@itisyou.app

Bank Statement Format Studio is an offline Windows utility that converts bank
statements between supported formats (MT940, ISO 20022 camt.053, CSV, with
Excel export). All processing happens locally on your computer: the
application makes no network connections and your statement data never leaves
your machine.

## System requirements

- Windows 10 (64-bit, version 1809 or later) or Windows 11
- About 150 MB of free disk space
- No administrator rights required — the app installs per-user
- No internet connection required to install or use the application

## Before you install: verify your download

This release is **not code-signed** (an authenticated publisher certificate
is planned for a future release). That has two honest consequences:

1. Windows SmartScreen will likely show **"Windows protected your PC"** when
   you run the installer, and Windows will show **"Unknown publisher"**.
   This is expected for this release.
2. Because Windows cannot verify the publisher for you, you should verify
   the download yourself using its SHA-256 checksum. It takes one command.

**Verification steps:**

1. Open PowerShell in your Downloads folder and run:

   ```
   Get-FileHash .\BankFormatStudio-1.0.0-setup.exe -Algorithm SHA256
   ```

2. Compare the result with the value in `SHA256SUMS.txt` (included with this
   package and also published on the download page). The two must match
   **exactly**:

   ```
   f393f34968cd4e703506d8ab2def2b341f7de59ca0485ebe4851eb6fe6a8f340
   ```

3. **If the hashes match** and you choose to proceed: run the installer, and
   when SmartScreen appears select **"More info"**, then **"Run anyway"**.
   Do not change any Windows security settings — SmartScreen and Microsoft
   Defender should stay switched on; this per-file confirmation is the
   standard flow Windows itself provides.
4. **If the hashes do not match**: do not install. Delete the download and
   contact support@itisyou.app.

## Installing

1. Run `BankFormatStudio-1.0.0-setup.exe`.
2. Read and accept the licence agreement (EULA — also included in this
   package and installed alongside the application).
3. Choose whether you want a desktop shortcut, then complete the wizard.
   The install is per-user and does not ask for administrator approval.

After installation you will find **Bank Statement Format Studio** in the
Start Menu. The install folder also contains `EULA.txt`,
`THIRD-PARTY-NOTICES.txt`, the third-party licence texts and the CSV format
documentation.

## Using the application

1. **Open statement…** — choose an MT940 (`.sta`, `.mt940`, `.940`, `.txt`),
   camt.053 XML, or CSV file exported by this application.
2. The file is validated and previewed, and declared balances are
   reconciled against the transactions.
3. Choose the target format and click **Convert**.
4. Review the **Validation & reconciliation** and **Information loss** tabs.
   Formats are not equally expressive, so a conversion may change or drop
   details — the report tells you exactly what, before you save.
5. **Save output…** — nothing is written to disk until you save.

## Uninstalling

Use *Settings → Apps → Installed apps → Bank Statement Format Studio →
Uninstall* (or the uninstaller in the Start Menu). The application stores
statement data only in memory while it runs; uninstalling removes the
installed files.

## Important notes

- The Software converts and reports on statement files you provide. It does
  not provide banking, accounting, tax, legal or financial advice.
- Support: **support@itisyou.app**
