<!--
# SPDX-FileCopyrightText: Copyright 2025 Eden Emulator Project
# SPDX-License-Identifier: GPL-3.0-or-later

# SPDX-FileCopyrightText: 2018 yuzu Emulator Project
# SPDX-License-Identifier: GPL-2.0-or-later
-->

# Vendichii

Vendichii es un fork personal de [Lichii](https://github.com/zortos293/Lichii), el emulador experimental de Nintendo Switch y Switch 2, centrado en jugar **The Legend of Zelda: Ocarina of Time** (Switch 2) a 60 fps estables y con generación de fotogramas.

No es una versión oficial de Lichii ni de los proyectos de los que deriva, y no está afiliado a Nintendo.

## Descarga

Las builds están en [Releases](https://github.com/VendavalSC/Vendichii/releases). Descomprime el zip entero y ejecuta **lichii.exe**.

- Windows x64 con una GPU Vulkan 1.3.
- Microsoft Visual C++ Redistributable 2015-2022 (x64).
- Juegos, claves y firmware no están incluidos: usa solo los que hayas obtenido legalmente.

Vendichii usa las mismas carpetas de datos que Lichii/Eden (`%APPDATA%\eden`), así que tus partidas y ajustes se mantienen.

## Qué tiene

Encima de Lichii (build 117):

- **Generación de fotogramas AMD FSR 3**: la interpolación y el flujo óptico oficiales de AMD (FidelityFX SDK v1.1.4, shaders sin modificar), sin Lossless Scaling ni nada externo. Se activa en *Configurar > Gráficos > Frame generation > AMD FSR 3 Frame Generation*. La barra de estado muestra `Display: X FPS` con los fotogramas generados.
- **PGO propio**: compilado con clang, ThinLTO y un perfil grabado jugando a Ocarina. En la ciudadela de Hyrule pasó de 35 a 45-50 fps.
- **zstd nativo**: la descompresión de datos de Ocarina corre en código nativo en vez de emulado.
- **Dynamic FPS** de Dark (Eglantine) integrado, y los hilos de la GPU fijados a sus propios núcleos.
- Herramientas de benchmark y perfilado para Windows en [`tools/windows`](tools/windows).

### Ajustes recomendados para Ocarina

- CPU emulada: **Normal** (Boost acelera el juego).
- Reactive flushing: **activado** (desactivado da pantalla blanca).

## Compilar

Con Visual Studio 2022+, el Vulkan SDK y LLVM instalados:

```powershell
powershell -ExecutionPolicy Bypass -File tools\windows\build-release.ps1 -Clang
```

El ejecutable queda en `build\clang\bin\lichii.exe`. Para regrabar el perfil PGO: `build-release.ps1 -PgoGenerate`, jugar con `tools\windows\pgo-run.ps1`, cerrar, `pgo-run.ps1 -Merge` y volver a compilar con `-Clang`. Más detalles en la [guía de compilación](docs/Build.md).

## Créditos y licencia

Vendichii se basa en el trabajo de **Lichii** (zortos293), **Frizti**, **Eglantine** (Djihads80, Camille LaVey), **Eden**, **yuzu** y **Sudachi**, y de todos sus colaboradores. Dynamic FPS es de Dark (Eglantine). FSR 3 es de AMD (licencia MIT). Se conservan los avisos de copyright originales y las licencias de terceros.

Licencia GPL-3.0: ver [LICENSE.txt](LICENSE.txt).
