# Changelog

All releases are unofficial builds. See the GitHub releases for assets and checksums.

## v29

- Adds #874: fence-flagged payload releases stay synchronized at low
  accuracy/Default fences, restoring Ocarina of Time performance after #337.
- Based on v28 / zortos `nx2` `c2e293ec`; includes the #910 OoT texture-memo
  crash fix and the official nx2 merge set.
- All v28 features included.
- Windows and Linux, standard and PGO.

## v28

- Based on zortos `nx2` `c2e293ec`, with the #910 Ocarina of Time texture-memo
  crash fix: null texture views are no longer prepared on a memo hit.
- Includes the official nx2 merge set: #858 (Bananza back-thread performance),
  #878 (precache memory), #879 (AV1 libdav1d), #880 (backable texture), #881
  (microphone silence), #885 (NUP zstd lazy decode) and #902 (SPIR-V
  clip-distance race).
- All v24 features included: native HDR,
  NVIDIA DLSS, Fritchii v4/v4.1 fixes and the full superbuild set.
- Windows and Linux, standard and PGO.

## v24

- Shader precache discovers every container the archive walker reads (#812),
  improving hit coverage before a game starts.
- Cached task/mesh pipelines are built at boot on GPUs without
  VK_EXT_mesh_shader (#841), avoiding first-use pipeline builds.
- All v23 features included: GPU-thread poll timer, pipeline-cache filtering,
  native HDR, NVIDIA DLSS and the full
  superbuild set.
- Windows and Linux, standard and PGO.
## v23

- Smoother GPU thread scheduling: the pending-channel poll timer resets when a
  channel makes progress, with shorter Windows waits (#621).
- Pipeline caches keep only undamaged, non-stale and non-duplicate records,
  avoiding slow loads and corrupt cache entries (#815).
- All v22 features included: shader
  precache, split GPU thread pinning, OoT FPS Unlock, native HDR, NVIDIA DLSS,
  the Fritchii fixes and the full superbuild set.
- Windows and Linux, standard and PGO.
## v22

- Ocarina of Time's recommended preset now also disables memory-operation
  synchronization and turns on NVIDIA DLSS where available (FSR 3.1 fallback).
- Latest `nx2` batch: shader precache before game start (#781), split GPU
  threads pinned to their own cores by default (#769), OoT FPS Unlock and
  Switch 2 frame-rate limit slider (#655), non-blocking channel waits (#752),
  fence-flagged report timing (#337), buffer read traps (#264), MKW water and
  waves (#690), deferred-clear render passes (#699), perspective-correct
  noperspective interpolation (#820), bounded native compute storage (#816),
  cheaper ASTC uploads (#296), stale-image upload fixes (#818/#817), Switch 2
  button icons (#691) and decoder/movie-clock fixes (#809).
- The rest of the superbuild set is unchanged.
- Windows and Linux, standard and PGO.

## v21

- Ocarina of Time's water no longer flickers at Zora's River and other water; a
  storage-buffer address mistaken for a texture handle now binds no texture.
- Upload staging buffers are kept and reused instead of being freed every 64
  frames, removing 2-68 ms setup stalls after pauses in Hyrule Field.
- Large video-memory cards may fill more of their budget before texture
  collection, and the texture-cache overrides are capped at the device budget.
- Ocarina of Time's movie network is replaced by an input copy, fixing its
  movie path.
- Faster GPU invalidation and query handling, fewer pipeline-cache evictions,
  motion-sensor fixes, NUP title fixes, LayeredFS mod-root guards and many more
  upstream fixes (zortos `nx2` `794602bf`, including #778).
- The full superbuild set is unchanged: OoT recommended-settings prompt,
  GPU-split and fence fixes, fence-flagged query reports, Bananza page-mark
  batching, mja00 work, Nolar's video/scheduler/texture-cache fixes, the
  `PRELOAD_ALL_PIPELINES` and `ASYNC_DISCARD` presets, NVIDIA DLSS on Windows,
  native HDR (opt-in) and the updater pointed at this repository.
- Windows and Linux, standard and PGO.

## v20

- **Native HDR output (opt-in).** Enable HDR in Graphics settings on a compatible
  Vulkan system and HDR display; reference white and peak luminance are adjustable.
  HDR uses RGB10A2/RGBA16F framebuffers and HDR swapchain color spaces, and skips
  SDR-only effects and frame generation while active. From the shortfuse HDR PR
  (upstream Eglantine #605, ported to Lichii as #180).
- HDR is off by default and requires an HDR-capable display; unsupported HDR
  presentation fails rather than silently falling back to SDR.
- The rest of the superbuild set is unchanged: OoT recommended-settings prompt,
  GPU-split and fence fixes, fence-flagged query reports, Bananza page-mark
  batching, mja00 uniform-bank/HMMA work, Nolar's video, scheduler and
  texture-cache fixes, the `PRELOAD_ALL_PIPELINES` and `ASYNC_DISCARD` presets,
  NVIDIA DLSS on Windows, and an updater pointed at this repository.
- Windows and Linux, standard and PGO.

## v19

- Mario Kart World no longer locks near 30 fps: GPU Clocks Boost and Overclock
  once again shrink Switch 2 GPU durations (upstream #664).
- A batch of AMD graphics fixes: occlusion query waits, non-Depth-ref compare
  samplers, blend key rebuilds, out-of-range texture handles, pipeline cache
  recovery after a driver rejection, uneven BCn mip handling and keeping
  preloaded pipelines resident (upstream #679).
- What this build adds over stock Lichii is unchanged: the OoT recommended-settings
  prompt, GPU-split and fence fixes, fence-flagged query reports, Bananza
  page-mark batching, the mja00 uniform-bank/HMMA work, Nolar's video,
  scheduler and texture-cache fixes, the `PRELOAD_ALL_PIPELINES` and
  `ASYNC_DISCARD` presets, and an updater pointed at this repository.
- Windows and Linux, standard and PGO.

## v18

- Movie video now stays in sync with its audio, with late-frame dropping, movie
  pacing and faster streaming for Switch 2 titles (upstream #659).
- Fixed an RDNA2 GPU crash caused by cooperative-matrix HMMA (upstream #657).
- Windows and Linux, standard and PGO.

## v17

- Ocarina of Time cutscenes now stay in sync with their audio below 60 fps: late
  movie frames are dropped, movie pacing is always on, and Switch 2 titles no
  longer pay the SD-card read throttle that delayed streamed video.
- NVIDIA DLSS for OoT: the effects mask is now handed to Streamline in a format
  it accepts, so the glow and particle fix works. DLSS presets E and F are now
  selectable.
- Windows and Linux, standard and PGO.

## v16

- NVIDIA DLSS is now available on Windows. Enable it in Graphics settings and
  use the download button under the option to fetch NVIDIA's Streamline and DLSS
  files. Requires a GeForce RTX card; AMD and Intel keep FSR 3.1.
- Option to bypass Ocarina of Time's sharpening anti-aliasing network.
- Fix for night-time smear and flicker from Navi's glow, fireflies and dust when
  DLSS is on.
- Windows and Linux, standard and PGO.

## v15

- Adds NVIDIA DLSS Super Resolution for Ocarina of Time and task/mesh pipelines
  through compute on GPUs without `VK_EXT_mesh_shader`.
- PGO builds verified and kept for Windows and Linux.
- Windows and Linux, standard and PGO.

## v14

- The OoT grass/foliage fix is now upstream: Hyrule Field's grass stays dense and
  Castle Town's near hedges keep their leaves.
- Cooperative-matrix HMMA for OoT (+12–24% standing/walking, RDNA4 41 → 60 fps),
  float16 support for LSFG frame generation, Dynamic FPS down to 10 fps, a 50 µs
  GPU-thread poll, texture-cache out-of-memory handling and framebuffer limits.
- Windows and Linux, standard and PGO.

## v13

- In-place AppImage updates with one rollback copy.
- Windows and Linux, standard and PGO.

## v12

- The built-in updater now points at this repository and finds `Lichii-vN-…`
  releases.
- Added device-loss diagnostics and frame-generation status in the status bar.
- Windows packages use bundled static FFmpeg.
- Windows and Linux, standard and PGO.

## v11

- Upstream fixes for OoT far-field sky haze, NaN handling, QMD release formats,
  microphone capture and NUP metadata.
- Windows packages use bundled static FFmpeg.
- Windows and Linux, standard and PGO.

## v10

- 43 upstream commits: 64-byte usage tracking, 32-bit global atomics, dynamic
  per-tap offsets, macro hand-back, Turing macro RAM, gathered-buffer lifetime,
  address-wrap rejection and game-list crash fixes.
- Windows and Linux, standard and PGO.

## 261106-v9

- Reviewed candidate fixes: NaN-defined min/max, QMD release formats,
  framebuffer limits, texture-cache OOM retries and mesh-shader logging.
- Windows and Linux, standard and PGO.

## 261106-v8

- Upstream OoT split-deadlock fix, GPU back bookkeeping, quad index growth,
  paired cbuf pointer and CPU-write download guard.
- Windows and Linux, standard and PGO.

## 261106-v7

- Opt-in desktop compatibility reports and Linux AppImage switch discovery.
- Windows and Linux, standard and PGO.

## 261106-v6

- Ocarina of Time now asks on launch whether to use recommended performance
  settings (FSR3, GPU accuracy Low, GPU NVDEC, async presentation and async
  shaders). Session-only; saved preferences are unchanged. New desktop configs
  receive those values as first-run defaults.
- GPU thread wake from the sharkiix work.
- Windows and Linux, standard and PGO.

## 261106-v4

- Async native draw discard, worker lost-wake fix, misaligned SSBO and compute
  write ordering fixes.
- GPU thread wake: queued commands wake the GPU thread immediately.
- Windows and Linux, standard and PGO.

## 261106-v3

- Async native discard stops draws stalling on unbuilt pipelines.
- Windows and Linux, standard and PGO.

## 261106-v2

- First release with the full curated superbuild fix set: Bananza page-mark
  batching, OoT reticle, GPU split, Frizti ports, mja00 fixes and AMD fixes.
- Windows and Linux, standard and PGO.
