# SPDX-License-Identifier: GPL-3.0-or-later

# Local Release build with the same options as the windows-x86_64 job in
# .github/workflows/release-binaries.yml, minus sccache and the update checker.
# Usage: powershell -ExecutionPolicy Bypass -File tools\windows\build-release.ps1 [-Reconfigure] [-Jobs N]
#
# By default it compiles with 4 jobs at below-normal priority so the PC stays quiet and usable;
# -Jobs 0 uses every core at normal priority.
# -Clang builds in build\clang with LLVM's clang-cl, ThinLTO and a PGO profile: vendichii.profdata
# when it exists (tools\windows\pgo-merge.ps1), else lichii-windows.profdata (trained on Ocarina).
# -PgoGenerate builds an instrumented build in build\pgo-gen that writes build\pgo-gen\profiles\*.profraw.

param(
    [switch]$Reconfigure,
    [switch]$Clang,
    [switch]$PgoGenerate,
    [int]$Jobs = 4
)

$ErrorActionPreference = "Stop"

# Compilers and linkers inherit this process's priority class.
if ($Jobs -gt 0) {
    (Get-Process -Id $PID).PriorityClass = "BelowNormal"
}
$repo = Resolve-Path "$PSScriptRoot\..\.."
$build = if ($PgoGenerate) { "$repo\build\pgo-gen" } elseif ($Clang) { "$repo\build\clang" } else { "$repo\build\release" }
$clangArgs = @()
if ($Clang -or $PgoGenerate) {
    $llvm = "$env:ProgramFiles/LLVM/bin" -replace '\\', '/'
    if ($PgoGenerate) {
        # The instrumented exe writes where LLVM_PROFILE_FILE says (pgo-run.ps1 sets it).
        $pgo = "/clang:-fprofile-generate /clang:-fprofile-update=atomic"
        $rt = Get-ChildItem "$env:ProgramFiles\LLVM\lib\clang\*\lib\windows\clang_rt.profile-x86_64.lib" |
            Select-Object -First 1
        # The linker flags are split on spaces: give the library by its short (8.3) path.
        $short = (New-Object -ComObject Scripting.FileSystemObject).GetFile($rt.FullName).ShortPath
        $clangArgs += "-DCMAKE_EXE_LINKER_FLAGS=$($short -replace '\\', '/')"
    } else {
        $profile = "$repo\vendichii.profdata"
        if (!(Test-Path $profile)) { $profile = "$repo\lichii-windows.profdata" }
        $profile = $profile -replace '\\', '/'
        $pgo = "/clang:-fprofile-use=$profile -Wno-backend-plugin -Wno-profile-instr-unprofiled -Wno-profile-instr-out-of-date"
    }
    $clangArgs += @(
        "-DCMAKE_C_COMPILER=$llvm/clang-cl.exe",
        "-DCMAKE_CXX_COMPILER=$llvm/clang-cl.exe",
        "-DCMAKE_LINKER=$llvm/lld-link.exe",
        "-DCMAKE_AR=$llvm/llvm-lib.exe",
        "-DCMAKE_C_FLAGS=/DWIN32 /D_WINDOWS /DNOMINMAX /D_USE_STD_VECTOR_ALGORITHMS=0 $pgo",
        "-DCMAKE_CXX_FLAGS=/DWIN32 /D_WINDOWS /DNOMINMAX /D_USE_STD_VECTOR_ALGORITHMS=0 /EHsc /GR $pgo",
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
