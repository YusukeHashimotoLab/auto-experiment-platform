# Bill of Materials (BOM)

Hardware used in the reference implementation described in the paper. Equivalent
instruments can be substituted; the control drivers in `src/devices/` are written
per-device and can be adapted.

## Instruments

| Item | Model | Qty | Notes |
|---|---|---|---|
| Hot-plate stirrer | IKA RET control-visc | 2 | RT–400 °C, stirring + temperature control |
| Robot arm | Dobot Magician | 2 | One per solution to prevent cross-contamination |
| Electric pipette | Sartorius Picus 2 (500–10,000 μL) | 2 | Dispensing speed electronically controlled in 9 steps, about 1–11 mL/s (nominal) |
| Electronic balance | Sartorius BCE822i-1SJP | 1 | Capacity 820 g, readability 0.01 g |
| Web camera (process monitoring) | Logitech C920n | 1 | Fixed above the system |
| Web camera (appearance imaging) | Logitech C920n | 1 | Part of the imaging system (`src/imaging/`) |
| Light | NEEWER RGB62 | 1 | White/red/green/blue illumination, controlled over Bluetooth LE (`src/imaging/`) |
| IoT sensor board | Raspberry Pi Zero WH + Waveshare Environment Sensor HAT | 1 | Temperature, humidity, illuminance, UV, VOC, 3-axis acceleration and angular velocity (magnetometer not read; see `src/monitoring/README.md`) |
| Control PC | — | 1 | Connects to all devices via Wi-Fi or USB |

## Fabrication

| Item | Model | Notes |
|---|---|---|
| 3D printer | Bambu Lab X1E | Used to print all fixtures in `cad/` |
| CAD software | Autodesk Fusion 360 | Source `.f3d` / `.f3z` files provided in `cad/` |

## Software / AI services

| Component | Used in |
|---|---|
| Gemini 3.5 Flash (Google) | `src/agent/` — control-code and experimental-flow generation |
| whisper-large-v3-turbo (OpenAI) | `src/voice/` — speech-to-text for voice input |
| YOLOv8 (Ultralytics, AGPL-3.0) | `detection/` — optional object detection for process monitoring |

<!-- TODO: add 3D-printing filament type/settings and any wiring or adapters used. -->
