# SPDX-License-Identifier: GPL-3.0-or-later

# Own PGO profile for Ocarina of Time:
#   build-release.ps1 -PgoGenerate   (instrumented build)
#   pgo-run.ps1                      (play a while, close the emulator)
#   pgo-run.ps1 -Merge               (writes vendichii.profdata)
#   build-release.ps1 -Clang         (optimized with it)

param([switch]$Merge)

$repo = Resolve-Path "$PSScriptRoot\..\.."
$profiles = "$repo\build\pgo-gen\profiles"
$llvm = "$env:ProgramFiles\LLVM\bin"
if ($Merge) {
    & "$llvm\llvm-profdata.exe" merge -o "$repo\vendichii.profdata" (Get-ChildItem "$profiles\*.profraw").FullName
    exit $LASTEXITCODE
}
New-Item -ItemType Directory -Force $profiles | Out-Null
$env:LLVM_PROFILE_FILE = "$profiles\lichii-%p.profraw"
Start-Process "$repo\build\pgo-gen\bin\lichii.exe"
