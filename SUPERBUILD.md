# Lichii Superbuild (unofficial)

> ## ✅ v32 recommended
>
> v32 is based on zortos `nx2` `a551b808`, includes #874 and selected safe Fritchii fixes, and is the current recommended release. v31/v30/v29/v28/v24 remain fallbacks.

## Credits

This build exists because of the work of:

- [zortos293/Lichii](https://github.com/zortos293/Lichii) — base `nx2`, compatibility reports, first-run performance defaults, Bananza page-mark batching, perf9 paths
- [jojo-chaechae/Eglantine](https://github.com/jojo-chaechae/Eglantine) — GPU-split submit and macro hand-back fixes
- [Duck912/Eglantine-ducky](https://github.com/Duck912/Eglantine-ducky) — OoT reticle/CPU-write fix and near-leaf pointer fix
- [Frizti/Lichii](https://github.com/Frizti/Lichii) — scoped buffer/submission/FSR3 fixes and Dynamic FPS
- [mja00/Lichii](https://github.com/mja00/Lichii) — uniform-bank upload, query timing, HMMA unroll
- [Nolar-Hack/Lichii](https://github.com/Nolar-Hack/Lichii) — video swap-interval, compute sizing, scheduler exclusion, guest RAM release, texture-cache threshold
- [BrunoSilvestre00](https://github.com/BrunoSilvestre00) — async native draw discard (PR #224)
- [Shakoquo/Lichii-sharkiix-version](https://github.com/Shakoquo/Lichii-sharkiix-version) — GPU thread wake and AMD/OoT tuning experiments
- The Eglantine, Eden, yuzu and Sudachi contributors

Curated performance and correctness fixes on top of
[zortos293/Lichii](https://github.com/zortos293/Lichii) `nx2`.

This is **not** an official Lichii build. It is a testing branch that combines
selected upstream and fork fixes with explicit provenance. Expect breakage; keep
a stock build as fallback.

## Base

- Upstream: `zortos293/Lichii`
- Branch: `nx2`
- Base commit: `a551b80888dacfc71bbdc2b2d0b81702d656c04e` (2026-11-08).
  The grass/foliage fix is now upstream as #551, so the 14-commit
  `capy/oot-hyrule-grass-fix` series is no longer carried.
- Upstream `nx2` already contains #303, #287, #314, #224, #273, #284, #290,
  #295, #149, #185, #197, #203, #215, #232, #241, #397, #398, #410, #412,
  #413, #414, #418, #425, #429, #433, #435, #438, #439, #442, #443, #444,
  #482, #485, #490, #432, #436, #351, #504, #255/#497, #499, #512, #515,
  #518/#519/#526, #524, #537, #509, #520, plus the 24-commit batch landing
  #588 (TXD/ATOMG shadow registers), #584 (Dynamic FPS down to 10 fps),
  #585 (sysmix audio), #580 (page-table walk reuse), #550 (disk-cache
  pipelines), #465 (bounded unbuilt-pipeline wait), #333 (page-table
  sizing), #481 (sorted RangeSet), #250 (skip empty invalidations), #174
  (software HMMA unroll), #245 (bindless handle words), #446 (50 us GPU
  thread poll), #440 (texture-cache OOM), #427 (framebuffer limits), #495
  (descriptor payload growth), #530 (Linux core pinning), #270 (present FPS
  limit), #365 (Overwolf hook disable), #484 (maximized window), #511 (MIME
  install), #160 (ZBIC failure), #221 (IPSwitch lines), #551 (OoT grass
  fix, 64 storage buffers and compute-pipeline rebuilds), #582/#583
  (HMMA on VK_KHR_cooperative_matrix, OoT +12-24% and RDNA4 41->60 fps),
  #587 (float16 for LSFG frame generation), #606
  (NVIDIA DLSS Super Resolution for OoT), #569 (task/mesh pipelines
  through compute without VK_EXT_mesh_shader), #616 (OoT sharpening-network
  bypass), #574 (CI ccache), #659 (movie A/V sync, imports #571), #657
  (keep HMMA off AMD emulated cooperative matrices, RDNA2 crash), #664
  (GPU Clocks Boost/Overclock for Switch 2, Mario Kart World 30 fps lock),
  #679 (AMD fixes from the CheezerWheezer fork survey) and the 26-commit
  batch ending #721 (OoT movie network input copy), #268 (texture-cache
  budget 5/8), #714 (switches read after load), #700 (block invalidation),
  #698 (hybrid CPU threads), #692 (TC override cap), #591 (pipeline cache
  version), #575 (host mip chains), #533/#611 (texture invalidation),
  #498/#610 (TLD4.F16 gathers), #479/#609 (DMA fence thread) and #778
  (Fritchii v4/v4.1: OoT water flicker, staging-buffer reuse, per-method
  switch reads), plus #781 (shader precache), #769 (split GPU thread
  pinning), #655 (OoT FPS unlock and frame-rate limit), #752 (channel wait),
  #337 (fence-flagged reports), #264 (buffer read traps), #690 (MKW water),
  #699 (deferred clear), #820 (noperspective interpolation), #816 (native
  compute storage bounds), #296 (ASTC uploads), #821 (face-button glyphs),
  #818 (stale guest image uploads), #817 (join-copy upload skip), #691
  (Switch 2 button icons), #809 (decoder packets/movie clock), #815
  (pipeline-cache record filtering), #621 (pending-channel poll timer), #812
  (shader precache archive discovery), #841 (cached task/mesh pipelines),
  #885 (NUP zstd lazy decode), #858 (Bananza back-thread perf), #881
  (microphone silence), #880 (backable texture), #878 (precache memory),
  #879 (AV1 decoder choice), #902 (SPIR-V clip-distance race), #910
  (texture-memo null-image crash), #921 (fast-draw/memo full-resolve parity)
  and #912 (dav1d default thread count). Those are not re-applied here.
- PR #635 (OoT DLSS glow/particle history fix) and the follow-up R16F bias-mask
  and DLSS preset E/F commits from `capy/oot-dlss-effects-mask-r16f` are carried
  locally. PR #635 is still open upstream; PR #644 (the R16F follow-up) was
  closed as an untested draft. If zortos lands either, rebase and drop our copy.
- The cutscene A/V sync package carried in v17 is now upstream as #659 and was
  dropped from this branch.
- Native HDR presentation from clshortfuse is carried locally: PR #180 here
  (a port of Djihads80/Eglantine#605). Both upstream PRs are still open. HDR is
  opt-in and off by default. If either lands, rebase and drop our copy.
- OoT recommended preset from PR #2 (EvertonCeciliano): disables memory-operation
  syncs for OoT and enables NVIDIA DLSS where available.
- License: GPL-3.0-or-later, inherited from Lichii/Eden/yuzu

## Branches

- `nx2` — untouched upstream snapshot used as the base
- `superbuild` — current curated build, including all portable fixes

This repository is a standalone public mirror, not a GitHub fork-network fork.
There is no separate AMD variant.

## Releases

Standard and PGO builds are published for Windows and Linux x86_64. PGO is the
recommended package. Both use `-fprofile-use=eglantine.profdata` (50,134 Itanium-
mangled names, matching our MinGW/Itanium-ABI Clang): Windows with Clang 23 + LLD,
Linux with Clang 23 + LLD, which is exactly upstream's Linux PGO method. Upstream's
Windows PGO uses clang-cl + ThinLTO + `lichii-windows.profdata` (MSVC-ABI names);
that profile cannot be read by our compiler, and ThinLTO was tested and reverted
because MSYS2 ships no `llvm-ar` to index bitcode archives. Windows packages use
bundled static FFmpeg to avoid the MSYS2 `libva.dll` false positive.

Windows builds also enable NVIDIA DLSS/Streamline. Upstream gates
`ENABLE_NVIDIA_DLSS` on `MSVC AND ARCHITECTURE_x86_64`; we relax it to
`WIN32 AND ARCHITECTURE_x86_64` so MinGW Clang builds show the **Use NVIDIA
DLSS** checkbox and compile the #606 / PR #635 code. The Streamline MIT headers
come from CPM; `sl.interposer.dll` and the DLSS plugins are loaded at run time
from the user's PC. Linux is unchanged (Streamline is Windows-only).

The updater points at this repository's releases (`callme-sy/Lichii-Superbuild`,
`vN` tags, `Lichii-vN-<platform>` assets). It is enabled in release builds only when
`LICHII_BUILD_TAG` and `LICHII_BUILD_PLATFORM` are set at configure time.

## Included fixes

### From zortos293/Lichii and forks

| Fix | Source |
|---|---|
| Bananza GPU-written page marks batched by bitmap word | zortos `perf/bananza-perf9`, `dd8e60ef` |
| Upload native 64 KiB uniform banks without protection churn | mja00 `fix/native-uniform-bank-upload`, `dbcbe547` |
| Write fence-flagged query reports after prior GPU work | mja00 `fix/fence-query-report-timing`, `0059f37b` |
| Unroll each K8 group of the software HMMA | mja00 `fix/hmma-k8-group-unroll`, `7221023e` |
| Do not download GPU data over newer CPU writes (OoT reticle) | Duck912, `05fe0408` |
| Submit deferred work before the split back waits on fences | GPU-split branch, `498345a5` |
| Hand macros back when the GPU split stops | GPU-split branch, `5b1b5c0f`, conflict resolved |
| Wake the GPU thread on a queued command | Shakoquo `sharkiix`, `28f594acc7` |
| OoT recommended settings prompt (session-only) | superbuild UI, `capy/new-user-performance-defaults` values |

### Additional portable fixes

| Fix | Source |
|---|---|
| Lift `EDEN_NX2_SWAP_INTERVAL` while a video plays | Nolar-Hack `oot-amd-linux`, `1ae67a43` |
| Size native compute storage buffers from the mapping only for DLSS/tables | Nolar-Hack, `3472a85a` |
| Keep other threads out of the Vulkan scheduler during split-back submit | Nolar-Hack, `b39883d2` |
| Release guest RAM when a Switch 2 game stops | Nolar-Hack, `30e3cc38` |
| `EDEN_NX2_TC_MINIMUM_MIB` texture-cache collection threshold | Nolar-Hack, `52504537` |

Upstream #273 already fixes the depth-compare integer case on AMD; the earlier
mja00 `be437dd4` and Nolar `63650298` variants are not re-applied on top of it.

## Deliberately not included

- mja00 storage-binding range cache (`2aea767b`) — conflicts with newer
  memory-manager code; needs a rebase.
- GPU-split overlapping-write wait (`add0db8c`) — conflicts with the newer
  query/drain path.
- Nolar ARM64 dynarmic superblock work — irrelevant on x86_64.
- Nolar tools/docs/fork-notice commits.
- Auto-stub debug logging.
- Unrelated forks and experimental branches.

## Environment switches

- `EDEN_NX2_PRELOAD_ALL_PIPELINES=1` is preset in the packaged
  `nx2_switches.txt`.
- `EDEN_NX2_ASYNC_DISCARD=1` is preset; native draws skip unbuilt pipelines
  instead of stalling (experimental, from PR #224).
- `EDEN_NX2_COMPUTE_MAPPING_SIZED=1` restores the old compute-buffer sizing for
  A/B testing of the OoT overexposure candidate.
- `EDEN_NX2_TC_MINIMUM_MIB` controls the texture-cache collection threshold.

## Building

The build is a normal Lichii PGO build. Set `<repo>` to the checkout, `<msys2>`
to the MSYS2 UCRT64 root, and `<qt>` to the Qt 6 prefix.

Windows (MSYS2 UCRT64, Clang 23):

```bash
cmake -S <repo> -B <repo>/build/pgo -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DYUZU_CMD=ON -DYUZU_ROOM=OFF \
  -DYUZU_USE_BUNDLED_QT=OFF -DYUZU_USE_BUNDLED_SDL3=ON \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld \
  "-DCMAKE_C_FLAGS=-fprofile-use=<repo>/eglantine.profdata -Wno-backend-plugin -Wno-profile-instr-unprofiled -Wno-profile-instr-out-of-date" \
  "-DCMAKE_CXX_FLAGS=-fprofile-use=<repo>/eglantine.profdata -Wno-backend-plugin -Wno-profile-instr-unprofiled -Wno-profile-instr-out-of-date"
cmake --build <repo>/build/pgo --target yuzu yuzu-cmd --parallel 8
```

Linux (Clang 23 + LLD, Qt 6.8.3):

```bash
cmake -S <repo> -B <repo>/build/pgo -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DYUZU_CMD=ON -DYUZU_ROOM=OFF \
  -DYUZU_USE_BUNDLED_QT=OFF -DCMAKE_PREFIX_PATH=<qt> \
  -DYUZU_USE_BUNDLED_SDL3=ON -Dfmt_FORCE_BUNDLED=ON \
  -DCMAKE_C_COMPILER=clang-23 -DCMAKE_CXX_COMPILER=clang++-23 \
  "-DCMAKE_EXE_LINKER_FLAGS=-B/usr/lib/llvm-23/bin -fuse-ld=lld" \
  "-DCMAKE_C_FLAGS=-fprofile-use=<repo>/eglantine.profdata -Wno-backend-plugin -Wno-profile-instr-unprofiled -Wno-profile-instr-out-of-date" \
  "-DCMAKE_CXX_FLAGS=-fprofile-use=<repo>/eglantine.profdata -Wno-backend-plugin -Wno-profile-instr-unprofiled -Wno-profile-instr-out-of-date"
cmake --build <repo>/build/pgo --target yuzu yuzu-cmd --parallel 8
```

See `tools/superbuild/README.md` for packaging notes.

## Reproducing the patch

`patches/superbuild.patch` is the complete diff from the base commit to
`superbuild`.

```bash
git checkout a551b808
git apply patches/superbuild.patch
```
