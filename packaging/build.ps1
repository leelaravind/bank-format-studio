# Build script — Bank Statement Format Studio Windows distribution.
# Usage:  powershell -ExecutionPolicy Bypass -File packaging\build.ps1
# Steps: licence gate -> tests -> notices -> licence texts -> PyInstaller onedir
#        -> smoke test -> (Inno Setup if iscc on PATH) -> SHA256SUMS manifest
# Signing: V1 ships unsigned per docs/UNSIGNED-RELEASE-POLICY.md (signing hook
# below stays inert until the owner has a certificate).

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "== 1/8 licence gate =="
& $py (Join-Path $root "tools\licence_gate.py")
if ($LASTEXITCODE -ne 0) { throw "licence gate failed" }

Write-Host "== 2/8 test suite =="
& $py -m pytest (Join-Path $root "tests") -q
if ($LASTEXITCODE -ne 0) { throw "tests failed - refusing to package" }

Write-Host "== 3/8 third-party notices =="
& $py (Join-Path $root "packaging\generate_notices.py")
if ($LASTEXITCODE -ne 0) { throw "notice generation failed" }

Write-Host "== 4/8 licence texts (LGPL/GPL) =="
# Canonical GNU texts are versioned in packaging/licenses (fetched from gnu.org;
# verbatim redistribution of licence texts is expressly permitted).
$licDir = Join-Path $PSScriptRoot "licenses"
foreach ($f in @("LICENSE.LGPL3.txt", "LICENSE.GPL3.txt")) {
    if (-not (Test-Path (Join-Path $licDir $f))) {
        throw "$f missing from packaging/licenses - restore it from the repository"
    }
}

Write-Host "== 5/8 PyInstaller (--onedir) =="
& $py -m PyInstaller (Join-Path $PSScriptRoot "bfs.spec") --noconfirm --distpath (Join-Path $PSScriptRoot "dist") --workpath (Join-Path $PSScriptRoot "build")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

Write-Host "== 6/8 smoke test of the frozen app =="
$exe = Join-Path $PSScriptRoot "dist\BankFormatStudio\BankFormatStudio.exe"
if (-not (Test-Path $exe)) { throw "frozen exe missing" }
# Qt DLLs must be replaceable files on disk (LGPL relink obligation):
$qtDlls = Get-ChildItem (Join-Path $PSScriptRoot "dist\BankFormatStudio") -Recurse -Filter "Qt6*.dll"
if ($qtDlls.Count -eq 0) { throw "Qt DLLs not found as files - LGPL relink obligation violated" }
Write-Host "   Qt DLLs present: $($qtDlls.Count) (relink obligation satisfied)"

Write-Host "== 7/8 installer (Inno Setup) =="
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

Write-Host "== 8/8 SHA-256 manifest (SEC-19 unsigned path) =="
# sha256sum-format manifest over the release artefacts; published through two
# independent channels per docs/UNSIGNED-RELEASE-POLICY.md.
$outDir = Join-Path $PSScriptRoot "Output"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
$artefacts = @($exe)
$setup = Get-ChildItem $outDir -Filter "BankFormatStudio-*-setup.exe" -ErrorAction SilentlyContinue
if ($setup) { $artefacts += $setup.FullName }
elseif ($isccPath) { throw "installer expected but no setup exe found in packaging\Output" }
$lines = foreach ($a in $artefacts) {
    $h = (Get-FileHash $a -Algorithm SHA256).Hash.ToLower()
    "$h  $(Split-Path $a -Leaf)"
}
$manifest = Join-Path $outDir "SHA256SUMS.txt"
$lines -join "`n" | Out-File $manifest -Encoding ascii
Write-Host "   $manifest"
$lines | ForEach-Object { Write-Host "   $_" }

# Signing hook (OWNER ACTION): when a certificate/Trusted Signing profile exists,
# sign dist\BankFormatStudio\BankFormatStudio.exe and the setup exe here with
# signtool. This script intentionally does NOT fake a signature.
Write-Host "Build finished. UNSIGNED binaries (docs/UNSIGNED-RELEASE-POLICY.md):"
Write-Host "publish SHA256SUMS.txt in two channels and disclose unsigned status"
Write-Host "at the point of download - never present this release as signed."
