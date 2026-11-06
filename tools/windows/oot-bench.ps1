# SPDX-License-Identifier: GPL-3.0-or-later

# Launches the local Release build with the frame-time log on, plus optional A/B switches.
# Every run writes %APPDATA%\eden\log\fps_<title>_<date>.csv (one line per second); summarize
# runs with tools\windows\fps-summary.py.
#
#   tools\windows\oot-bench.ps1                                   # Frizti defaults
#   tools\windows\oot-bench.ps1 -PerfOn clean_words,index_rebind  # turn off-by-default opts on
#   tools\windows\oot-bench.ps1 -PerfOff method                   # turn one default opt off
#   tools\windows\oot-bench.ps1 -Profile -ProfileDelay 60         # 20 s sample profile of the GPU
#                                                                 # and guest CPU threads, counted
#                                                                 # from the emulator's start
#   tools\windows\oot-bench.ps1 -GpuProfile                       # GPU thread zone shares in the log
#   tools\windows\oot-bench.ps1 -FrameTrace                       # swap interval and present pacing in the log
#   tools\windows\oot-bench.ps1 -Env @{ EDEN_NX2_MME_JIT = '1' }  # any other switch
#   tools\windows\oot-bench.ps1 -Set EDEN_NX2_A2C_REFRESH=1       # the same, as NAME=VALUE

param(
    [string[]]$PerfOn = @(),
    [string[]]$PerfOff = @(),
    [switch]$Profile,
    [int]$ProfileDelay = 45,
    [int]$ProfileSeconds = 20,
    [string]$ProfileThreads = "GPU,GPUBack,VulkanWorker,CPUCore_*",
    [switch]$GpuProfile,
    [switch]$FrameTrace,
    [hashtable]$Env = @{},
    [string[]]$Set = @(),
    [string]$Game = ""
)

$repo = Resolve-Path "$PSScriptRoot\..\.."
$exe = Get-ChildItem "$repo\build\release\bin" -Filter lichii.exe -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $exe) {
    Write-Error "oot-bench.ps1: build\release\bin\lichii.exe not found; run build-release.ps1"
    exit 1
}

$env:EDEN_FPS_LOG = "1"
# TAS scripts (Ctrl+F7 records, Ctrl+F5 plays) step in 1/60 s of wall time, so a recorded route
# replays the same at any frame rate.
$env:EDEN_TAS_REALTIME = "1"
if ($PerfOn) { $env:EDEN_NX2_PERF_ON = $PerfOn -join "," }
if ($PerfOff) { $env:EDEN_NX2_PERF_OFF = $PerfOff -join "," }
if ($Profile) {
    $env:EDEN_NX2_SAMPLE_PROFILE = "1000"
    $env:EDEN_NX2_SAMPLE_DELAY = "$ProfileDelay"
    $env:EDEN_NX2_SAMPLE_SECONDS = "$ProfileSeconds"
    $env:EDEN_NX2_SAMPLE_THREADS = $ProfileThreads
    # dynarmic's block map, so tools\windows\jit_report.py can name the guest code in [jit] samples
    $env:EDEN_JIT_PERF_MAP = (Join-Path $env:APPDATA "eden\log")
}
if ($GpuProfile) { $env:EDEN_NX2_GPU_PROFILE = "1" }
if ($FrameTrace) { $env:EDEN_DKB_FRAME_TRACE = "1" }
foreach ($key in $Env.Keys) { Set-Item "env:$key" $Env[$key] }
# "-File" hands "A=1,B=2" over as one string: split it where a new NAME= starts.
foreach ($pair in ($Set | ForEach-Object { $_ -split ",(?=[A-Za-z_][A-Za-z0-9_]*=)" })) {
    $name, $value = $pair -split "=", 2
    Set-Item "env:$name" $value
}

Get-ChildItem env: | Where-Object { $_.Name -like "EDEN_*" } |
    ForEach-Object { Write-Host "$($_.Name)=$($_.Value)" }

$gameArgs = if ($Game) { @("-g", $Game) } else { @() }
& $exe.FullName @gameArgs
