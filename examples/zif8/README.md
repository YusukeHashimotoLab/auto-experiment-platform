# ZIF-8 demonstration

Experimental flows for the two-solution mixing demonstration described in the paper:
ZIF-8 synthesis in which solution 2 is dispensed at three different **pipette speed
steps (1, 5 and 9)**, three trials per condition in alternating order.

The batches themselves were run from a spreadsheet — see
[`docs/csv-runner.md`](../../docs/csv-runner.md) and Provenance below. The JSON files
here express that same sequence for the JSON runner.

## Provenance — please read first

> **The paper's batches were run through the CSV runner, not through these JSON
> files.**
>
> The nine ZIF-8 batches reported in the paper were executed with the lab's
> spreadsheet runner — the internal `excel_runner/run_csv.py`, published here as
> [`src/flow/csv_runner/`](../../src/flow/csv_runner/) — in the version in force
> from 2026-07-02 onward (internal commit `4584333`, 2026-06-30). No
> LLM-generated JSON flow was executed for those runs. The operator typed the
> volumes, Z descents, angles and pipette speeds into a spreadsheet and the
> runner performed a fixed sequence.
>
> **The three JSON files in this directory are the equivalent flows for the JSON
> path.** They reproduce that fixed sequence step for step, so that the same
> experiment can be run through `src/flow/run_flow.py` or the GUI, and so that the
> sequence is readable without running anything. They are not the run records of
> the paper's experiments.
>
> Concretely, this means:
>
> - The **motion sequence** is the historical one, taken from the source of the
>   runner version above: descend onto the source vial → aspirate → rise → rotate
>   to the balance → descend → **tare with the tip already lowered** → dispense →
>   **read the mass before the tip rises** → rise → `go_home` (the home move also
>   undoes the rotation). Robot 1 completes its sequence, then Robot 2.
> - The **numeric values** — 5 mL per solution, 0.1 mm aspiration descent, 120 mm
>   dispensing descent, ±90° rotations, Robot 1 dispensing at speed 9, aspiration
>   at speed 1 for both robots — are those of the lab's committed control sheet at
>   that commit. They are **not necessarily the values of every batch**: the
>   dispensing speed of Robot 2 was varied over 1 / 5 / 9 across the nine batches,
>   which is what these three files differ in. The per-batch run records are not
>   published yet; when they are added they will replace the placeholder sensor
>   CSVs below.
> - Aspiration ran at **speed 1** in every batch: it was the code constant
>   `ASPIRATE_SPEED = 1`, not a spreadsheet cell. (A note in the lab's sheet
>   claimed aspiration was "always 5"; that note was stale and never affected the
>   runs.)
> - The **single `capture_and_save` at the end of each JSON file is an addition**
>   of this public example. The CSV sequence took no photograph; the public runner
>   offers it as the optional `capture_photo` parameter, off by default.
> - The **dispensing times quoted below are nominal**, computed from the Picus 2
>   speed table in the pipette manual, not measured on the instrument.
> - The **geometry is fixture-specific**. It is the geometry of the original
>   setup, but it has not been re-verified against it; measure your own flask and
>   vial positions before a real run.
> - The CSV files `sensor_session_sample.csv` and `sensor_session_sample_tags.csv`
>   are **column templates with fabricated values**, not measurements. See
>   [Monitoring sample files](#monitoring-sample-files-placeholders) below.
>
> Nothing in this directory should be cited as measured data.

## Files

The three flow files are identical except for the `speed` of the solution-2
`dispense` step. Solution 1 is always dispensed at speed 9 (nominal 0.45 s for
5 mL) and both solutions are aspirated at speed 1.

| File | Solution 2 `dispense.speed` | Nominal time for 5 mL | Nominal rate |
|---|---|---|---|
| `zif8_two_solution_mixing_speed1.json` | 1 | 5.1 s | 0.98 mL/s |
| `zif8_two_solution_mixing_speed5.json` | 5 | 1.45 s | 3.4 mL/s |
| `zif8_two_solution_mixing_speed9.json` | 9 | 0.45 s | 11.1 mL/s |

### Picus 2 speed steps → nominal time for 5 mL

The Picus 2 electronic pipette is set by a **speed step from 1 to 9**, not by a
time. The manual (p. 63) gives the seconds needed per 10 mL at each step; this
table is encoded in `calculate_operation_time()` in
[`src/devices/picus2/picus2_controller.py`](../../src/devices/picus2/picus2_controller.py).
Times for 5 mL are half of those values:

| Speed step | s per 10 mL (manual) | Nominal time for 5 mL | Nominal rate for 5 mL |
|---|---|---|---|
| 1 | 10.2 | 5.10 s | 0.98 mL/s |
| 2 | 7.4 | 3.70 s | 1.35 mL/s |
| 3 | 5.4 | 2.70 s | 1.85 mL/s |
| 4 | 3.8 | 1.90 s | 2.63 mL/s |
| 5 | 2.9 | 1.45 s | 3.45 mL/s |
| 6 | 2.2 | 1.10 s | 4.55 mL/s |
| 7 | 1.7 | 0.85 s | 5.88 mL/s |
| 8 | 1.3 | 0.65 s | 7.69 mL/s |
| 9 | 0.9 | 0.45 s | 11.11 mL/s |

These are **nominal** figures from the manual's table, linear in volume. They do
not include the pipette's own acceleration and settling, and they were not
measured on the instrument, so the actual dispensing time will differ. The
**speed step is the quantity that was actually set and is therefore the primary
fact**; the times are given only to make the conditions interpretable.

> Earlier drafts of this repository named the files `_5s`, `_2s` and `_0.5s` and
> described speed 5 as "~2.0 s". That was wrong: 2.0 s for 5 mL corresponds to
> speed 4 (1.9 s), not speed 5. The files have been renamed after the speed step
> they set, and the times recomputed from the table above.

## What the flow does

The same sequence as a CSV run, in the same order:

1. **Robot 1 / solution 1** (Zn(NO₃)₂·6H₂O + PEG in DMF): lower 0.1 mm onto the
   source vessel, aspirate 5 mL at speed 1, rise, rotate +90° over the vial on the
   balance, lower 120 mm into it.
2. Tare the balance at that lowered position, dispense 5 mL at speed 9, and read
   the balance **before** the tip rises (median of 3 readings — the mass of
   solution 1).
3. Raise the arm 120 mm and send Robot 1 home; the home move also undoes the
   rotation, so there is no separate rotate-back step.
4. **Robot 2 / solution 2** (2-methylimidazole + triethylamine in DMF): the same
   ten steps mirrored (rotation −90°), dispensing at the speed step under test.
5. Photograph the vial — **this last step only exists in these JSON examples**;
   the CSV runs that produced the paper's data ended after Robot 2 went home.

Reagent quantities, stirring conditions and the pre-mixing procedure are given in the
paper (Methods). Solution recipes are not encoded in the flow: the flow only moves,
aspirates, dispenses, weighs and photographs.

## Adapting to your setup

- `move_z` distances (−0.1 / +0.1 mm at the source vessel, −120 / +120 mm into the
  vial on the balance) and the ±90° `rotate_relative` angles are specific to the
  fixture geometry of the original setup — see Provenance above — and were not
  re-verified against it.
  Measure your own flask and vial positions relative to each robot's home position and
  edit these values. Use `--mock` first, then the "position check" presets in
  `src/agent/presets/` (`wdc_2_dispense_robot1.json`, `wdc_3_dispense_robot2.json`)
  with the pipette steps removed.
- `robot_id` 1 and 2 map to the two arm + pipette pairs; each pipette handles only
  one solution, so tips are never exchanged.

## Running

```bash
# schema check only, no hardware, no motion
python -m src.flow.run_flow examples/zif8/zif8_two_solution_mixing_speed5.json --validate-only

# validate + dry run without hardware
python -m src.flow.run_flow examples/zif8/zif8_two_solution_mixing_speed5.json --mock

# real run (ports from .env or flags; see docs/setup.md)
python -m src.flow.run_flow examples/zif8/zif8_two_solution_mixing_speed5.json
```

Substitute `_speed1` or `_speed9` for the other two conditions.

Or load the file in the GUI (`streamlit run src/gui/app.py`) and press Run.

## Process logs

Sample process logs (dispensed masses, sensor CSVs, photographs) from the paper are
not included in this directory yet, except for the monitoring placeholders below. The
per-batch run records — the control sheet, `results.csv` and log folder of each of the
nine batches — are not published yet and will be added here, replacing the
placeholders below, when available.
<!-- TODO: add sample logs / measured masses when ready -->

For data that *is* real and published, see
[`examples/dispensing_stability/`](../dispensing_stability/): 100 repeated 3 mL
water injections weighed on the balance, with the original control script.

### Monitoring sample files (placeholders)

- [`sensor_session_sample.csv`](sensor_session_sample.csv) — **placeholder**
  showing the column layout produced by the IoT sensor dashboard
  (`src/monitoring/dashboard/launch_sensor_dashboard.py`): a header row plus 3
  example rows at the dashboard's 100 ms sampling interval. Values are
  plausible but fabricated, not measurements from an actual run. Note that its
  `uvi` column reads `0` because the LTR390 was left in ALS mode until
  2026-09-08; that column now carries a UV index (float).
- [`sensor_session_sample_tags.csv`](sensor_session_sample_tags.csv) —
  **placeholder** for the companion AprilTag pose-tracking log from the same
  session (`_tags` suffix): a header row plus 2 example rows.

Both files exist only to document the CSV format ahead of time — see
[`src/monitoring/README.md`](../../src/monitoring/README.md#log-format) for
the column reference. They will be replaced with real sensor/marker logs from
a ZIF-8 synthesis session once that data is available.
