# SPDX-License-Identifier: GPL-3.0-or-later

# Waits for the running Lichii to exit, then runs oot-bench.ps1 with the given arguments, so the
# next benchmark opens as soon as the previous one is closed.
#   tools\windows\after-close.ps1 -Profile -ProfileDelay 15 -Set "NAME=VALUE"

while (Get-Process lichii -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 1
}
& "$PSScriptRoot\oot-bench.ps1" @args
