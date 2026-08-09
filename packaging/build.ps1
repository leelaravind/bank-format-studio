# Build script — Bank Statement Format Studio Windows distribution.
# Usage:  powershell -ExecutionPolicy Bypass -File packaging\build.ps1
# Steps: licence gate -> tests -> notices -> licence texts -> PyInstaller onedir
#        -> smoke test -> (Inno Setup if iscc on PATH) -> (signing hook if configured)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "== 1/7 licence gate =="
& $py (Join-Path $root "tools\licence_gate.py")
if ($LASTEXITCODE -ne 0) { throw "licence gate failed" }

Write-Host "== 2/7 test suite =="
& $py -m pytest (Join-Path $root "tests") -q
if ($LASTEXITCODE -ne 0) { throw "tests failed - refusing to package" }

Write-Host "== 3/7 third-party notices =="
& $py (Join-Path $root "packaging\generate_notices.py")
if ($LASTEXITCODE -ne 0) { throw "notice generation failed" }

Write-Host "== 4/7 licence texts (LGPL/GPL) =="
# Canonical GNU texts are versioned in packaging/licenses (fetched from gnu.org;
# verbatim redistribution of licence texts is expressly permitted).
$licDir = Join-Path $PSScriptRoot "licenses"
foreach ($f in @("LICENSE.LGPL3.txt", "LICENSE.GPL3.txt")) {
    if (-not (Test-Path (Join-Path $licDir $f))) {
        throw "$f missing from packaging/licenses - restore it from the repository"
    }
}

Write-Host "== 5/7 PyInstaller (--onedir) =="
& $py -m PyInstaller (Join-Path $PSScriptRoot "bfs.spec") --noconfirm --distpath (Join-Path $PSScriptRoot "dist") --workpath (Join-Path $PSScriptRoot "build")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

Write-Host "== 6/7 smoke test of the frozen app =="
$exe = Join-Path $PSScriptRoot "dist\BankFormatStudio\BankFormatStudio.exe"
if (-not (Test-Path $exe)) { throw "frozen exe missing" }
# Qt DLLs must be replaceable files on disk (LGPL relink obligation):
$qtDlls = Get-ChildItem (Join-Path $PSScriptRoot "dist\BankFormatStudio") -Recurse -Filter "Qt6*.dll"
if ($qtDlls.Count -eq 0) { throw "Qt DLLs not found as files - LGPL relink obligation violated" }
Write-Host "   Qt DLLs present: $($qtDlls.Count) (relink obligation satisfied)"

Write-Host "== 7/7 installer (Inno Setup) =="
$isccCmd = Get-Command iscc -ErrorAction SilentlyContinue
$isccPath = if ($isccCmd) { $isccCmd.Source }
            elseif (Test-Path "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") { "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" }
            elseif (Test-Path "C:\Program Files (x86)\Inno Setup 6\ISCC.exe") { "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" }
if ($isccPath) {
    & $isccPath (Join-Path $PSScriptRoot "installer.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed" }
    Write-Host "Installer written to packaging\Output\"
} else {
    Write-Warning "Inno Setup (ISCC.exe) not found - installer not built. Install Inno Setup 6 and rerun."
}

# Signing hook (OWNER ACTION): when a certificate/Trusted Signing profile exists,
# sign dist\BankFormatStudio\BankFormatStudio.exe and the setup exe here with
# signtool. This script intentionally does NOT fake a signature.
Write-Host "Build finished. Unsigned binaries - signing requires the owner's certificate."
