# SPDX-License-Identifier: GPL-3.0-or-later

# Waits for the running Lichii to exit, turns the gdbstub back off in the config, rebuilds and then
# runs oot-bench.ps1 with the given arguments: one step for "close it and test the new build".
# -Fsr3FrameGen also turns frame generation on with FSR3 (no Lossless Scaling DLL needed).

param([switch]$Fsr3FrameGen)

while (Get-Process lichii -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 1
}
$ini = Join-Path $env:APPDATA "eden\config\qt-config.ini"
$text = [IO.File]::ReadAllText($ini)
$text = $text -replace "use_gdbstub\\default=false(\r?\n)use_gdbstub=true", "use_gdbstub\default=true`$1use_gdbstub=false"
if ($Fsr3FrameGen) {
    $text = $text -replace "frame_gen\\default=true(\r?\n)frame_gen=false", "frame_gen\default=false`$1frame_gen=true"
    $text = $text -replace "frame_gen_type\\default=(true|false)(\r?\n)frame_gen_type=0", "frame_gen_type\default=false`$2frame_gen_type=1"
}
[IO.File]::WriteAllText($ini, $text)
Write-Host "Building..."
& powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\build-release.ps1" *> (Join-Path $PSScriptRoot "..\..\build-release.log")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed: see build-release.log"
    exit $LASTEXITCODE
}
& "$PSScriptRoot\oot-bench.ps1" @args
