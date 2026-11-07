# SPDX-License-Identifier: GPL-3.0-or-later

# Local Release build with the same options as the windows-x86_64 job in
# .github/workflows/release-binaries.yml, minus sccache and the update checker.
# Usage: powershell -ExecutionPolicy Bypass -File tools\windows\build-release.ps1 [-Reconfigure] [-Jobs N]
#
# By default it compiles with 4 jobs at below-normal priority so the PC stays quiet and usable;
# -Jobs 0 uses every core at normal priority.
# -Clang builds in build\clang with LLVM's clang-cl, ThinLTO and eglantine.profdata (PGO).

param(
    [switch]$Reconfigure,
    [switch]$Clang,
    [int]$Jobs = 4
)

$ErrorActionPreference = "Stop"

# Compilers and linkers inherit this process's priority class.
if ($Jobs -gt 0) {
    (Get-Process -Id $PID).PriorityClass = "BelowNormal"
}
$repo = Resolve-Path "$PSScriptRoot\..\.."
$build = if ($Clang) { "$repo\build\clang" } else { "$repo\build\release" }
$clangArgs = @()
if ($Clang) {
    $llvm = "$env:ProgramFiles/LLVM/bin" -replace '\\', '/'
    $profile = "$repo/eglantine.profdata" -replace '\\', '/'
    $pgo = "/clang:-fprofile-use=$profile -Wno-backend-plugin -Wno-profile-instr-unprofiled -Wno-profile-instr-out-of-date"
    $clangArgs = @(
        "-DCMAKE_C_COMPILER=$llvm/clang-cl.exe",
        "-DCMAKE_CXX_COMPILER=$llvm/clang-cl.exe",
        "-DCMAKE_LINKER=$llvm/lld-link.exe",
        "-DCMAKE_C_FLAGS=/DWIN32 /D_WINDOWS /D_USE_STD_VECTOR_ALGORITHMS=0 $pgo",
        "-DCMAKE_CXX_FLAGS=/DWIN32 /D_WINDOWS /D_USE_STD_VECTOR_ALGORITHMS=0 /EHsc /GR $pgo",
        "-DENABLE_LTO=ON"
    )
}

. "$PSScriptRoot\load-msvc-env.ps1"

# A MinGW CMake (GnuTLS) has no CA file, so its downloads of the CI packages fail certificate
# checks. Git for Windows ships a CA bundle.
$caBundle = "$env:ProgramFiles\Git\mingw64\etc\ssl\certs\ca-bundle.crt"
$tlsArgs = @()
if (Test-Path $caBundle) {
    $tlsArgs += "-DCMAKE_TLS_CAINFO=$($caBundle -replace '\\', '/')"
}

$vulkanSdk = Get-ChildItem C:\VulkanSDK -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
if (-not $vulkanSdk) {
    Write-Error "build-release.ps1: Vulkan SDK not found under C:\VulkanSDK"
    exit 1
}
$env:VULKAN_SDK = $vulkanSdk.FullName
$env:PATH = "$($vulkanSdk.FullName)\Bin;$env:PATH"

if ($Reconfigure -or !(Test-Path "$build\CMakeCache.txt")) {
    cmake -S $repo -B $build -G Ninja `
        -DCMAKE_BUILD_TYPE=Release `
        -DBUILD_TESTING=OFF `
        -DYUZU_TESTS=OFF `
        -DYUZU_CMD=ON `
        -DYUZU_ROOM=OFF `
        -DYUZU_ROOM_STANDALONE=OFF `
        -DYUZU_USE_BUNDLED_SDL3=ON `
        -DENABLE_UPDATE_CHECKER=OFF `
        -DLICHII_BUILD_PLATFORM=windows-x86_64 `
        -DUSE_DISCORD_PRESENCE=OFF `
        -DLICHII_LINK_ICF=OFF `
        @tlsArgs @clangArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Jobs -gt 0) {
    cmake --build $build --parallel $Jobs
} else {
    cmake --build $build
}
exit $LASTEXITCODE
