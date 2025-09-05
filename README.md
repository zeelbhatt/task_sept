# Neuronav (MVP) — Unified Sensor SDK

> A small, pragmatic SDK that gives a **one‑line** path to work with sensors (starting with Luxonis OAK via DepthAI), with **automatic driver installation**, **simple recording**, and **mock/webcam fallbacks** so you can test without hardware.

---

## Why this project exists
Most camera SDKs require manual driver installs, device‑specific boilerplate, and fragile environment setup. This repo hides that complexity:
- **Auto‑installs** runtime dependencies (DepthAI + OpenCV) the first time you call our API
- Provides a **single, consistent Sensor interface** (works with OAK today; extensible for others)
- Gives you a **one‑liner to record** to MP4
- **Still works without an OAK** (uses webcam or synthetic frames)

The main goal: let a developer write **3 lines** and get a recording, without learning DepthAI internals.

---

## What this repo contains
- A minimal Python package: `neuronav/`
- A **factory** to get a DepthAI sensor: `from neuronav.sensors import GetDepthai`
- A **client** to manage recording: `from neuronav import NeuronavClient`
- A **runtime installer** that `pip install`s missing packages and makes them immediately importable in the same Python process
- A **DepthAI adapter** that supports three modes: `depthai` (real device), `webcam`, `synthetic`

---

## High‑level flow (how things work)
```
User code
  └─ sensor = GetDepthai("oak-d-pro", mock_source="synthetic")
        ├─ ensure_package("opencv-python" -> import cv2)
        ├─ ensure_package("depthai" -> import depthai)
        ├─ choose mode: depthai | webcam | synthetic
        └─ build pipeline (if depthai)

  └─ client = NeuronavClient(api_key="...")
  └─ client.record(sensor, duration_seconds=5)
        ├─ sensor.start()
        ├─ loop: sensor.read() -> write frames to MP4
        └─ finally: sensor.stop(); sensor.cleanup()
```

---

## Project structure
```
neuronav/
  __init__.py               # exports NeuronavClient
  client.py                 # simple recording client
  utils/
    __init__.py
    installer.py            # ensure_package(): runtime auto-install + import refresh
  sensors/
    __init__.py             # GetDepthai(...) factory
    base.py                 # Sensor Protocol (interface contract)
    depthai_adapter.py      # DepthAISensor (depthai | webcam | synthetic)
README.md                   # this file
pyproject.toml              # build backend config (setuptools)
setup.cfg                   # package metadata & tool configs
```

---

## Key modules & design decisions

### `neuronav/utils/installer.py`
**What it does:**
- `ensure_package(pip_name, import_name=None)` tries `import import_name`.
- If missing, runs `pip install <pip_name>` **in‑process** and then:
  - refreshes `sys.path` (adds user site‑packages when pip falls back to `--user`)
  - invalidates import caches
  - imports the module **without restarting** Python

**Why this approach:**
- Removes the “go install this thing” step from the user
- Handles cases where pip installs to a different location than the running interpreter has in `sys.path`
- Supports packages whose **pip name ≠ import name** (e.g., `opencv-python` vs `cv2`)

### `neuronav/sensors/base.py`
**What it is:**
- A `typing.Protocol` defining the **Sensor interface**: `initialize()`, `start()`, `read() -> bool`, `stop()`, `cleanup()`, and `name: str`.

**Why Protocol:**
- **Structural typing** (duck typing with type safety). Any class that matches the shape is a Sensor; no inheritance required. This keeps the client decoupled from any specific device implementation.

### `neuronav/sensors/depthai_adapter.py`
**What it is:**
- `DepthAISensor` wrapper with **three modes**:
  - `depthai` (real OAK device via DepthAI pipeline)
  - `webcam` (OpenCV `VideoCapture(index)`) — for testing without OAK
  - `synthetic` (numpy‑generated test pattern) — for testing without *any* camera
- Writes MP4 using `cv2.VideoWriter` with file names like: `recordings/YYYYmmdd_HHMMSS_oak_d_pro_<mode>.mp4`

**Why these choices:**
- **Fallbacks** let you develop and test anywhere (CI, laptops with no OAK)
- **Simple MP4 writing** (works cross‑platform) – can be upgraded to DepthAI **hardware encoders** later for performance
- **Explicit lifecycle** ensures resources are always released (even on exceptions)

### `neuronav/sensors/__init__.py`
**What it is:**
- `GetDepthai(...)` factory that:
  - constructs `DepthAISensor` with config (mode, width/height/fps)
  - calls `initialize()` so returned object is ready to `start()`

**Why a factory:**
- Users get a ready‑to‑use sensor in **one call** (no pipeline ceremony)

### `neuronav/client.py`
**What it is:**
- `NeuronavClient(api_key, upload=False)` – stores API key for future cloud use
- `record(sensor, duration_seconds=None)` – starts the sensor, pumps frames in a loop, handles Ctrl+C, and cleans up deterministically

**Why this shape:**
- Minimal surface area for v1, focused on recording. Easy to extend with `snapshot`, `list_devices`, segmented recording, cloud upload, etc.

---


## Quickstart Create vertual environment if needed.
- `python -m venv myenv`
- `source myenv/bin/activate`
- Then run: `python test_script.py`


