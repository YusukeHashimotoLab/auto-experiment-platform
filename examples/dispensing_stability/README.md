# Dispensing stability (100 repeated 3 mL injections)

Raw data and the historical control script for the dispensing-stability
measurement reported in the paper (§3.3 Methods, §4.1 Results).

## What was measured

Ion-exchanged water was aspirated and dispensed **100 times** at the **same
nominal volume of 3 mL**, by one robot arm carrying a Sartorius Picus 2
electronic pipette. After each injection the receiving vessel was weighed on
the electronic balance and the **difference from the previous reading** was
recorded as the dispensed mass. At room temperature the density of water is
close to 1 g/mL, so the mass in grams is read directly as the delivered volume
in millilitres.

| Item | Value |
|---|---|
| Liquid | Ion-exchanged water |
| Nominal volume per injection | 3 mL |
| Repetitions | n = 100 |
| Pipette | Sartorius Picus 2 (electronic), on a Dobot Magician arm |
| Aspiration speed step | 9 |
| Dispensing speed step | **9** (`dispensation_speed_1 = 9` in `control_250328.py`) |
| Wait between aspirate and dispense | 1 s (`wait_seconds`) |
| Balance | Sartorius BCE822i, readability **0.01 g** |
| Date | 2025-03-28 |

At speed step 9 the driver's timing table
(`src/devices/picus2/picus2_controller.py`, 0.9 s per 10 mL) gives a nominal
dispensing time of **≈0.27 s for 3 mL (≈11 mL/s)**.

> The balance readability of 0.01 g is the floor on the measurement: the
> scatter reported below is only about twice the quantisation step of the
> instrument, so it is an upper bound on the true dispensing variability
> rather than a precise estimate of it.

## Files

| File | Contents |
|---|---|
| `weight.csv` | The raw data: header `weight` plus 100 balance differences in grams, verbatim as written by the script. |
| `control_250328.py` | The script that produced `weight.csv` on 2025-03-28, verbatim apart from an added provenance header and the redaction of the pipettes' Bluetooth addresses and serial numbers. It imports the lab-local modules `ika_control`, `material_injection` and `BCE8221`, which are **not** part of this repository, so it is **not runnable here** — it is kept for provenance. |
| `stats.py` | Recomputes the statistics below from `weight.csv` (standard library + NumPy only). |

## Statistics

Computed from `weight.csv` in this directory with `stats.py`:

```
$ python examples/dispensing_stability/stats.py
n    : 100
mean : 3.0102 g
SD   : 0.0222 g   (sample, ddof=1)
RSD  : 0.738 %  (100 * SD / mean)
min  : 2.93 g
max  : 3.09 g
```

| Quantity | Formula | Value |
|---|---|---|
| n | number of rows in `weight.csv` | 100 |
| Mean | *x̄* = (1/n) Σ *xᵢ* | 3.0102 g |
| Standard deviation (sample) | *s* = √( Σ(*xᵢ* − *x̄*)² / (n − 1) ) — i.e. `ddof=1` | 0.02220 g |
| Relative standard deviation | RSD = 100 · *s* / *x̄* | 0.738 % |
| Minimum | min *xᵢ* | 2.93 g |
| Maximum | max *xᵢ* | 3.09 g |

The *population* standard deviation (`ddof=0`) is 0.02209 g, i.e. an RSD of
0.734 %; the choice of `ddof` does not change the rounded values quoted in the
paper.

## Comparison with the paper

| Quantity | Paper (§3.3 / §4.1) | Recomputed here | Agrees? |
|---|---|---|---|
| n | 100 | 100 | yes |
| Mean | 3.010 g | 3.0102 g | yes |
| SD | 0.022 g | 0.02220 g | yes |
| RSD | 0.74 % | 0.738 % | yes (0.738 % rounds to 0.74 %) |

No mismatch was found: every number the paper quotes is reproduced by
`stats.py` from the CSV in this directory. The paper does not quote min/max;
those are given above for completeness.

Two details are *not* stated in the paper and are recorded here from the
script instead: the speed step used (9, both aspiration and dispensing) and the
1 s wait between aspiration and dispensing.

## Reproducing the numbers

```bash
python examples/dispensing_stability/stats.py
# or point it at your own file with the same one-column layout
python examples/dispensing_stability/stats.py path/to/your_weights.csv
```

Requires NumPy only (already in `requirements.txt`).

## Reproducing the measurement on this platform

`control_250328.py` cannot be run here. The equivalent measurement is expressed
as a JSON flow for `src/flow/` — a `tare_scale` / `aspirate` / `dispense` /
`measure_weight` cycle inside a loop — using the volume, speed and wait values
from the table above. See [`docs/experimental-flow.md`](../../docs/experimental-flow.md)
for the schema and [`examples/zif8/`](../zif8/) for a worked flow.
