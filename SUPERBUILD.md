# Lichii Superbuild (unofficial)

Curated performance and correctness fixes on top of
[zortos293/Lichii](https://github.com/zortos293/Lichii) `nx2`.

This is **not** an official Lichii build. It is a testing branch that combines
selected upstream and fork fixes with explicit provenance. Expect breakage; keep
a stock build as fallback.

## Base

- Upstream: `zortos293/Lichii`
- Branch: `nx2`
- Base commit: `e219d24c5affb2450963017dd8b07ec22618654e` (2026-11-06)
- Upstream `nx2` already contains #273 (AMD shader typing/depth sampling) and
  #284 (AV1 in MinGW builds); those are not re-applied here.
- License: GPL-3.0-or-later, inherited from Lichii/Eden/yuzu

## Branches

- `nx2` — untouched upstream snapshot used as the base
- `superbuild` — current curated build, including all portable AMD-relevant fixes
- `legacy/superbuild-55532` — historical 55532-based branch, kept for reference

This repository is a standalone private mirror, not a GitHub fork-network fork.
AMD-relevant fixes are generic and fused into the single `superbuild` branch;
there is no separate AMD variant.

## Releases

PGO is the only published build. Normal builds are used for validation and A/B
testing only; they are not attached to releases. The PGO profile is
`eglantine.profdata`, built with Clang 23 and LLD.

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
git checkout e219d24c
git apply patches/superbuild.patch
```

## Credits

- zortos293 and the Lichii/Eden/yuzu contributors
- Frizti
- mja00 / Matt Artist
- Nolar-Hack
- Duck912
- jojo-chaechae
- Everyone whose fixes were ported or referenced above
