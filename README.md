# TOPIUM USB INTRO

A Windows 10/11 utility that lets you register a USB drive already connected to your PC, select a GIF, and configure an automatic intro when that exact drive is reconnected.

## Intended behavior

1. Open the configuration application.
2. Select your already-connected USB hard drive.
3. Browse to a GIF and preview it.
4. Enable automatic playback; Windows Task Scheduler registers an event-triggered one-shot launch.
5. Upon reconnection, the configured GIF plays **once**, File Explorer opens the drive, and the one-shot app exits.

The program should have **no continuously running custom background process**. An event-driven Windows task handles launch; real USB-hardware behavior must be validated on the target Windows PC.

## Current release status

The implementation is a source candidate for v0.2.0. Windows EXE builds and real USB tests are pending. See the source files, [GitHub Actions](https://github.com/t8pium/topium-usb-intro/actions), and build report when they are published.

No USB AutoRun security bypass, no executable on inserted media, no telemetry, and no paid API.
