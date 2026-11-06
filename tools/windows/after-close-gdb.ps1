# SPDX-License-Identifier: GPL-3.0-or-later

# Waits for the running Lichii to exit, turns the gdbstub on in the config (the emulator rewrites
# it on exit, so it can only be changed once it is closed) and runs oot-bench.ps1 with the given
# arguments. tools\windows\gdb_callers.py then connects to port 6543.

while (Get-Process lichii -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 1
}
$ini = Join-Path $env:APPDATA "eden\config\qt-config.ini"
$text = [IO.File]::ReadAllText($ini)
$text = $text -replace "use_gdbstub\\default=true(\r?\n)use_gdbstub=false", "use_gdbstub\default=false`$1use_gdbstub=true"
[IO.File]::WriteAllText($ini, $text)
& "$PSScriptRoot\oot-bench.ps1" @args
