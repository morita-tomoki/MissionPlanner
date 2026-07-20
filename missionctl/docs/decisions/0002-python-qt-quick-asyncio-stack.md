# 2. Python + Qt Quick (QML) + asyncio, core free of Qt

## Status
Accepted — 2026-07-20

## Context
Stack chosen by the human: Python + Qt Quick, developed on macOS, by a solo
engineer with Claude Code as the primary maintainer. The legacy MissionPlanner
failed on maintainability because UI (WinForms), transport, and state were fused
into global god-classes and a thread+lock model.

## Decision
- GUI: **PySide6** (official Qt for Python, LGPL) with **QML** for the view.
- Concurrency: **asyncio** everywhere; unify with the Qt event loop via **qasync**
  in a single process / single thread. No `threading`, no polling sleeps, no locks.
- Split the codebase into a **pure-Python `core` that never imports Qt** and a thin
  `qt/` bridge. Enforced by import-linter.

## Consequences
- The core is fully testable headless (pytest + tlog replay + SITL) — critical for
  an agent that cannot easily drive a GUI.
- The GUI can be swapped or a headless daemon added later without touching core.
- qasync is a small dependency risk; acceptable and isolated to `qt/`.

## Rejected alternatives
- **.NET + Avalonia**: rejected — human requires Python + Qt.
- **MAVSDK-Python**: rejected — incomplete ArduPilot support, extra C++ server
  process. (pymavlink chosen instead — ADR-0004.)
- **PyQt6**: viable, but PySide6's LGPL and official status fit a solo commercial
  project better.
