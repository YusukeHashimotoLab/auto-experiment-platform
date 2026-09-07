"""Spreadsheet (CSV) input path for the fixed two-solution mixing experiment.

See `docs/csv-runner.md`. The runner reads `control.csv`, builds the same step list
the JSON flows in `examples/zif8/` describe, validates it with `ExperimentWorkflow`
and runs it through the same executor and safety frame as `src/flow/run_flow.py`.
"""
from src.flow.csv_runner.run_csv import (  # noqa: F401
    CONTROL_CSV_PATH,
    EXAMPLE_CSV_PATH,
    PARAM_SPECS,
    build_steps,
    build_workflow,
    default_csv_path,
    load_params_from_csv,
    main,
    run_two_solution_mixing,
    write_results_csv,
)

__all__ = [
    "CONTROL_CSV_PATH",
    "EXAMPLE_CSV_PATH",
    "PARAM_SPECS",
    "build_steps",
    "build_workflow",
    "default_csv_path",
    "load_params_from_csv",
    "main",
    "run_two_solution_mixing",
    "write_results_csv",
]
