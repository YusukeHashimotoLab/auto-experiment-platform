# `src/gui` — browser-based GUI

A Streamlit app for building, reviewing and running experimental flows without
editing JSON by hand.

```bash
streamlit run src/gui/app.py
```

Opens `http://localhost:8501`.

| file | role |
|---|---|
| `app.py` | the Streamlit UI only: flow canvas, presets, AI/voice input, sidebar, progress |
| `runner.py` | all execution logic, Streamlit-free and unit-tested (`tests/test_gui_runner.py`) |
| `analyze_dispense_log.py` | precision/accuracy statistics for a finished run folder |

`app.py` holds no device code: pressing *Run* hands the flow to `runner.FlowRunner`,
which takes exactly the same path as the CLI (`python -m src.flow.run_flow`), so a
flow behaves identically whether it is started from the browser or the terminal.

## Features

- **Flow canvas** — every step of the current flow as an editable card (parameters,
  `robot_id`, reorder, delete); a toolbox adds new steps.
- **Presets** — load a validated flow from `src/agent/presets/`.
- **AI generation** — describe the experiment in natural language; the agent
  (`src/agent`) returns a flow that is shown in the canvas for review before running.
  Optionally start from a preset and let the agent change only its parameters.
- **Voice input** — microphone button next to each text box; transcription by
  `src/voice`.
- **Validation before execution** — the flow is checked against the Pydantic schema
  (`src/flow/schema.py`) and its loops are expanded *before* any device is opened.
  A flow that fails validation is refused: the errors are listed in the UI (one line
  per offending step) and no `ExperimentSession` is created. Flows arriving from the
  agent, a preset or an uploaded JSON file are validated on arrival as well, and the
  *Validate* button re-checks the current canvas without running it.
- **Mock / Real** — *Mock* runs the whole flow against `MockLabRobot` /
  `MockSharedDevices`, writing the same log folder as a real run; nothing is recorded
  and the safety gate is not queried. *Real* drives the instruments.
- **Stop** — cancels the running flow. Cancellation lands in `ExperimentSession`'s
  abort path, the same one Ctrl+C takes on the CLI: every robot is emergency-stopped,
  all devices are disconnected, and the run folder is finalised with
  `status: aborted`. (There is no separate "emergency stop" that leaves the run
  half-finished behind.)
- **Progress and log** — a progress bar (`n/total` steps) and the step-by-step log,
  including the device-level messages (balance readings, image paths).
- **Monitoring hook** — in Real mode, if the sensor dashboard (`src/monitoring`) is
  reachable at `SENSOR_SERVER_URL` (default `http://localhost:8000`), recording is
  started before the run and stopped after it, and the dashboard's `/api/is_safe`
  check gates every step (an unreachable dashboard does not block the run).

## Device settings (sidebar)

Ports and the camera index default to **`config.yaml`** in the repository root
(falling back to the tracked `config.example.yaml`), read through `src.config` — the
same source the CLI uses, so the GUI and the CLI cannot drift apart. Edits in the
sidebar apply to the current browser session only; *↺ config.yaml の値に戻す* restores
the file's values. For a permanent change, edit `config.yaml`.

Only the devices the flow actually uses are opened: robots are taken from the
`robot_id` of the steps, the pipette from `aspirate`/`dispense`/`blow_out`, the
balance from `measure_weight`/`tare_scale` and the camera from `capture_and_save`.

## What a run leaves behind

Every run — from the GUI or the CLI, mock or real — creates

```
logs/<date>/<flow name>_<timestamp>/
    run.log               every log line of the run
    <flow>.json           a copy of the flow that was executed
    measurements.csv      one row per step (weight, image path, status, duration)
    dispense_accuracy.csv each dispense paired with the mass weighed after it
    metadata.json         start/end, status, robots used, counts
    summary.md            human-readable report
    images/               pictures taken by capture_and_save
```

The folder is shown under the progress bar while the run is in progress.

To get the statistics of a dispensing run (mean, SD, variance, CV as the
repeatability figure, and the bias against the nominal mass as the trueness figure):

```bash
python -m src.gui.analyze_dispense_log logs/<date>/<flow name>_<timestamp>
python -m src.gui.analyze_dispense_log <run folder> --volume 5 --density 0.998
```

It reads `dispense_accuracy.csv` and falls back to the `weight_g` column of
`measurements.csv`, so it works for any run that weighed something.

## How the run is driven (and why)

Streamlit re-runs the whole script on every interaction, so the run cannot simply
block the script — but slicing it into one step per re-run would mean keeping live
device handles in `st.session_state` and re-implementing the safety frame around
them. Instead `FlowRunner` executes the flow in **one background thread with one
asyncio event loop**, entirely inside `ExperimentSession.run()`, and publishes
`ProgressEvent`s on a queue; the Streamlit script drains that queue and re-runs
itself every ~0.4 s while the thread is alive. *Stop* cancels the asyncio task from
the outside. The run thread never touches the Streamlit API, which is also why
`runner.py` can be tested without a browser.

## Requirements

`streamlit`, `streamlit-mic-recorder` (voice button) and the modules in `src/agent`,
`src/voice`, `src/flow`, `src/devices`. The app degrades gracefully: without an LLM
key the AI button shows a hint; without `ffmpeg`/whisper the microphone is hidden.
