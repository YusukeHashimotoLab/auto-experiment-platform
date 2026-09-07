# `src/flow` — experimental-flow validation and execution

| File | Role |
|---|---|
| `schema.py` | Pydantic models for every action and for the whole flow (`ExperimentWorkflow`). `python src/flow/schema.py` prints the JSON Schema. |
| `executor.py` | `expand_loops()` flattens `loop_start`/`loop_end`; `execute_step()` dispatches one step to the right robot (`robot_id`) or to the shared devices. |
| `experiment_session.py` | `ExperimentSession` — the safety frame shared by every runner: initialise → run → **emergency stop on Ctrl+C**, go home on error → always disconnect. Robot and shared-device construction go through injectable factories, so mock and real runs use the same frame. |
| `experiment_logger.py` | `ExperimentLogger` — one folder per run under `logs/`, holding `run.log`, `measurements.csv`, `summary.md`, `metadata.json`, `images/` and a copy of the input JSON. |
| `accuracy_logger.py` | `DispenseAccuracyLogger` — pairs each `dispense` with the `measure_weight` that follows it and writes expected/measured mass and error to `dispense_accuracy.csv`. |
| `run_flow.py` | Command-line runner: validate → expand → initialise only the devices the flow needs → execute inside `ExperimentSession` → record every step → clean up. |
| `csv_runner/` | Spreadsheet input path: reads a `parameter,value,note` CSV and runs the fixed two-solution mixing sequence with those values. See below. |

The format itself is documented in [`docs/experimental-flow.md`](../../docs/experimental-flow.md).

## Command line

```bash
# validate only
python -m src.flow.run_flow path/to/flow.json --validate-only

# dry run with simulated devices
python -m src.flow.run_flow path/to/flow.json --mock

# real run; ports from config.yaml, overridable per run
python -m src.flow.run_flow path/to/flow.json \
    --robot1-dobot COM3 --robot1-picus2 COM4 \
    --robot2-dobot COM5 --robot2-picus2 COM6 \
    --scale-port COM8 --camera-index 1

# real run without sensor-CSV/video recording
python -m src.flow.run_flow path/to/flow.json --no-record

# dispensing ethanol rather than water (affects the accuracy CSV only)
python -m src.flow.run_flow path/to/flow.json --liquid-density 0.789
```

Only robots whose `robot_id` appears in the flow are connected; the balance and
camera are connected only if a step needs them.

### Ports and workspace limits

Ports and workspace limits come from `config.yaml` in the repository root — copy
`config.example.yaml` to `config.yaml` and edit it (`config.yaml` is gitignored; if
it is missing the example file is used, and if that is missing too the built-in
defaults in `src/config.py` apply). For a single run the resolution order is:

    command-line flag  >  environment variable (.env)  >  config.yaml  >  defaults

Every move is checked against the `workspace` limits by `WorkspaceValidator`
**before** the robot is commanded — for all robots, and in `--mock` mode too, so a
flow can be screened for out-of-range moves without hardware. A violation aborts
the run before the offending step executes.

### Recording

`--record` starts sensor-CSV recording on the monitoring dashboard (launching it
headless if needed) plus overhead-camera video for the duration of the run. It is
on by default for real runs, off with `--no-record`, and always off with `--mock`.

### What a run leaves behind

Each run creates `logs/<YYYY-MM-DD>/<flow name>_<timestamp>/` containing:

| File | Contents |
|---|---|
| `run.log` | the full console log of the run |
| `measurements.csv` | one row per step: timestamp, elapsed time, action, robot, loop iteration, status, duration, weight, image path, error |
| `summary.md` | human-readable report: outcome, the weight/photo timeline, and every step |
| `metadata.json` | start/end time, status (`completed` / `aborted` / `failed`), error, robots used, step and measurement counts |
| `images/` | photographs taken by `capture_and_save` during this run |
| `<flow>.json` | a copy of the input flow, so the run stays reproducible |
| `dispense_accuracy.csv` | expected vs. measured dispensed mass per `dispense` (only if the flow weighs after dispensing) |

### Interrupting a run

Ctrl+C triggers an **emergency stop**: the Dobot command queue is force-stopped
(the move in progress halts immediately, the queue is discarded and the conveyor
motors stop) and the IKA stirrer/heater is switched off. No further motion is
commanded — in particular the robot is *not* sent home, which would be another
move. Devices are then disconnected and the run is recorded as `aborted`.
On an ordinary error the robots do go home before disconnecting.

## Spreadsheet input (`csv_runner/`)

For the two-solution mixing experiment there is no need to touch JSON at all. Copy
`csv_runner/control.example.csv` to `csv_runner/control.csv`, edit the volumes, Z
descents, angles and pipette speeds in a spreadsheet program, and run:

```bash
python -m src.flow.csv_runner.run_csv --mock      # dry run
python -m src.flow.csv_runner.run_csv             # real run
```

The runner builds the fixed step list — the same shape as
`examples/zif8/zif8_two_solution_mixing_speed*.json` — validates it with
`ExperimentWorkflow` and runs it through `execute_step` inside an `ExperimentSession`,
so the workspace validator, the logging and the run folder are identical to a JSON run.
The dispensed masses are additionally written back to `results.csv` next to the input
sheet. Full documentation: [`docs/csv-runner.md`](../../docs/csv-runner.md).

## Library use

```python
from src.flow.schema import ExperimentWorkflow
from src.flow.executor import execute_step, expand_loops

flow = ExperimentWorkflow(**json_dict)          # raises pydantic.ValidationError if invalid
steps = expand_loops([s.model_dump() for s in flow.steps])
for step in steps:
    await execute_step(step, robots, shared_devices, logger)
```

`robots` is a dict `{robot_id: LabRobot | MockLabRobot}`; `shared_devices` is a
`SharedDevices` (or `None` if the flow uses none). `execute_step` returns the
step's measurement, if any (`{"weight": ...}` or `{"image_path": ...}`), which is
what `run_flow.py` records into `measurements.csv`.

To get the same safety frame in your own script, wrap the body in an
`ExperimentSession`:

```python
from src.flow.experiment_session import ExperimentSession

session = ExperimentSession(mock=False)          # mock=True for simulated devices

async def body():
    robot = await session.add_robot(1, use_picus2=True)
    shared = await session.add_shared(use_scale=True)
    ...                                          # your steps

await session.run(body)                          # emergency stop / go home / cleanup
```

## Tests

```bash
pytest tests/
```

The suite covers schema validation and loop expansion, the workspace validator and
its wiring to `config.yaml`, the `ExperimentSession` safety frame (including that a
cancellation emergency-stops instead of homing), the Dobot force-stop protocol, the
accuracy logger, the run_flow port precedence and the CSV runner (parameter
validation, the generated step list and a full mock run). It needs no hardware.

## Adding an action

1. Define a model in `schema.py` with an `action: Literal["..."]` field and add it to
   `LabRobotAction`.
2. Add an `elif action == "..."` branch in `execute_robot_step` or
   `execute_shared_device_step` (and add the name to `SHARED_DEVICE_ACTIONS` for the
   latter).
3. Implement the behaviour in the safety wrapper (`src/devices/safety`), never in the
   executor.
4. Describe it in the agent prompt (`src/agent/llm_service.py`) and in
   `docs/experimental-flow.md`.
