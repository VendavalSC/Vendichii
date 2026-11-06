# Superbuild build notes

The superbuild is a normal Lichii PGO build. The exact configure commands are in
[`SUPERBUILD.md`](../../SUPERBUILD.md).

## Windows packaging

After building `build/pgo`:

```bash
mkdir -p <out>
cp -a <repo>/build/pgo/bin/. <out>/
cd <out>
windeployqt6 --release --no-translations --no-compiler-runtime --no-opengl-sw \
  --no-system-dxc-compiler --no-system-d3d-compiler \
  --dir <out> --libdir <out> --plugindir <out>/plugins lichii.exe
```

Copy the non-system DLLs that `objdump -p` lists, then add `qt.conf`:

```ini
[Paths]
Prefix = .
Plugins = plugins
```

`nx2_switches.txt` is read at GUI start. A user copy in
`%APPDATA%\eden\nx2_switches.txt` or
`$XDG_CONFIG_HOME/eden/nx2_switches.txt` takes precedence.

## Linux packaging

After building `build/pgo`:

```bash
strip <repo>/build/pgo/bin/lichii <repo>/build/pgo/bin/eden-cli
tar -czf <out>.tar.gz -C <out-dir> .
```

For an AppImage, use `linuxdeploy` with the Qt plugin and point `QMAKE` at the
Qt 6 `qmake`. The AppImage strips binaries during deployment.

## Profile

`eglantine.profdata` is in the repository root. Do not regenerate or modify it
unless you are intentionally changing the profile.
