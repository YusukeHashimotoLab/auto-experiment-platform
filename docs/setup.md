# Setup guide

<!-- TODO: write the full setup procedure when the code is imported. Outline: -->

1. **Hardware assembly** — print the fixtures in `cad/`, mount the electric pipettes
   on the robot arm tips, place the receiving container on the electronic balance.
   One robot arm + one pipette per solution (prevents cross-contamination).
2. **Connections** — connect all instruments to the control PC via Wi-Fi or USB.
   The IoT sensor board (Raspberry Pi Zero WH) publishes time-stamped sensor data.
3. **Software** — install Python dependencies, copy `.env.example` to `.env`, set keys.
4. **First run** — generate an experimental flow with the AI agent, confirm it on the
   GUI, and execute.

See `docs/experimental-flow.md` for the JSON flow format.
